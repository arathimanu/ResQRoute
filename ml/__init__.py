def __getattr__(name):
    if name in (
        "RoadConditionPrediction",
        "predict_road_condition",
        "SUPPORTED_IMAGE_EXTENSIONS",
        "VALID_ROAD_STATUSES",
    ):
        from . import road_condition
        return getattr(road_condition, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "RoadConditionPrediction",
    "predict_road_condition",
    "SUPPORTED_IMAGE_EXTENSIONS",
    "VALID_ROAD_STATUSES",
]
