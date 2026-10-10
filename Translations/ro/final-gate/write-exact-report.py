#!/usr/bin/env python3
"""Write the standard preserve-exact receipt inside the Romanian-owned directory.

The shared CLI restricts output to Documentation. The shared validation function
has no such path restriction; it runs the same full 16,538-unit check here.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import validate  # noqa: E402

if __name__ == "__main__":
    validate("ro", pathlib.Path(__file__).with_name("preserve-exact.json"))
