import torch
import torch.nn as nn
from transformers import CLIPModel, CLIPProcessor
from typing import List
from PIL import Image

class Classifier(nn.Module):
    """
    A PyTorch module that uses the CLIP model to classify images as 'cat' or 'dog'.

    This classifier computes image features and compares them against pre-computed
    text features for "a photo of a cat" and "a photo of a dog", and return the
    resulting similarities (logits). Note that they don't sum up to 1.
    """

    def __init__(
        self,
        model: str = "openai/clip-vit-base-patch16",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        """
        Initializes the Classifier, loads the CLIP model and processor,
        and pre-computes text features.

        You can set `local_files_only=True` after downloading it for
        the first time to avoid network requests to huggingface.
        """
        super().__init__()
        self.device = device

        # Load the pre-trained CLIP model and its processor
        # You can set `local_files_only=True` to avoid
        # network requests to huggingface
        self.model = CLIPModel.from_pretrained(model, local_files_only=False).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model, local_files_only=False)

        # Define the text labels for classification
        self.labels = ["a photo of a cat", "a photo of a dog"]

        # Process the text labels and compute their features.
        # This is done within torch.no_grad() to ensure the resulting tensor
        # does not require gradients.
        text_inputs = self.processor(text=self.labels, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            text_features = self.model.get_text_features(**text_inputs)
        text_features = text_features.requires_grad_(False)

        # Register text features as a buffer. Buffers are part of the module's state
        # but are not considered model parameters.
        self.register_buffer('text_features', text_features)

    def preprocess(self, images: List[Image.Image]) -> torch.Tensor:
        """
        Preprocesses a list of PIL images into a tensor suitable for the CLIP model.

        Args:
            images: A list of PIL Images.

        Returns:
            A tensor of pixel values ready to be fed into the forward method.
        """
        inputs = self.processor(images=images, return_tensors="pt", padding=True)
        return inputs['pixel_values'].to(self.device)

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        """
        Performs the forward pass of the classifier using pre-processed image tensors.

        Args:
            pixel_values: A batch of pre-processed image tensors of the size
                          expected by the CLIP model (e.g., Bx3x224x224).

        Returns:
            A tensor of shape (B, 2) on the same device as the model, where B is
            the batch size. Each row contains the logits for the
            classes [cat, dog].
        """
        # Extract image features using the CLIP model.
        # Gradients will be computed for this part if requires_grad is True.
        image_features = self.model.get_image_features(pixel_values=pixel_values)

        # Normalize both image and text features for cosine similarity calculation.
        # self.text_features is a buffer and does not require gradients.
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        text_features = self.text_features / self.text_features.norm(p=2, dim=-1, keepdim=True)

        # Calculate the cosine similarity between image and text features.
        # This results in the logits for each class.
        # (B, 512) @ (512, 2) -> (B, 2)
        logits = image_features @ text_features.t()

        return logits

if __name__ == '__main__':
    # This block demonstrates how to use the Classifier class.
    # It will be executed only when the script is run directly.
    import requests

    print("Running a quick demonstration of the Classifier.")

    # Initialize the classifier
    classifier = Classifier()
    print(f"Classifier is running on device: {classifier.device}")

    # URL of a sample image (a cat)
    url = "http://images.cocodataset.org/val2017/000000039769.jpg"

    # Download and open the image
    image = Image.open(requests.get(url, stream=True).raw)

    # The classifier expects a batch, so we wrap the single image in a list
    image_batch = [image]

    # 1. Preprocess the image(s) to get the required tensor
    pixel_values = classifier.preprocess(image_batch)
    print(f"\nImage tensor shape after preprocessing: {pixel_values.shape}")

    # 2. Pass the pre-processed tensor to the forward method
    logits = classifier(pixel_values)

    # Move the output tensor to the CPU for printing and further processing
    # if it was computed on a different device.
    logits_cpu = logits.cpu().detach()

    print(f"Image URL: {url}")
    print(f"Logits (cat=0, dog=1): {logits_cpu.numpy()}")

    # Determine the predicted class
    predicted_index = torch.argmax(logits_cpu, dim=1).item()
    predicted_label = ["cat", "dog"][predicted_index]

    print(f"Predicted class: {predicted_label} ({predicted_index})")
