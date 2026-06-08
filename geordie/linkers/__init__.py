"""Entity linkers for geordie."""

from .base import BaseLinker


def __getattr__(name):
    if name == "NominatimLinker":
        from .nominatim import NominatimLinker
        return NominatimLinker
    if name == "GeoNamesLinker":
        from .geonames import GeoNamesLinker
        return GeoNamesLinker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["BaseLinker", "NominatimLinker", "GeoNamesLinker"]