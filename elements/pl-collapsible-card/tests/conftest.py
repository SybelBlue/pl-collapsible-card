from __future__ import annotations

import sys
from pathlib import Path

ELEMENT_ROOT = Path(__file__).resolve().parents[1]
if str(ELEMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(ELEMENT_ROOT))
