import argparse
import sys
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from multiprocessing import Pool
from os import cpu_count
from typing import Dict, List
from functools import partial
import torch

from clip_classifier import Classifier

# --- Constants ---
DUPLICATION_FACTOR = 3
CLIP_BATCH_SIZE = 256

# Laplacian Analysis Constants
ANALYSIS_START_TARGET = 1
ANALYSIS_END_TARGET = 10
STRONG_ATTACK_SLOPE = 0.025
STRONG_NORMAL_SLOPE = 0.04

# Manual override for specific, human-inspected ORIGINAL bit indices.
# MANUAL_INSPECTION: Dict[int, bool] = {}
MANUAL_INSPECTION: Dict[int, bool] = {
    29: True,  # Manually fix this bit
    364: True,
}

# --- Worker Functions for Parallel Processing ---
def get_laplacian_noise_map(image: Image.Image) -> np.ndarray:
    grayscale_image = image.convert('L')
    laplacian_kernel = (0, 1, 0, 1, -4, 1, 0, 1, 0)
    kernel = ImageFilter.Kernel(size=(3, 3), kernel=laplacian_kernel, scale=1)
    laplacian_image = grayscale_image.filter(kernel)
    laplacian_array = np.array(laplacian_image)
    abs_laplacian = np.abs(laplacian_array)
    if abs_laplacian.max() > 0:
        return (abs_laplacian / abs_laplacian.max()) * 255
    return abs_laplacian

def process_laplacian_image(image_path: Path) -> Dict:
    idx = int(image_path.stem)
    original_image = Image.open(image_path)
    noise_map_array = get_laplacian_noise_map(original_image)
    hist_counts = np.bincount(noise_map_array.flatten().astype(int), minlength=256)
    
    log_counts = np.log(hist_counts + 1)
    x1, x2 = ANALYSIS_START_TARGET, ANALYSIS_END_TARGET
    while x1 < len(log_counts) and hist_counts[x1] == 0: x1 += 1
    if x2 <= x1: x2 = x1 + 1
    while x2 < len(log_counts) and hist_counts[x2] == 0: x2 += 1

    slope = 0.0 if (x1 >= x2 or x2 >= len(log_counts)) else (log_counts[x2] - log_counts[x1]) / (x2 - x1)
    return {"idx": idx, "slope": slope, "hist_counts": hist_counts, "x1": x1, "x2": x2}

