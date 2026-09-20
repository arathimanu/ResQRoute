"""Road condition prediction interface for ResQRoute disaster management.

Phase 5:
  - Establishes a standard prediction contract (RoadConditionPrediction).
  - Validates image paths, extensions, road status classes, and confidence ranges.
  - Implements a placeholder function `predict_road_condition()` that returns safe,
    transparent default predictions without pretending to perform real ML.
  - Designed for seamless drop-in replacement by a PyTorch transfer-learning model in later phases.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional, Set

# Supported status classes matching RoadStatus in src/graph.py
VALID_ROAD_STATUSES: Set[str] = {"CLEAR", "DAMAGED", "BLOCKED"}

# Common image file extensions supported for road inspection
SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def validate_prediction_inputs(
    image_path: str,
    status: Optional[str] = None,
    confidence: Optional[float] = None,
    check_file_exists: bool = False,
) -> None:
    """Validate image path, status, and confidence parameters.

    Raises:
        ValueError: If image_path is empty, extension is unsupported, status is invalid,
                    or confidence is outside [0.0, 1.0].
        FileNotFoundError: If check_file_exists is True and image_path does not exist on disk.
    """
    # 1. Validate image path existence/type
    if not image_path or not isinstance(image_path, str) or not image_path.strip():
        raise ValueError("Image path cannot be empty or missing.")

    # 2. Validate file extension
    ext = Path(image_path).suffix.lower()
    if not ext or ext not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported image extension '{ext}'. Supported formats: {sorted(SUPPORTED_IMAGE_EXTENSIONS)}"
        )

    # 3. Optional physical file existence check
    if check_file_exists and not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found on disk: '{image_path}'")

    # 4. Validate road status
    if status is not None and status not in VALID_ROAD_STATUSES:
        raise ValueError(
            f"Invalid road condition status '{status}'. Must be one of: {sorted(VALID_ROAD_STATUSES)}"
        )

    # 5. Validate confidence range [0.0, 1.0]
    if confidence is not None:
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"Confidence score {confidence} must be a float in the range [0.0, 1.0]."
            )


@dataclass
class RoadConditionPrediction:
    """Standardized prediction output for disaster road imagery.

    Attributes:
        status: Predicted condition ('CLEAR', 'DAMAGED', 'BLOCKED').
        confidence: Prediction confidence score between 0.0 and 1.0.
        image_path: Path to the evaluated image file.
        message: Informative explanation or placeholder notice.
    """
    status: str
    confidence: float
    image_path: str
    message: str

    def __post_init__(self) -> None:
        """Validate fields upon instantiation."""
        validate_prediction_inputs(
            image_path=self.image_path,
            status=self.status,
            confidence=self.confidence,
            check_file_exists=False,
        )


def predict_road_condition(
    image_path: str,
    mock_status: Optional[str] = "CLEAR",
    mock_confidence: float = 0.85,
    check_file_exists: bool = False,
) -> RoadConditionPrediction:
    """Placeholder road-condition classifier for disaster imagery.

    NOTE ON ML IMPLEMENTATION:
      This is a placeholder function and DOES NOT perform real deep-learning inference.
      It returns a safe default prediction with an explicit status message indicating
      that it is a placeholder.

      If `mock_status` is explicitly set to None, it raises a `NotImplementedError`
      to signal that real PyTorch weights are required.

    Args:
        image_path: Path to the image file (e.g. aerial drone shot or street photo).
        mock_status: The mock status to return ('CLEAR', 'DAMAGED', 'BLOCKED'), or None
                     to raise NotImplementedError.
        mock_confidence: Simulated confidence score [0.0, 1.0].
        check_file_exists: If True, checks if the image exists on disk before predicting.

    Returns:
        RoadConditionPrediction: Validated prediction result.

    Raises:
        NotImplementedError: If mock_status is None (signaling real model requirement).
        ValueError: If validation of path, extension, status, or confidence fails.
        FileNotFoundError: If check_file_exists is True and file is missing.
    """
    # If explicitly configured without mock status, signal that real model is not implemented
    if mock_status is None:
        validate_prediction_inputs(image_path, check_file_exists=check_file_exists)
        raise NotImplementedError(
            "Real PyTorch transfer-learning model is not yet loaded. "
            "Pass mock_status ('CLEAR', 'DAMAGED', 'BLOCKED') or load weights in later phases."
        )

    # Validate all inputs
    validate_prediction_inputs(
        image_path=image_path,
        status=mock_status,
        confidence=mock_confidence,
        check_file_exists=check_file_exists,
    )

    filename = os.path.basename(image_path)
    return RoadConditionPrediction(
        status=mock_status,
        confidence=float(mock_confidence),
        image_path=str(image_path),
        message=f"[PLACEHOLDER] Mock prediction for '{filename}'. Real PyTorch classifier will replace this in later phase.",
    )


# =====================================================================
# Verification and Self-Test Scenarios
# =====================================================================
if __name__ == "__main__":
    print("====================================================================")
    print("   ResQRoute Phase 5: Road Condition ML Interface Self-Test         ")
    print("====================================================================\n")

    # --- Test 1: Valid Default Placeholder Prediction ---
    print("[Test 1] Standard Placeholder Prediction:")
    pred_1 = predict_road_condition("data/sample_road.jpg")
    print(f"  - Image:      {pred_1.image_path}")
    print(f"  - Status:     {pred_1.status}")
    print(f"  - Confidence: {pred_1.confidence}")
    print(f"  - Message:    {pred_1.message}")
    assert pred_1.status == "CLEAR"
    assert pred_1.confidence == 0.85
    assert "[PLACEHOLDER]" in pred_1.message
    print("  [PASS] Test 1: Valid default placeholder prediction generated.\n")

    # --- Test 2: Custom Mock Prediction (BLOCKED with 0.95 confidence) ---
    print("[Test 2] Custom Mock Prediction:")
    pred_2 = predict_road_condition("data/flood_debris.png", mock_status="BLOCKED", mock_confidence=0.95)
    print(f"  - Status:     {pred_2.status}")
    print(f"  - Confidence: {pred_2.confidence}")
    assert pred_2.status == "BLOCKED"
    assert pred_2.confidence == 0.95
    print("  [PASS] Test 2: Custom status and confidence correctly validated.\n")

    # --- Test 3: Validation Error - Missing Image Path ---
    print("[Test 3] Validation: Empty Image Path:")
    try:
        predict_road_condition("")
        assert False, "Should have raised ValueError for empty path!"
    except ValueError as e:
        print(f"  - Caught expected error: {e}")
        print("  [PASS] Test 3: Empty path properly rejected.\n")

    # --- Test 4: Validation Error - Unsupported Extension ---
    print("[Test 4] Validation: Unsupported Image Extension (.txt):")
    try:
        predict_road_condition("notes/report.txt")
        assert False, "Should have raised ValueError for unsupported extension!"
    except ValueError as e:
        print(f"  - Caught expected error: {e}")
        print("  [PASS] Test 4: Unsupported extension properly rejected.\n")

    # --- Test 5: Validation Error - Confidence Out of Bounds ---
    print("[Test 5] Validation: Out-of-Bounds Confidence (1.5 and -0.1):")
    try:
        predict_road_condition("data/road.jpg", mock_confidence=1.5)
        assert False, "Should have raised ValueError for confidence > 1.0!"
    except ValueError as e:
        print(f"  - Caught expected error (high): {e}")

    try:
        predict_road_condition("data/road.jpg", mock_confidence=-0.1)
        assert False, "Should have raised ValueError for confidence < 0.0!"
    except ValueError as e:
        print(f"  - Caught expected error (negative): {e}")
        print("  [PASS] Test 5: Out-of-bounds confidence properly rejected.\n")

    # --- Test 6: Validation Error - Invalid Road Status ---
    print("[Test 6] Validation: Invalid Road Status ('UNDERWATER'):")
    try:
        predict_road_condition("data/road.png", mock_status="UNDERWATER")
        assert False, "Should have raised ValueError for invalid status!"
    except ValueError as e:
        print(f"  - Caught expected error: {e}")
        print("  [PASS] Test 6: Invalid status properly rejected.\n")

    # --- Test 7: Explicit NotImplementedError when mock_status is None ---
    print("[Test 7] Signaling Real Model Requirement (mock_status=None):")
    try:
        predict_road_condition("data/road.jpg", mock_status=None)
        assert False, "Should have raised NotImplementedError!"
    except NotImplementedError as e:
        print(f"  - Caught expected error: {e}")
        print("  [PASS] Test 7: NotImplementedError raised when mock is disabled.\n")

    print("====================================================================")
    print("   All Phase 5 Road Condition ML Interface tests passed!           ")
    print("====================================================================\n")
