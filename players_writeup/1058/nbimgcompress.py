#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import argparse, base64, glob, io, json, sys, re
from copy import deepcopy

try:
    from PIL import Image, ImageOps
except ImportError:
    print("请先安装 Pillow： pip install pillow", file=sys.stderr)
    sys.exit(1)

def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))

def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

def is_image_mime(m: str) -> bool:
    return m.startswith("image/")

def trim_text_lines(value, max_lines: int = 100, head: int = 50, tail: int = 50):
    if not isinstance(value, (str, list)):
        return value, False

    if isinstance(value, str):
        lines = value.splitlines(keepends=True)
        is_str = True
    else:
        lines = []
        for part in value:
            if isinstance(part, str):
                lines.extend(part.splitlines(keepends=True))
            else:
                lines.append(str(part))
        is_str = False

    if len(lines) <= max_lines:
        return value, False

    trimmed_lines = lines[:head] + ["...\n"] + lines[-tail:]
    if is_str:
        return "".join(trimmed_lines), True
    return trimmed_lines, True

def trim_output_text(out: dict, max_lines: int = 100, head: int = 50, tail: int = 50) -> int:
    changed = 0

    if "text" in out:
        new_text, updated = trim_text_lines(out["text"], max_lines=max_lines, head=head, tail=tail)
        if updated:
            out["text"] = new_text
            changed += 1

    data = out.get("data")
    if isinstance(data, dict):
        for key in list(data.keys()):
            if key.startswith("text/"):
                new_val, updated = trim_text_lines(data[key], max_lines=max_lines, head=head, tail=tail)
                if updated:
                    data[key] = new_val
                    changed += 1

    return changed

def exif_transpose(im: Image.Image) -> Image.Image:
    # 处理相机旋转信息
    try:
        return ImageOps.exif_transpose(im)
    except Exception:
        return im

def resize_by_max_width(im: Image.Image, max_w: int) -> Image.Image:
    w, h = im.size
    if w <= max_w:
        return im
    new_h = int(h * (max_w / float(w)))
    return im.resize((max_w, max(1, new_h)), Image.LANCZOS)

def to_jpeg_bytes(src_bytes: bytes, max_width: int, quality: int) -> bytes:
    with Image.open(io.BytesIO(src_bytes)) as im:
        im = exif_transpose(im)
        im = resize_by_max_width(im, max_width)

        # 透明图铺白底
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            if im.mode == "P":
                im = im.convert("RGBA")
            bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
            im = bg
        else:
            im = im.convert("RGB")

        out = io.BytesIO()
        # progressive + optimize 能再小一些
        im.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
        return out.getvalue()

def update_md_refs(src, old_name: str, new_name: str):
    """把 markdown 源里 (attachment:old) 改成 (attachment:new)。"""
    pat = re.compile(r'(\(attachment:)' + re.escape(old_name) + r'(\))')
    def repl_text(text: str) -> str:
        return pat.sub(r'\1' + new_name + r'\2', text)

    if isinstance(src, list):
        return [repl_text(x) for x in src]
    elif isinstance(src, str):
        return repl_text(src)
    return src

def suggest_new_name(old: str) -> str:
    if old.lower().endswith(".jpg") or old.lower().endswith(".jpeg"):
        return old
    # 把扩展名改为 .jpg；没有扩展名就追加
    if "." in old:
        base = old.rsplit(".", 1)[0]
        return base + ".jpg"
    return old + ".jpg"

def process_attachments_in_cell(cell: dict, max_width: int, quality: int,
                                rename_keys_to_jpg: bool) -> int:
    """返回本 cell 里被修改的 attachment 数量。"""
    attachments = cell.get("attachments", {})
    changed = 0
    if not attachments:
        return 0

    new_attachments = {}
    to_rename = []  # (old_name, new_name)

    for name, bundle in attachments.items():
        # 找到其中的 image/* 数据（可能有多个 mime，取第一个能解码的）
        img_mimes = [m for m in bundle.keys() if is_image_mime(m)]
        if not img_mimes:
            new_attachments[name] = bundle
            continue

        success = False
        for m in img_mimes:
            try:
                src_b = b64d(bundle[m])
                jpeg_b = to_jpeg_bytes(src_b, max_width=max_width, quality=quality)
                # 重写为单一 image/jpeg
                new_bundle = {"image/jpeg": b64e(jpeg_b)}
                new_attachments[name] = new_bundle
                changed += 1
                success = True
                break
            except Exception:
                # 换下一个 mime 尝试
                continue

        if not success:
            # 原样保留，避免破坏
            new_attachments[name] = bundle

    # 重命名 attachment key 并同步 markdown 引用
    if rename_keys_to_jpg and changed:
        renamed_attachments = {}
        # 为避免重名，收集已有 key
        existing = set(new_attachments.keys())
        for old_name in list(new_attachments.keys()):
            new_name = suggest_new_name(old_name)
            if new_name != old_name:
                # 避免碰撞
                base = new_name.rsplit(".", 1)[0]
                ext = ".jpg"
                idx = 1
                tmp = new_name
                while tmp in existing:
                    tmp = f"{base}_{idx}{ext}"
                    idx += 1
                new_name = tmp
                existing.add(new_name)
                to_rename.append((old_name, new_name))

        if to_rename:
            for old, new in to_rename:
                renamed_attachments[new] = new_attachments.pop(old)
            new_attachments.update(renamed_attachments)
            # 修正 markdown 源里的 attachment: 引用
            cell["source"] = update_md_refs(cell.get("source", ""), old, new)

    # 写回
    if changed:
        cell["attachments"] = new_attachments
    return changed

