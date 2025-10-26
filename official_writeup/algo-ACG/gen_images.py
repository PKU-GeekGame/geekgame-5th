import argparse
import logging
import random
import sys
from pathlib import Path
from itertools import count
from typing import List
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import torch
from PIL import Image
from tqdm import tqdm
from torchvision.transforms.functional import to_pil_image

from clip_classifier import Classifier
from attack import attack, unnormalize

# --- Constants ---
# BATCH_SIZE is used for pre-classifying images and generating normal images.
# The attack-specific batch size is handled within attack.py
BATCH_SIZE = 64

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gen.log", mode='w'),
        logging.StreamHandler()
    ]
)

# --- Image Provider Class ---
class ImageProvider:
    """Manages providing images from a list of paths."""
    def __init__(self, name: str, image_paths: List[Path], shuffle_seed: int = None):
        self.name = name
        self.prefetched_images = list(image_paths)
        self.current_index = 0

        if not self.prefetched_images:
            raise ValueError(f"ImageProvider '{name}' was initialized with zero images.")

        if shuffle_seed is not None:
            random.Random(shuffle_seed).shuffle(self.prefetched_images)
        else:
            random.shuffle(self.prefetched_images)
        logging.info("Initialized ImageProvider '%s' with %d images.", self.name, len(self.prefetched_images))

    def get_image(self) -> Image.Image:
        """Gets the next image from the list, looping if necessary."""
        if self.current_index >= len(self.prefetched_images):
            self.current_index = 0
            logging.warning("Looping over images for provider '%s'.", self.name)

        image_path = self.prefetched_images[self.current_index]
        self.current_index += 1
        return Image.open(image_path).convert("RGB")

def save_image_worker(image_to_save: Image.Image, path: Path):
    """Helper function to save a single PIL image, for use with ThreadPoolExecutor."""
    image_to_save.save(path, "PNG")