def create_plot_worker(case_data: Dict, output_dir: Path):
    """Worker function to generate a plot for a single non-confident or split-decision case."""
    original_idx = case_data['original_idx']
    title_reason = case_data['title_reason']
    
    fig, axes = plt.subplots(DUPLICATION_FACTOR, 1, figsize=(10, 4 * DUPLICATION_FACTOR), sharex=True)
    fig.suptitle(f"{title_reason} for Original Bit {original_idx}\nFinal Result: {case_data['final_result']}", fontsize=16)

    for i, duplicate_data in enumerate(case_data['duplicates']):
        ax = axes[i]
        actual_idx = duplicate_data['actual_idx']
        hist_counts = duplicate_data['hist_counts']
        x1, x2 = duplicate_data['x1'], duplicate_data['x2']
        reason = duplicate_data['reason']
        
        ax.bar(np.arange(256), hist_counts, color='navy', width=1.0)
        ax.set(yscale='log', title=f"Image {actual_idx} | Initial Vote: {reason}")
        ax.grid(True, which='both', linestyle=':', linewidth=0.5)

        y1_log, y2_log = np.log(hist_counts[x1] + 1), np.log(hist_counts[x2] + 1)
        ax.plot([x1, x2], [np.exp(y1_log)-1, np.exp(y2_log)-1], color='orange', linewidth=2, linestyle='--', zorder=5)

    plt.xlabel("Pixel Brightness")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_dir / f"case_{original_idx}.png", dpi=100)
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser(
        description="Solve flag2 using a voting system on duplicated image sets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--images-dir", type=Path, default=Path("flag2_images"), help="Directory containing the input images.")
    parser.add_argument("--plot-dir", type=Path, help="[Optional] Directory to save plots for non-confident and split-decision cases.")
    parser.add_argument("--flag-file", type=Path, help="[Debug] Optional ground truth flag file to compare results against.")
    args = parser.parse_args()

    if not args.images_dir.is_dir(): sys.exit(f"Error: Input directory not found at '{args.images_dir}'")
    try: image_paths = sorted(list(args.images_dir.glob("*.png")), key=lambda p: int(p.stem))
    except ValueError: sys.exit("Error: Image filenames must be numeric for sorting.")
    
    n_images = len(image_paths)
    if n_images == 0: sys.exit(f"Error: No PNG images found in '{args.images_dir}'")
    if n_images % DUPLICATION_FACTOR != 0: sys.exit(f"Error: Total images ({n_images}) not divisible by DUPLICATION_FACTOR ({DUPLICATION_FACTOR}).")

    original_n_bits = n_images // DUPLICATION_FACTOR
    print(f"[*] Found {n_images} images, representing {original_n_bits} original bits.")

    gt_flag_bits = None
    if args.flag_file:
        if not args.flag_file.is_file(): sys.exit(f"Error: Flag file not found at '{args.flag_file}'")
        flag_bytes = args.flag_file.read_bytes()
        gt_flag_bits = np.unpackbits(np.frombuffer(flag_bytes, dtype=np.uint8), bitorder='little')
        if len(gt_flag_bits) != original_n_bits: sys.exit(f"Error: Flag file has {len(gt_flag_bits)} bits, but expected {original_n_bits}.")
        print(f"[*] Loaded ground truth flag with {len(gt_flag_bits)} bits for final comparison.")

    device = "mps"

    print(f"\n[*] Stage 1: Getting CLIP and Laplacian data...")
    classifier_p16 = Classifier(model="openai/clip-vit-base-patch16", device=device)
    classifier_p32 = Classifier(model="openai/clip-vit-base-patch32", device=device)
    all_data = [{} for _ in range(n_images)]

    with torch.no_grad():
        for i in tqdm(range(0, n_images, CLIP_BATCH_SIZE), desc="CLIP Processing"):
            batch_indices = range(i, min(i + CLIP_BATCH_SIZE, n_images))
            images = [Image.open(image_paths[j]) for j in batch_indices]
            px_p16 = classifier_p16.preprocess(images).to(device)
            p16_logits = classifier_p16(px_p16).cpu().numpy()
            px_p32 = classifier_p32.preprocess(images).to(device)
            p32_logits = classifier_p32(px_p32).cpu().numpy()
            for j, idx in enumerate(batch_indices):
                all_data[idx]['p16_logits'] = p16_logits[j]
                all_data[idx]['p32_logits'] = p32_logits[j]

    with Pool(processes=cpu_count()) as pool:
        laplacian_results = list(tqdm(pool.imap(process_laplacian_image, image_paths), total=n_images, desc="Laplacian"))
    for res in laplacian_results: all_data[res['idx']].update(res)

    print("\n[*] Stage 2: Applying voting logic and printing detailed analysis...")
    flag_bits = np.zeros(original_n_bits, dtype=int)
    non_confident_cases, split_decision_cases = [], []

    for original_idx in range(original_n_bits):
        print("-" * 110)
        print(f"Analyzing Original Bit Index: {original_idx}")

        if original_idx in MANUAL_INSPECTION:
            flag_bits[original_idx] = int(MANUAL_INSPECTION[original_idx])
            print("  -> Final Result: MANUAL OVERRIDE ->", "ATTACKED" if flag_bits[original_idx] else "Unattacked")
            continue

        votes = {"conf_attack": 0, "conf_unattacked": 0}
        group_slopes, duplicates_data = [], []

        for group_idx in range(DUPLICATION_FACTOR):
            actual_idx = original_idx + group_idx * original_n_bits
            data = all_data[actual_idx]
            slope = data['slope']
            group_slopes.append(slope)
            
            p16_l, p32_l = data['p16_logits'], data['p32_logits']
            p16_l_str = f"[{p16_l[0]:>6.2f},{p16_l[1]:>6.2f}]"
            p32_l_str = f"[{p32_l[0]:>6.2f},{p32_l[1]:>6.2f}]"

            reason = "Ambiguous"
            if abs(slope) <= STRONG_ATTACK_SLOPE:
                votes["conf_attack"] += 1; reason = "Confident Attack"
            elif abs(slope) >= STRONG_NORMAL_SLOPE:
                votes["conf_unattacked"] += 1; reason = "Confident Unattacked"
            
            data.update({"reason": reason, "actual_idx": actual_idx})
            duplicates_data.append(data)
            print(f"  - Group {group_idx} (Img {actual_idx}): P16L={p16_l_str}, P32L={p32_l_str}, Slope={slope:<7.4f} -> Vote: {reason}")

        final_decision_is_attacked, decision_reason_summary = False, ""
        
        if votes["conf_attack"] > votes["conf_unattacked"]:
            final_decision_is_attacked = True
            decision_reason_summary = f"Confident Majority ({votes['conf_attack']} vs {votes['conf_unattacked']})"
            if votes["conf_unattacked"] > 0:
                split_decision_cases.append({
                    "original_idx": original_idx, "title_reason": "Split Decision",
                    "duplicates": duplicates_data, "final_result": "ATTACKED"
                })
        elif votes["conf_unattacked"] > votes["conf_attack"]:
            final_decision_is_attacked = False
            decision_reason_summary = f"Confident Majority ({votes['conf_unattacked']} vs {votes['conf_attack']})"
            if votes["conf_attack"] > 0:
                split_decision_cases.append({
                    "original_idx": original_idx, "title_reason": "Split Decision",
                    "duplicates": duplicates_data, "final_result": "Unattacked"
                })
        else: # Tie or no confident votes
            mean_slope = np.mean(group_slopes)
            midpoint = (STRONG_ATTACK_SLOPE + STRONG_NORMAL_SLOPE) / 2
            final_decision_is_attacked = abs(mean_slope) < midpoint
            reason_prefix = "Confident Tie" if votes["conf_attack"] > 0 else "No Confident Votes"
            decision_reason_summary = f"{reason_prefix} -> Mean Slope ({mean_slope:.4f})"
            non_confident_cases.append({
                "original_idx": original_idx, "title_reason": "Non-Confident Decision", "mean_slope": mean_slope,
                "duplicates": duplicates_data, "final_result": "ATTACKED" if final_decision_is_attacked else "Unattacked"
            })
        
        flag_bits[original_idx] = int(final_decision_is_attacked)
        result_str = "ATTACKED" if final_decision_is_attacked else "Unattacked"
        print(f"  -> Votes [Conf A/U: {votes['conf_attack']}/{votes['conf_unattacked']}] -> Reason: {decision_reason_summary} -> FINAL RESULT: {result_str}")

    if args.plot_dir:
        all_cases_to_plot = non_confident_cases + split_decision_cases
        if all_cases_to_plot:
            print(f"\n[*] Stage 3: Plotting {len(all_cases_to_plot)} non-confident/split-decision cases...")
            args.plot_dir.mkdir(parents=True, exist_ok=True)
            plot_task = partial(create_plot_worker, output_dir=args.plot_dir)
            with Pool(processes=cpu_count()) as pool:
                list(tqdm(pool.imap(plot_task, all_cases_to_plot), total=len(all_cases_to_plot), desc="Plotting"))
            print(f"[*] Plots saved to '{args.plot_dir.absolute()}'")

    print("\n" + "="*50); print("Analysis Complete.")
    
    if split_decision_cases:
        print(f"\n[!] WARNING: {len(split_decision_cases)} bits had split confident votes:")
        print(f"    Indices: {[case['original_idx'] for case in split_decision_cases]}")
    if non_confident_cases:
        print(f"\n[!] NOTICE: {len(non_confident_cases)} bits were decided by mean slope (non-confident):")
        print(f"    Indices: {[case['original_idx'] for case in non_confident_cases]}")
    
    if gt_flag_bits is not None:
        incorrect_indices = np.where(flag_bits != gt_flag_bits)[0]
        if len(incorrect_indices) > 0:
            print("\n--- [DEBUG] Incorrect Predictions ---"); print(f"Found {len(incorrect_indices)} incorrect bits: {incorrect_indices.tolist()}")
        else:
            print("\n--- [DEBUG] All predictions match the ground truth flag! ---")

    final_flag_bytes = np.packbits(flag_bits, bitorder='little').tobytes()
    print("\n[+] Flag successfully generated:"); print(final_flag_bytes)

if __name__ == "__main__":
    main()
