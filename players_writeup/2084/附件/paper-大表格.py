import sys, re, math
import xml.etree.ElementTree as ET

CIRCLE_D_PREFIX = "m 0,-3 c 0.795609"  # 题面里圆点 path 的 d 前缀
BLUE_FILL = "#1f77b4"

def parse_transform_matrix(s: str):
    # matrix(a,b,c,d,e,f) -> return (a,b,c,d,e,f) as float
    m = re.search(r"matrix\(\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*\)", s or "")
    if not m:
        return None
    return tuple(float(m.group(i)) for i in range(1, 7))

def extract_id_num(s: str):
    if not s:
        return -1
    m = re.search(r"(\d+)$", s)
    return int(m.group(1)) if m else -1

def kmeans_1d(values, k=4, max_iter=100):
    # Simple 1D k-means; returns labels (same length as values) and centers
    if len(values) < k:
        # pad unique sorted approach
        uniq = sorted(values)
        centers = [uniq[min(i, len(uniq)-1)] for i in range(k)]
    else:
        lo, hi = min(values), max(values)
        if lo == hi:
            centers = [lo + 0.0 for _ in range(k)]
        else:
            step = (hi - lo) / (k + 1)
            centers = [lo + (i+1)*step for i in range(k)]
    labels = [0]*len(values)
    for _ in range(max_iter):
        changed = False
        # assign
        for i, v in enumerate(values):
            idx = min(range(k), key=lambda j: abs(v - centers[j]))
            if labels[i] != idx:
                labels[i] = idx
                changed = True
        # update
        new_centers = centers[:]
        for j in range(k):
            pts = [v for v, lbl in zip(values, labels) if lbl == j]
            if pts:
                new_centers[j] = sum(pts)/len(pts)
        if all(abs(new_centers[j]-centers[j]) < 1e-9 for j in range(k)):
            centers = new_centers
            break
        centers = new_centers
        if not changed:
            break
    return labels, centers

def map_to_0123(coords):
    # coords: list of floats for one axis, returns labels 0..3 aligned to sorted centers
    if not coords:
        return [], []
    k = 4
    # Fast path: exactly 4 distinct values
    uniq = sorted(set(round(v, 3) for v in coords))
    if len(uniq) == 4:
        idx_by_value = {val:i for i, val in enumerate(sorted(uniq))}
        labels = [idx_by_value[round(v, 3)] for v in coords]
        centers = [val for val in sorted(uniq)]
        return labels, centers
    # Otherwise k-means
    labels, centers = kmeans_1d(coords, k=4)
    # Remap cluster ids to 0..3 by center rank
    ranking = {j:i for i, j in enumerate(sorted(range(4), key=lambda j: centers[j]))}
    labels_mapped = [ranking[lbl] for lbl in labels]
    centers_sorted = [centers[j] for j in sorted(range(4), key=lambda j: centers[j])]
    return labels_mapped, centers_sorted

def bytes_printable_score(bs: bytes):
    printable = set(range(32, 127)) | {9,10,13}
    good = sum(1 for b in bs if b in printable)
    return good / max(1, len(bs))

def try_decode(nibbles):
    # Try combinations:
    # orientations: x normal/rev, y normal/rev
    # nibble order per byte: [hi,lo] or [lo,hi]
    results = []
    n = len(nibbles)
    if n % 2 == 1:
        n -= 1  # drop last odd nibble
    for xrev in (False, True):
        for yrev in (False, True):
            for hi_lo in (True, False):  # True: first is high nibble
                def map_nib(v):
                    y = (v >> 2) & 0b11
                    x = v & 0b11
                    if xrev: x = 3 - x
                    if yrev: y = 3 - y
                    return (y << 2) | x
                mapped = [map_nib(v) for v in nibbles[:n]]
                if hi_lo:
                    bs = bytes(((mapped[i] << 4) | mapped[i+1]) for i in range(0, len(mapped), 2))
                else:
                    bs = bytes(((mapped[i+1] << 4) | mapped[i]) for i in range(0, len(mapped), 2))
                score = bytes_printable_score(bs)
                txt = None
                try:
                    txt = bs.decode('utf-8', errors='ignore')
                except:
                    txt = None
                contains_flag = 1 if (txt and re.search(r"(flag|ctf)\{.*?\}", txt, re.I)) else 0
                results.append({
                    "xrev": xrev, "yrev": yrev, "hi_lo": hi_lo,
                    "bytes": bs, "text": txt, "score": score,
                    "contains_flag": contains_flag
                })
    # pick best: contains_flag first, then score, then longer text
    results.sort(key=lambda r: (r["contains_flag"], r["score"], len(r["bytes"])), reverse=True)
    return results

def main(svg_path):
    tree = ET.parse(svg_path)
    root = tree.getroot()
    # SVG may have namespace; handle any
    paths = []
    for elem in root.iter():
        tag = elem.tag.split('}', 1)[-1]  # strip namespace
        if tag != 'path':
            continue
        d = elem.get('d') or ""
        style = elem.get('style') or ""
        transform = elem.get('transform') or ""
        pid = elem.get('id') or ""
        # 过滤“圆点”path：优先用 d 前缀；不行则用填充色与 transform 都存在
        if d.startswith(CIRCLE_D_PREFIX) or (('#1f77b4' in style.lower()) and 'matrix(' in transform):
            m = parse_transform_matrix(transform)
            if not m:
                continue
            e, f = m[4], m[5]  # 平移量即点坐标
            paths.append((extract_id_num(pid), e, f, pid))
    if not paths:
        print("未找到任何散点 path，请检查 d 前缀或填充色过滤条件。")
        return
    # 按 id 顺序
    paths.sort(key=lambda t: t[0])
    paths.reverse()
    xs = [p[1] for p in paths]
    ys = [p[2] for p in paths]
    xlabels, xcenters = map_to_0123(xs)
    ylabels, ycenters = map_to_0123(ys)
    if len(xlabels) != len(paths) or len(ylabels) != len(paths):
        print("聚类失败。")
        return
    # 生成 nibbles（保持重复点）
    nibbles = [((ylabels[i] << 2) | xlabels[i]) for i in range(len(paths))]
    results = try_decode(nibbles)
    best = results[0]
    # 输出最佳猜测
    print("最佳候选：")
    print(f"x_reverse={best['xrev']}, y_reverse={best['yrev']}, hi_is_first={best['hi_lo']}")
    print("hex:", best["bytes"].hex())
    try:
        s = best["bytes"].decode('utf-8')
        print("utf8:", s)
    except:
        print("ascii_ignore:", best["bytes"].decode('ascii','ignore'))
    # 同时输出若干次优候选，便于人工确认
    print("\n其他候选（最多 3 个）：")
    for cand in results[1:4]:
        print(f"- xrev={cand['xrev']} yrev={cand['yrev']} hi_first={cand['hi_lo']} score={cand['score']:.2f}")
        print("  hex:", cand["bytes"].hex())
        if cand["text"]:
            print("  text:", cand["text"][:120])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 quadbits_svg_flag.py input.svg")
        sys.exit(1)
    main(sys.argv[1])