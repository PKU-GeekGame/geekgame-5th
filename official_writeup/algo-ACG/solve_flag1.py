import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

# We will use the provided Classifier class.
# Ensure clip_classifier.py is in the same directory or accessible.
from clip_classifier import Classifier

# --- Constants ---
BATCH_SIZE = 256  # Adjust based on available VRAM
DUPLICATION_FACTOR = 3 # The number of duplicate images for each original bit

def main():
    parser = argparse.ArgumentParser(
        description="A robust solver for Level 1 using a voting system on duplicated images.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--images-dir", type=Path, default=Path("flag1_images"), help="The directory to read images from.")
    args = parser.parse_args()

    device = "mps"
    print(f"Using device: {device}", file=sys.stderr)

    # --- 1. Load Models ---
    print("Loading target classifier (vit-base-patch16)...", file=sys.stderr)
    target_classifier = Classifier("openai/clip-vit-base-patch16", device=device).eval()

    # --- 2. Find and Sort Image Files ---
    if not args.images_dir.exists():
        sys.exit(f"Error: Images directory not found at '{args.images_dir}'")

    image_paths = sorted(args.images_dir.glob("*.png"), key=lambda p: int(p.stem))

    n_images = len(image_paths)
    if n_images == 0:
        sys.exit(f"Error: No PNG images found in '{args.images_dir}'")
    if n_images % DUPLICATION_FACTOR != 0:
        sys.exit(f"Error: Total images ({n_images}) not divisible by DUPLICATION_FACTOR ({DUPLICATION_FACTOR}).")

    original_n_bits = n_images // DUPLICATION_FACTOR
    print(f"Found {n_images} images, representing {original_n_bits} original bits.", file=sys.stderr)

    # --- 3. First Pass: Get all hint bits from the target model ---
    all_hint_bits = np.zeros(n_images, dtype=int)
    print("\n[*] Stage 1: Classifying all images with target model (p16) to get hint...", file=sys.stderr)
    with torch.no_grad():
        for i in tqdm(range(0, n_images, BATCH_SIZE), desc="Getting hint bits"):
            batch_paths = image_paths[i:i + BATCH_SIZE]
            batch_images = [Image.open(p) for p in batch_paths]
            pixel_values = target_classifier.preprocess(batch_images)
            p16_preds = torch.argmax(target_classifier(pixel_values), dim=1).cpu().numpy()
            all_hint_bits[i:i + len(p16_preds)] = p16_preds

    # --- 4. Assemble and Print the Hint ---
    hint_bytes = np.packbits(all_hint_bits, bitorder='little').tobytes()
    print("\n[+] Recovered Hint (from target model's perspective):")
    print(hint_bytes)
    
    # --- 5. Second Pass: Compare models and vote on groups ---
    print("Loading ground truth classifier (vit-base-patch32)...", file=sys.stderr)
    gt_classifier = Classifier("openai/clip-vit-base-patch32", device=device).eval()

    final_flag_bits = np.zeros(original_n_bits, dtype=int)
    split_decision_cases = []
    print("\n[*] Stage 2: Comparing with ground truth model (p32) and voting...", file=sys.stderr)
    with torch.no_grad():
        for original_idx in tqdm(range(original_n_bits), desc="Analyzing image groups"):
            group_image_indices = [original_idx + i * original_n_bits for i in range(DUPLICATION_FACTOR)]
            group_image_paths = [image_paths[i] for i in group_image_indices]
            
            batch_images = [Image.open(p) for p in group_image_paths]
            px_p16 = target_classifier.preprocess(batch_images)
            px_p32 = gt_classifier.preprocess(batch_images)

            p16_preds = torch.argmax(target_classifier(px_p16), dim=1)
            p32_preds = torch.argmax(gt_classifier(px_p32), dim=1)
            
            votes = {"attack": 0, "unattacked": 0}
            is_attacked_group = (p16_preds != p32_preds).cpu().numpy()

            for vote_is_attack in is_attacked_group:
                if vote_is_attack:
                    votes["attack"] += 1
                else:
                    votes["unattacked"] += 1
            
            final_decision_is_attacked = votes["attack"] > votes["unattacked"]
            final_flag_bits[original_idx] = int(final_decision_is_attacked)

            if votes["attack"] > 0 and votes["unattacked"] > 0:
                split_decision_cases.append(original_idx)

    # --- 6. Final Report ---
    print("\n" + "="*50)
    print("Analysis Complete.")
    
    if split_decision_cases:
        print(f"\n[!] WARNING: {len(split_decision_cases)} bits had split votes (e.g., 2 attack, 1 unattacked):")
        print(f"    Indices: {split_decision_cases}")

    flag_bytes = np.packbits(final_flag_bits, bitorder='little').tobytes()
    num_attacked = sum(final_flag_bits)
    print(f"\nDetected {num_attacked} attacked original bits out of {original_n_bits}.", file=sys.stderr)

    print("\n[+] Recovered Flag (from voting):")
    print(flag_bytes)

if __name__ == '__main__':
    main()
