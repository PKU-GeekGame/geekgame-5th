import argparse
import logging
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO
from tqdm import tqdm

# --- Constants ---
DOG_API_URL = "https://api.thedogapi.com/v1/images/search"
CAT_API_URL = "https://api.thecatapi.com/v1/images/search"
MAX_DIMENSION = 512

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def resize_image_if_needed(image: Image.Image) -> Image.Image:
    """
    Resizes an image if its largest dimension exceeds MAX_DIMENSION,
    while maintaining the original aspect ratio.
    """
    width, height = image.size
    if max(width, height) <= MAX_DIMENSION:
        return image

    if width > height:
        new_width = MAX_DIMENSION
        new_height = int(height * (MAX_DIMENSION / width))
    else:
        new_height = MAX_DIMENSION
        new_width = int(width * (MAX_DIMENSION / height))

    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def process_existing_images(directory: Path):
    """Checks all images in a directory and resizes them if they are too large."""
    logging.info("Checking existing images in '%s' for resizing...", directory)
    
    existing_images = list(directory.glob("*.png")) + list(directory.glob("*.jpg"))
    if not existing_images:
        return

    for image_path in tqdm(existing_images, desc=f"Processing {directory.name}"):
        try:
            with Image.open(image_path) as img:
                original_size = img.size
                img.load()
                
            img = Image.open(image_path)
            resized_img = resize_image_if_needed(img)
            
            if resized_img.size != original_size:
                new_path = directory / f"{image_path.stem}.png"
                resized_img.save(new_path, "PNG")
                if image_path.suffix.lower() != ".png":
                    image_path.unlink()

        except Exception as e:
            logging.warning("Could not process existing image %s: %s", image_path, e)


def fetch_and_save_images(url: str, animal: str, target_num_images: int, output_dir: Path, resize_existing: bool):
    """
    Ensures the output directory has a total of target_num_images, fetching only the missing ones.
    Optionally processes existing images in the directory to meet size constraints.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if resize_existing:
        process_existing_images(output_dir)
    else:
        logging.info("Skipping resizing of existing images in '%s' as requested.", output_dir)
    
    # Count how many valid images we already have
    existing_image_count = len(list(output_dir.glob("*.png")))
    
    # Calculate how many new images are needed to reach the target
    num_to_fetch = target_num_images - existing_image_count

    if num_to_fetch <= 0:
        logging.info(
            "Directory '%s' already contains %d images (target is %d). Nothing to fetch.", 
            output_dir, existing_image_count, target_num_images
        )
        return
        
    logging.info(
        "Directory '%s' has %d images. Prefetching %d new %s images to reach the target of %d...",
        output_dir, existing_image_count, num_to_fetch, animal, target_num_images
    )
    
    start_index = existing_image_count
    
    progress_bar = tqdm(range(num_to_fetch), desc=f"Fetching {animal.capitalize()} Images")
    for i in progress_bar:
        saved = False
        while not saved:
            try:
                response = requests.get(url)
                response.raise_for_status()
                image_url = response.json()[0]['url']
                
                image_response = requests.get(image_url)
                image_response.raise_for_status()
                
                image = Image.open(BytesIO(image_response.content)).convert("RGB")
                
                resized_image = resize_image_if_needed(image)
                
                # Save with an incrementing index, starting from the current count
                resized_image.save(output_dir / f"{start_index + i}.png", "PNG")
                saved = True
                
            except requests.RequestException as e:
                logging.warning("API call failed: %s. Retrying...", e)
            except (KeyError, IndexError):
                logging.warning("Unexpected API response format. Retrying...")

def main():
    parser = argparse.ArgumentParser(description="Prefetch and resize dog/cat images to a local cache.")
    parser.add_argument("--output-dir", type=Path, default=Path("prefetched_images"), help="Directory to store the prefetched images.")
    parser.add_argument("--num-dogs", type=int, required=True, help="The target total number of dog images in the cache.")
    parser.add_argument("--num-cats", type=int, required=True, help="The target total number of cat images in the cache.")
    parser.add_argument(
        "--resize-existing",
        action="store_true",
        help="If set, check and resize images already in the output directory."
    )
    args = parser.parse_args()
    
    should_resize_existing = args.resize_existing
    
    fetch_and_save_images(DOG_API_URL, "dog", args.num_dogs, args.output_dir / "dogs", resize_existing=should_resize_existing)
    fetch_and_save_images(CAT_API_URL, "cat", args.num_cats, args.output_dir / "cats", resize_existing=should_resize_existing)
    
    logging.info("Image prefetching and processing complete.")

if __name__ == "__main__":
    main()
