"""Simple CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="geordie",
        description="Geographic entity extraction, linking & role classification.",
    )
    parser.add_argument("text", nargs="?", help="Text to process (reads stdin if omitted)")
    parser.add_argument(
        "--backend",
        choices=["nominatim", "geonames"],
        default="nominatim",
        help="Entity linking backend (default: nominatim)",
    )
    parser.add_argument("--geonames-path", help="Path to GeoNames TSV file")
    parser.add_argument("--device", default=None, help="Computation device (cpu/cuda)")
    parser.add_argument("--no-cache", action="store_true", help="Disable persistent cache")
    args = parser.parse_args()

    from geordie import Geordie

    text = args.text or sys.stdin.read()
    if not text.strip():
        print("No input text provided.", file=sys.stderr)
        sys.exit(1)

    geordie = Geordie(
        device=args.device,
        linker_backend=args.backend,
        geonames_path=args.geonames_path,
        cache_path=None if args.no_cache else "geordie_cache.db",
    )
    results = geordie.process_text(text)
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
