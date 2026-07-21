"""Retired weak forecast entry points.

Future predictions are only valid when the C11 Situation/World Model freezes
their evidence, verification contract, contradiction contract, and expiry.
"""

from typing import NoReturn


WORLD_MODEL_PREDICTION_OWNER = (
    "matters.analysis.world_inference.PersistentAdvisoryWorldModel.publish"
)


class ForecastEntryPointRetiredError(RuntimeError):
    """Raised when code tries to use the removed lightweight forecast route."""


def reject_weak_forecast_entrypoint() -> NoReturn:
    raise ForecastEntryPointRetiredError(
        "forecast_entrypoint_retired: future predictions must use the unique "
        f"World Model prediction owner {WORLD_MODEL_PREDICTION_OWNER}"
    )


class Forecast:
    """Compatibility-shaped tombstone that always rejects direct construction."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        reject_weak_forecast_entrypoint()


__all__ = [
    "Forecast",
    "ForecastEntryPointRetiredError",
    "WORLD_MODEL_PREDICTION_OWNER",
    "reject_weak_forecast_entrypoint",
]
