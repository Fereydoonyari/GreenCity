"""Vegetation analysis infrastructure package."""

from greencity.infrastructure.imagery.pipeline import NumpyVegetationPipeline

__all__ = ["HlsEarthAccessAdapter", "LandsatThermalAdapter", "NumpyVegetationPipeline"]


def __getattr__(name: str):
    """Lazy-load satellite adapters so unit tests can import the NDVI pipeline alone."""

    if name == "HlsEarthAccessAdapter":
        from greencity.infrastructure.imagery.hls import HlsEarthAccessAdapter

        return HlsEarthAccessAdapter
    if name == "LandsatThermalAdapter":
        from greencity.infrastructure.imagery.landsat import LandsatThermalAdapter

        return LandsatThermalAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
