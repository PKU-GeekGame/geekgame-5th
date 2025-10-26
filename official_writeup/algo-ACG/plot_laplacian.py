import argparse
import sys
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np
import matplotlib.pyplot as plt

def get_laplacian_noise_map(image: Image.Image) -> Image.Image:
    """
    Applies a Laplacian filter to an image and normalizes the result
    to create a visible map of high-frequency noise and edges.

    Returns:
        A new 8-bit grayscale PIL Image representing the noise map.
    """
    # 1. Convert to grayscale ('L') for the filter.
    grayscale_image = image.convert('L')

    # 2. Define and apply the Laplacian kernel.
    laplacian_kernel = (
        0,  1,  0,
        1, -4,  1,
        0,  1,  0
    )
    kernel = ImageFilter.Kernel(
        size=(3, 3),
        kernel=laplacian_kernel,
        scale=1
    )
    laplacian_image = grayscale_image.filter(kernel)

    # 3. Convert to NumPy, take absolute value, and normalize to 0-255.
    laplacian_array = np.array(laplacian_image)
    abs_laplacian = np.abs(laplacian_array)
    if abs_laplacian.max() > 0:
        normalized_array = (abs_laplacian / abs_laplacian.max()) * 255
    else:
        normalized_array = abs_laplacian # Handle pure black images

    # 4. Convert back to a visible PIL Image.
    return Image.fromarray(normalized_array.astype(np.uint8))

def main():
    parser = argparse.ArgumentParser(
        description="Plot the brightness distribution of an image after applying a Laplacian kernel.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--image", type=Path, required=True, help="Path to the input image file.")
    parser.add_argument("--output", type=Path, required=True, help="Path to save the output plot PNG file.")
    args = parser.parse_args()

    if not args.image.is_file():
        print(f"Error: Image file not found at '{args.image}'", file=sys.stderr)
        sys.exit(1)

    # --- Image Processing ---
    print(f"[*] Loading and processing image: {args.image}")
    try:
        original_image = Image.open(args.image)
        noise_map_image = get_laplacian_noise_map(original_image)
    except Exception as e:
        print(f"Error: Could not process image. {e}", file=sys.stderr)
        sys.exit(1)

    # Convert the final noise map to a 1D list of pixel values for the histogram
    laplacian_pixel_values = np.array(noise_map_image).flatten()

    # --- Plotting ---
    print(f"[*] Generating brightness distribution plot...")
    fig, ax = plt.subplots(figsize=(10, 6))

    # We use a logarithmic scale on the y-axis because the number of dark pixels
    # (value 0) will be orders of magnitude higher than other pixels. A log scale
    # makes the rest of the distribution visible.
    ax.hist(laplacian_pixel_values, bins=256, range=(0, 256), color='navy', log=True)

    ax.set_title(f'Laplacian Brightness Distribution for "{args.image.name}"')
    ax.set_xlabel('Pixel Brightness (0=Black, 255=White)')
    ax.set_ylabel('Pixel Count (Logarithmic Scale)')
    ax.set_xlim(0, 255)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # --- Saving Output ---
    print(f"[*] Saving plot to: {args.output}")
    try:
        plt.savefig(args.output, dpi=150)
    except Exception as e:
        print(f"Error: Could not save plot. {e}", file=sys.stderr)
        sys.exit(1)
        
    print("[+] Done.")
    # Optional: uncomment the line below to show the plot interactively
    # plt.show()


if __name__ == "__main__":
    main()