# --- Main Generation Logic ---
def main():
    parser = argparse.ArgumentParser(description="Generate images for the Advanced CLIP Geometry challenge.")
    parser.add_argument("--hint-file", type=Path, required=True, help="Path to the hint file (read as bytes).")
    parser.add_argument("--flag-file", type=Path, required=True, help="Path to the flag file (read as bytes).")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to save the generated images.")
    parser.add_argument("--flag-duplicate", type=int, required=True, help="Number of times to duplicate the flag bits.")
    # Use one of the following two options to set the mode
    parser.add_argument("--flag1-images-dir", type=Path, help="Use Flag 1 mode. Path to dir with 'dogs' and 'cats' subfolders.")
    parser.add_argument("--flag2-images-dir", type=Path, help="Use Flag 2 mode. Path to dir with 'confuser' animal images.")
    # Optional arguments
    parser.add_argument("--max-bytes", type=int, help="Maximum number of bytes from the original flag to process before duplication.")
    parser.add_argument("--shuffle-seed", type=int, help="Seed for shuffling image lists for reproducibility.")
    args = parser.parse_args()

    # --- 1. Validate Arguments and Determine Mode ---
    if not (args.flag1_images_dir or args.flag2_images_dir):
        sys.exit("Error: You must specify either --flag1-images-dir or --flag2-images-dir.")
    if args.flag1_images_dir and args.flag2_images_dir:
        sys.exit("Error: Please specify only one of --flag1-images-dir or --flag2-images-dir.")

    mode = "flag1" if args.flag1_images_dir else "flag2"
    logging.info(f"--- Starting Image Generation in {mode.upper()} MODE ---")

    # --- 2. Load, Duplicate, and Prepare Bit Data ---
    hint_bytes = args.hint_file.read_bytes()
    flag_bytes = args.flag_file.read_bytes()

    if args.max_bytes:
        # Note: max_bytes applies to the *original* flag length, before duplication.
        flag_bytes = flag_bytes[:args.max_bytes]

    if args.flag_duplicate <= 0:
        sys.exit("Error: --flag-duplicate must be a positive integer.")

    duplicated_flag_bytes = flag_bytes * args.flag_duplicate
    n_bits = len(duplicated_flag_bytes) * 8
    attack_mask = np.unpackbits(np.frombuffer(duplicated_flag_bytes, dtype=np.uint8), bitorder='little')

    if n_bits == 0:
        logging.warning("No data found in flag file after processing. Exiting."); return

    hint_bits = np.unpackbits(np.frombuffer(hint_bytes, dtype=np.uint8), bitorder='little')
    if len(hint_bits) > n_bits:
        raise ValueError(f"Hint file contains {len(hint_bits)} bits, which is more than the total generated image count of {n_bits}.")

    hint_bits = np.pad(hint_bits, (0, n_bits - len(hint_bits)), 'constant', constant_values=0)
    logging.info(f"Original flag has {len(flag_bytes)*8} bits. Duplicating {args.flag_duplicate} times.")
    logging.info(f"Total number of images to generate: {n_bits}")

    # --- 3. Setup Classifier and Output Directory ---
    device = "cuda" if torch.cuda.is_available() else "cpu"
    classifier = Classifier(device=device).eval()

    args.output_dir.mkdir(exist_ok=True)
    for i in count(n_bits):
        if not (stale_file := args.output_dir / f"{i}.png").exists(): break
        stale_file.unlink()

    # --- 4. Initialize Image Providers Based on Mode ---
    dog_provider, cat_provider = None, None
    if mode == "flag1":
        logging.info("Initializing Flag 1 image providers...")
        dog_paths = sorted((args.flag1_images_dir / "dogs").glob("*.*"))
        cat_paths = sorted((args.flag1_images_dir / "cats").glob("*.*"))
        dog_provider = ImageProvider("dog", dog_paths, args.shuffle_seed)
        cat_provider = ImageProvider("cat", cat_paths, args.shuffle_seed)
    else: # mode == "flag2"
        logging.info("Initializing Flag 2 image providers...")
        all_image_paths = sorted(list(args.flag2_images_dir.glob("*.jpg")) + list(args.flag2_images_dir.glob("*.png")))
        if not all_image_paths:
            sys.exit(f"Error: No .jpg or .png images found in '{args.flag2_images_dir}'")

        logging.info(f"Pre-classifying {len(all_image_paths)} confuser images...")
        dog_pool_paths, cat_pool_paths = [], []
        with torch.no_grad():
            for i in tqdm(range(0, len(all_image_paths), BATCH_SIZE), desc="Pre-classifying"):
                batch_paths = all_image_paths[i:i+BATCH_SIZE]
                images = [Image.open(p).convert("RGB") for p in batch_paths]
                pixel_values = classifier.preprocess(images).to(device)
                preds = torch.argmax(classifier(pixel_values), dim=1).cpu().tolist()
                for path, pred in zip(batch_paths, preds):
                    if pred == 1: dog_pool_paths.append(path)
                    else: cat_pool_paths.append(path)

        dog_provider = ImageProvider("dog_pool", dog_pool_paths, args.shuffle_seed)
        cat_provider = ImageProvider("cat_pool", cat_pool_paths, args.shuffle_seed)

    # --- 5. Main Generation Logic ---
    final_ground_truth_bits = [None] * n_bits
    images_to_save = [None] * n_bits

    # --- Phase 1: Generate all UNATTACKED images (Batched) ---
    logging.info("--- Phase 1: Generating all unattacked images ---")
    unattacked_indices = [i for i, is_attacked in enumerate(attack_mask) if not is_attacked]
    if unattacked_indices:
        logging.info(f"Gathering {len(unattacked_indices)} base images for unattacked set...")
        unattacked_base_images = []
        for i in unattacked_indices:
            ground_truth_bit = bool(hint_bits[i])
            final_ground_truth_bits[i] = ground_truth_bit
            provider_to_use = dog_provider if ground_truth_bit else cat_provider
            unattacked_base_images.append(provider_to_use.get_image())

        logging.info("Batch processing and unnormalizing unattacked images...")
        with torch.no_grad():
            for i in tqdm(range(0, len(unattacked_indices), BATCH_SIZE), desc="Generating normal images"):
                batch_indices = unattacked_indices[i:i + BATCH_SIZE]
                batch_images_pil = unattacked_base_images[i:i + BATCH_SIZE]
                
                pixel_values = classifier.preprocess(batch_images_pil).to(device)
                unnormalized_tensors = unnormalize(pixel_values.cpu()).clamp_(0, 1)

                for j, original_idx in enumerate(batch_indices):
                    images_to_save[original_idx] = to_pil_image(unnormalized_tensors[j])

    # --- Phase 2: Prepare and execute BATCHED ATTACK ---
    attack_indices = [i for i, is_attacked in enumerate(attack_mask) if is_attacked]
    if attack_indices:
        logging.info("--- Phase 2: Preparing base images for attack ---")
        attack_base_images, attack_targets = [], []
        for i in tqdm(attack_indices, desc="Finding suitable base images"):
            hint_bit, ground_truth_bit = bool(hint_bits[i]), not bool(hint_bits[i])
            final_ground_truth_bits[i] = ground_truth_bit
            attack_targets.append(int(hint_bit))

            provider_to_use = dog_provider if ground_truth_bit else cat_provider
            while True:
                candidate_image = provider_to_use.get_image()
                pixel_values = classifier.preprocess([candidate_image]).to(device)
                with torch.no_grad():
                    prediction = int(torch.argmax(classifier(pixel_values), dim=1).item())
                if prediction == ground_truth_bit:
                    attack_base_images.append(candidate_image)
                    break

        logging.info("--- Phase 3: Executing attack using the imported attack function ---")
        attacked_pil_images = attack(
            images=attack_base_images,
            target_labels=attack_targets,
            classifier=classifier
        )

        for i, pil_image in enumerate(attacked_pil_images):
            original_image_idx = attack_indices[i]
            images_to_save[original_image_idx] = pil_image

    # --- 6. Finalization (Concurrent Saving) ---
    logging.info("--- Phase 4: Saving all images and ground truth ---")
    for i in range(n_bits):
        if images_to_save[i] is None or final_ground_truth_bits[i] is None:
            raise RuntimeError(f"Data for index {i} was not generated.")

    save_tasks = [(images_to_save[i], args.output_dir / f"{i}.png") for i in range(n_bits)]
    with ThreadPoolExecutor() as executor:
        list(tqdm(executor.map(lambda p: save_image_worker(*p), save_tasks), total=len(save_tasks), desc="Saving images"))

    gt_path = Path("ground_truth_generated.bin")
    gt_bytes = np.packbits(np.array(final_ground_truth_bits, dtype=np.uint8), bitorder='little').tobytes()
    gt_path.write_bytes(gt_bytes)

    logging.info("Successfully saved ground truth to '%s'.", gt_path)
    logging.info("--- Image Generation Complete ---")

if __name__ == "__main__":
    main()
