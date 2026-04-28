"""Auto-download GeoNames dumps to the geordie cache directory."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import requests

from ..linkers.base import get_cache_dir

logger = logging.getLogger(__name__)

GEONAMES_BASE_URL = "https://download.geonames.org/export/dump/"

KNOWN_DUMPS = {
    "cities500":    "cities500.zip",
    "cities1000":   "cities1000.zip",
    "cities5000":   "cities5000.zip",
    "cities15000":  "cities15000.zip",
    "allCountries": "allCountries.zip",
}


def get_geonames_cache_dir() -> Path:
    """Return (and create) ``~/.cache/geordie/geonames/``."""
    d = get_cache_dir() / "geonames"
    d.mkdir(parents=True, exist_ok=True)
    return d


def download_geonames_dump(
    dump: str = "cities15000",
    force: bool = False,
) -> Path:
    """
    Download and unzip a GeoNames dump into ``~/.cache/geordie/geonames/``.

    Skips the download if the ``.txt`` file already exists, unless ``force=True``.

    Parameters
    ----------
    dump :
        One of ``"cities500"``, ``"cities1000"``, ``"cities5000"``,
        ``"cities15000"`` (default), or ``"allCountries"``.
    force :
        Re-download and overwrite even if the file already exists.

    Returns
    -------
    Path
        Path to the extracted ``.txt`` file.

    Examples
    --------
    >>> from geordie.utils.download import download_geonames_dump
    >>> path = download_geonames_dump("cities15000")
    >>> print(path)
    /home/user/.cache/geordie/geonames/cities15000.txt
    """
    if dump not in KNOWN_DUMPS:
        raise ValueError(
            f"Unknown dump {dump!r}. Choose from: {sorted(KNOWN_DUMPS)}"
        )

    cache_dir = get_geonames_cache_dir()
    zip_filename = KNOWN_DUMPS[dump]
    txt_filename = zip_filename.replace(".zip", ".txt")
    zip_path = cache_dir / zip_filename   # ← fix: was missing
    txt_path = cache_dir / txt_filename   # ← fix: was missing

    # Skip if already extracted                  ← fix: entire block was missing
    if txt_path.exists() and not force:
        logger.info("GeoNames dump already cached: %s", txt_path)
        return txt_path

    # ------------------------------------------------------------------ download
    url = GEONAMES_BASE_URL + zip_filename
    logger.info("Downloading GeoNames dump: %s -> %s", url, zip_path)
    print(f"Downloading {url} ...")

    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=65_536):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                mb = downloaded / 1_048_576
                print(f"\r  {pct:5.1f}%  ({mb:.1f} MB)", end="", flush=True)
    print()

    # ------------------------------------------------------------------ extract
    logger.info("Extracting %s ...", zip_path)
    print(f"Extracting {zip_path.name} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member.lower().endswith(".txt") and "readme" not in member.lower():
                zf.extract(member, cache_dir)
                logger.info("Extracted: %s", cache_dir / member)

    # Clean up zip to save space
    zip_path.unlink()
    logger.info("Removed zip: %s", zip_path)

    if not txt_path.exists():
        raise FileNotFoundError(
            f"Extraction finished but expected file not found: {txt_path}"
        )

    print(f"Done — GeoNames dump ready at: {txt_path}")
    return txt_path