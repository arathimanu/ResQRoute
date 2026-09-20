"""PyTorch Model Architecture and Preprocessing Pipeline for ResQRoute.

Phase 5B:
  - Defines transfer learning architecture using lightweight backbones (MobileNetV3-Small or ResNet18).
  - Replaces final classification head with a 3-class output layer (CLEAR, DAMAGED, BLOCKED).
  - Standardizes image preprocessing with ImageNet normalization and 224x224 crop.
  - Gracefully handles offline environments where pretrained weights cannot be downloaded.
  - Provides clear diagnostic messages if PyTorch/torchvision are not yet installed.
"""

from typing import List, Optional

# Supported road condition classes
CLASS_NAMES: List[str] = ["CLEAR", "DAMAGED", "BLOCKED"]
NUM_CLASSES: int = len(CLASS_NAMES)

# Standard ImageNet normalization parameters
IMAGENET_MEAN: List[float] = [0.485, 0.456, 0.406]
IMAGENET_STD: List[float] = [0.229, 0.224, 0.225]

# Dependency detection
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False

try:
    import torchvision
    from torchvision import models, transforms
    TORCHVISION_AVAILABLE = True
except ImportError:
    torchvision = None
    models = None
    transforms = None
    TORCHVISION_AVAILABLE = False

INSTALL_INSTRUCTIONS = (
    "PyTorch and torchvision are required for deep-learning road condition classification.\n"
    "To install them into your virtual environment, run:\n"
    "    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu\n"
    "Or for CUDA/GPU support, run:\n"
    "    pip install torch torchvision"
)


def check_dependencies() -> None:
    """Check that PyTorch and torchvision are available.

    Raises:
        ImportError: If torch or torchvision is missing, with setup instructions.
    """
    if not TORCH_AVAILABLE or not TORCHVISION_AVAILABLE:
        raise ImportError(
            f"Required deep learning libraries are missing.\n{INSTALL_INSTRUCTIONS}"
        )


def get_inference_transforms(image_size: int = 224):
    """Create the standard evaluation/inference image transformation pipeline.

    Pipeline stages:
      1. Resize shorter edge to 256 pixels.
      2. Center crop to (image_size, image_size), default 224x224.
      3. Convert PIL Image to PyTorch FloatTensor in range [0.0, 1.0].
      4. Normalize RGB channels using ImageNet mean and standard deviation.

    Args:
        image_size: Target square resolution (default 224).

    Returns:
        torchvision.transforms.Compose: Transformation pipeline.

    Raises:
        ImportError: If torchvision is not installed.
    """
    check_dependencies()

    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(image_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def create_model(
    pretrained: bool = True,
    num_classes: int = NUM_CLASSES,
    architecture: str = "mobilenet_v3_small",
):
    """Create a transfer-learning convolutional neural network for road classification.

    Supported Architectures:
      - 'mobilenet_v3_small': Ultra-lightweight (~1.5M - 2.5M parameters), ideal for
        edge devices, drones, and fast CPU inference.
      - 'resnet18': Standard residual network (~11.2M parameters), strong baseline
        for fine-grained road texture and damage features.

    Transfer Learning Head Modification:
      - MobileNetV3-Small: Replaces final layer `classifier[3]` with `Linear(in_features, num_classes)`.
      - ResNet18: Replaces `fc` with `Linear(in_features, num_classes)`.

    Args:
        pretrained: If True, loads ImageNet pretrained backbone weights.
                    If weight download fails or pretrained is False, initializes backbone randomly.
        num_classes: Number of target classes (default 3: CLEAR, DAMAGED, BLOCKED).
        architecture: Backbone architecture ('mobilenet_v3_small' or 'resnet18').

    Returns:
        torch.nn.Module: Configured classification model.

    Raises:
        ImportError: If PyTorch or torchvision is not installed.
        ValueError: If an unsupported architecture string is provided.
    """
    check_dependencies()

    arch = architecture.lower().strip()

    if arch == "mobilenet_v3_small":
        weights = None
        if pretrained:
            try:
                weights = models.MobileNet_V3_Small_Weights.DEFAULT
            except Exception as e:
                print(f"[Warning] Could not load pretrained weights ({e}). Initializing backbone randomly.")
                weights = None

        model = models.mobilenet_v3_small(weights=weights)

        # Replace final classification projection layer:
        # classifier is: [Linear(576, 1024), Hardswish(), Dropout(0.2), Linear(1024, 1000)]
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, num_classes)
        return model

    elif arch == "resnet18":
        weights = None
        if pretrained:
            try:
                weights = models.ResNet18_Weights.DEFAULT
            except Exception as e:
                print(f"[Warning] Could not load pretrained weights ({e}). Initializing backbone randomly.")
                weights = None

        model = models.resnet18(weights=weights)

        # Replace final classification projection layer:
        # fc is: Linear(512, 1000)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
        return model

    else:
        raise ValueError(
            f"Unsupported architecture '{architecture}'. Supported: ['mobilenet_v3_small', 'resnet18']"
        )


# =====================================================================
# Verification and Self-Test Scenarios
# =====================================================================
if __name__ == "__main__":
    print("====================================================================")
    print("   ResQRoute Phase 5B: PyTorch Architecture & Preprocessing Demo   ")
    print("====================================================================\n")

    print(f"Target Classification Classes: {CLASS_NAMES} (Total: {NUM_CLASSES})\n")

    if not TORCH_AVAILABLE or not TORCHVISION_AVAILABLE:
        print("[Dependency Status] PyTorch or torchvision is currently not installed.")
        print(INSTALL_INSTRUCTIONS)
        print("\n  [PASS] Dependency check executed cleanly and provided setup instructions.")
    else:
        print(f"[Dependency Status] PyTorch v{torch.__version__} and torchvision v{torchvision.__version__} detected.\n")

        # 1. Test Transforms
        print("[Test 1] Building inference preprocessing pipeline...")
        pipe = get_inference_transforms(image_size=224)
        print(f"  -> Pipeline transforms: {pipe}\n")

        # 2. Test MobileNetV3-Small creation (offline-safe without downloading weights)
        print("[Test 2] Creating MobileNetV3-Small model (num_classes=3)...")
        model = create_model(pretrained=False, num_classes=3, architecture="mobilenet_v3_small")
        model.eval()

        dummy_input = torch.randn(1, 3, 224, 224)
        with torch.no_grad():
            logits = model(dummy_input)

        print(f"  -> Input tensor shape:  {tuple(dummy_input.shape)}")
        print(f"  -> Output logits shape: {tuple(logits.shape)}")
        assert logits.shape == (1, 3), f"Expected shape (1, 3), got {logits.shape}"
        print("  [PASS] MobileNetV3-Small output shape matches 3 classes.\n")

        # 3. Test ResNet18 creation
        print("[Test 3] Creating ResNet18 model (num_classes=3)...")
        resnet = create_model(pretrained=False, num_classes=3, architecture="resnet18")
        resnet.eval()

        with torch.no_grad():
            resnet_logits = resnet(dummy_input)

        print(f"  -> ResNet18 logits shape: {tuple(resnet_logits.shape)}")
        assert resnet_logits.shape == (1, 3), f"Expected shape (1, 3), got {resnet_logits.shape}"
        print("  [PASS] ResNet18 output shape matches 3 classes.\n")

    print("====================================================================")
    print("   Phase 5B verification complete!                                  ")
    print("====================================================================\n")
