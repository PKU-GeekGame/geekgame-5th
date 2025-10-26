import sys
from typing import List
import torch
import torchattacks
from PIL import Image
from tqdm import tqdm
from torchvision.transforms.functional import to_pil_image

from clip_classifier import Classifier

try:
    from clip_constants import CLIP_IMAGE_MEAN, CLIP_IMAGE_STD
except ImportError:
    print("Error: Could not import from 'clip_constants'.")
    print("It is part of the challenge to find the correct mean and std values.")
    sys.exit(1)

# --- Constants ---
MAX_ATTACK_ATTEMPTS = 20

# Batch size for running the attack. Limited by VRAM during the backward pass.
ATTACK_BATCH_SIZE = 32

# Batch size for running predictions. Can be larger as it's only a forward pass.
PREDICT_BATCH_SIZE = 128

def unnormalize(t: torch.Tensor) -> torch.Tensor:
    """
    Reverses the normalization on a tensor (image) that was normalized with
    CLIP's specific mean and standard deviation.

    Args:
        tensor: A PyTorch tensor of shape (C, H, W) or (B, C, H, W).

    Returns:
        A PyTorch tensor with values unnormalized, ready to be converted to a PIL Image.
    """
    mean = torch.tensor(CLIP_IMAGE_MEAN, device=t.device, dtype=t.dtype).view(3, 1, 1)
    std = torch.tensor(CLIP_IMAGE_STD, device=t.device, dtype=t.dtype).view(3, 1, 1)
    unnormalized_tensor = t.mul(std).add(mean)
    return unnormalized_tensor

def attack(
    images: List[Image.Image],
    target_labels: List[int],
    classifier: Classifier
) -> List[Image.Image]:
    """
    Performs a targeted PGD adversarial attack on a batch of images.

    Args:
        images: A list of PIL.Image.Image objects to be attacked.
        target_labels: A list of integer labels (0 for 'cat', 1 for 'dog')
                       corresponding to each image. The attack will try to make
                       the classifier predict this label for the image.
        classifier: An initialized instance of the Classifier class to attack.

    Returns:
        A list of PIL.Image.Image objects. Each image is either a successfully
        attacked version of the original or the original image itself if the
        attack failed (very rarely) within the given attempts.
    """
    if len(images) != len(target_labels):
        raise ValueError("The number of images must match the number of target labels.")

    device = classifier.device
    attacked_images = [None] * len(images)
    remaining_indices = list(range(len(images)))

    for attempt in range(MAX_ATTACK_ATTEMPTS):
        if not remaining_indices:
            print("All attacks succeeded.")
            break

        print(f"--- Attack Attempt {attempt + 1}/{MAX_ATTACK_ATTEMPTS} | Images remaining: {len(remaining_indices)} ---")

        bases = [images[i] for i in remaining_indices]
        targets = torch.tensor([target_labels[i] for i in remaining_indices], device=device, dtype=torch.long)
        adv_values = torch.zeros(len(bases), 3, 224, 224, device=device)

        attack_op = torchattacks.PGD(
            classifier,
            eps=8/255,
            alpha=2/255,
            steps=attempt // 2 + 1,
            random_start=True
        )
        attack_op.set_normalization_used(mean=CLIP_IMAGE_MEAN, std=CLIP_IMAGE_STD)
        attack_op.set_mode_targeted_by_label(quiet=True)

        # --- Batch Processing Loop for Attack ---
        for i in tqdm(range(0, len(bases), ATTACK_BATCH_SIZE), desc="  Attacking batch"):
            sub_images = bases[i:i+ATTACK_BATCH_SIZE]
            sub_targets = targets[i:i+ATTACK_BATCH_SIZE]
            px_values = classifier.preprocess(sub_images).to(device)
            adv_values[i:i+len(sub_images)] = attack_op(px_values, sub_targets)

        # --- Batch Processing Loop for Prediction (to save VRAM) ---
        with torch.no_grad():
            num_adv_images = adv_values.shape[0]
            predictions = torch.zeros(num_adv_images, dtype=torch.long, device=device)
            for i in tqdm(range(0, num_adv_images, PREDICT_BATCH_SIZE), desc="  Predicting batch"):
                batch_adv_values = adv_values[i:i+PREDICT_BATCH_SIZE]
                batch_predictions = torch.argmax(classifier(batch_adv_values), dim=1)
                predictions[i:i+len(batch_predictions)] = batch_predictions

        # --- Check for Success ---
        successful_mask = (predictions == targets)
        if torch.any(successful_mask):
            successful_original_indices = [remaining_indices[i] for i, succ in enumerate(successful_mask) if succ]
            successful_adv_images = unnormalize(adv_values[successful_mask].cpu())

            for j, adv_tensor in enumerate(successful_adv_images):
                original_image_idx = successful_original_indices[j]
                attacked_images[original_image_idx] = to_pil_image(adv_tensor.clamp_(0, 1))

        remaining_indices = [idx for i, idx in enumerate(remaining_indices) if not successful_mask[i]]

    if remaining_indices:
        raise RuntimeError(f"{len(remaining_indices)} images could not be successfully attacked, please increase MAX_ATTACK_ATTEMPTS.")

    return attacked_images