def process_outputs_in_cell(cell: dict, max_width: int, quality: int) -> int:
    """可选：压缩 outputs 里的 image/* -> image/jpeg（一般不需要）。"""
    oc = 0
    for out in cell.get("outputs", []) or []:
        oc += trim_output_text(out)
        data = out.get("data")
        if not isinstance(data, dict):
            continue
        mimes = [m for m in list(data.keys()) if is_image_mime(m)]
        for m in mimes:
            try:
                src_b = b64d(data[m])
                jpeg_b = to_jpeg_bytes(src_b, max_width=max_width, quality=quality)
                # 用 jpeg 替换所有 image/*，只保留一个
                for mm in mimes:
                    data.pop(mm, None)
                data["image/jpeg"] = b64e(jpeg_b)
                oc += 1
                break
            except Exception:
                continue
    return oc

def process_notebook(nb: dict, max_width: int, quality: int,
                     rename_keys_to_jpg: bool):
    nb = deepcopy(nb)
    att_changes = 0
    out_changes = 0
    for cell in nb.get("cells", []):
        att_changes += process_attachments_in_cell(
            cell, max_width=max_width, quality=quality,
            rename_keys_to_jpg=rename_keys_to_jpg
        )
        out_changes += process_outputs_in_cell(
            cell, max_width=max_width, quality=quality
        )
    return nb, att_changes, out_changes


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="将 .ipynb 中的 attachments 与 outputs 统一转为指定宽度的 JPEG，默认 800px，质量 90。"
    )
    ap.add_argument(
        "inputs",
        nargs="+",
        help="待处理的 notebook 路径，可以一次指定多个或使用通配符 (*.ipynb)",
    )
    ap.add_argument(
        "-o",
        "--output",
        help="输出路径；处理多个文件时请提供目录，默认覆盖原文件。",
        default=None,
    )
    ap.add_argument("--max-width", type=int, default=800, help="最大宽度，单位px，默认 800")
    ap.add_argument("--jpeg-quality", type=int, default=80, help="JPEG 质量（1-95），默认 90")
    ap.add_argument(
        "--rename-keys-to-jpg",
        action="store_true",
        help="将 attachment 的 key 统一成 .jpg，并同步更新 markdown 引用",
    )

    args = ap.parse_args()

    expanded_inputs = []
    for pattern in args.inputs:
        matches = sorted(glob.glob(pattern))
        if matches:
            expanded_inputs.extend(matches)
        else:
            expanded_inputs.append(pattern)

    seen = set()
    input_paths = []
    for path in expanded_inputs:
        if path not in seen:
            input_paths.append(path)
            seen.add(path)

    if not input_paths:
        print("未找到需要处理的文件。", file=sys.stderr)
        sys.exit(1)

    if args.output and len(input_paths) > 1:
        if os.path.exists(args.output) and not os.path.isdir(args.output):
            print("处理多个文件时，--output 必须是目录。", file=sys.stderr)
            sys.exit(1)
        os.makedirs(args.output, exist_ok=True)

    for input_path in input_paths:
        output_path = args.output or input_path
        if args.output and len(input_paths) > 1:
            output_path = os.path.join(args.output, os.path.basename(input_path))

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                nb = json.load(f)
        except FileNotFoundError:
            print(f"找不到 notebook: {input_path}", file=sys.stderr)
            continue

        old_size = os.path.getsize(input_path)

        new_nb, a_changed, o_changed = process_notebook(
            nb,
            max_width=args.max_width,
            quality=args.jpeg_quality,
            rename_keys_to_jpg=args.rename_keys_to_jpg,
        )

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(new_nb, f, ensure_ascii=False, indent=1)

        new_size = os.path.getsize(output_path)
        same_path_note = "" if output_path != input_path else " (覆盖原文件)"
        print(
            f"{input_path} -> {output_path}{same_path_note}"
            f"    修改的 attachments: {a_changed}，修改的 outputs: {o_changed}，文件大小: {old_size} -> {new_size} 字节"
        )
