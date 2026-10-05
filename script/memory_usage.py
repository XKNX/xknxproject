"""
Measure the peak memory usage of parsing an ETS project and its application programs.

Run from the project directory:
    python3 -m script.memory_usage

This is run in CI to notice changes that increase the memory demand drastically -
eg. using `ElementTree.parse()` where `ElementTree.iterparse()` was used before.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import time
import tracemalloc

from xknxproject import XKNXProj

# The test project holding the biggest application program file (~10 MB uncompressed)
PROJECT_PATH = (
    Path(__file__).parent.parent / "test" / "resources" / "smart_linking.knxproj"
)
PROJECT_PASSWORD = "test"
PROJECT_LANGUAGE = "de-DE"

# Peak memory limit in MiB. Baseline is ~8 MiB - reading `knx_master.xml` into a
# full ElementTree accounts for most of it. Reading one of the application program
# files that way would add >50 MiB on its own.
DEFAULT_LIMIT = 24.0

MIB = 1024 * 1024


def main() -> int:
    """Measure each parsing operation separately and check its peak memory usage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=float,
        default=DEFAULT_LIMIT,
        help=f"fail if either operation exceeds this many MiB (default: {DEFAULT_LIMIT})",
    )
    args = parser.parse_args()

    knxproj = XKNXProj(PROJECT_PATH, PROJECT_PASSWORD, language=PROJECT_LANGUAGE)
    limit_exceeded = False
    for parse in (knxproj.parse, knxproj.parse_application_programs):
        tracemalloc.start()
        _start = time.perf_counter()
        parse()
        duration = time.perf_counter() - _start
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        peak_mib = peak / MIB
        print(f"### Memory usage of `{parse.__name__}()` for `{PROJECT_PATH.name}`")
        print()
        print(f"- Peak memory: **{peak_mib:.1f} MiB** (limit {args.limit:.1f} MiB)")
        print(f"- Parsing time: {duration:.2f} s")

        if peak_mib > args.limit:
            print()
            print(
                f"Peak memory exceeds the limit of {args.limit:.1f} MiB. "
                "Either reduce the memory demand or raise the limit "
                "in `script/memory_usage.py` deliberately."
            )
            limit_exceeded = True
    return int(limit_exceeded)


if __name__ == "__main__":
    raise SystemExit(main())
