# -*- coding: utf-8 -*-
"""
Official rmapV2 Research Area (審査区分) mapping loader.

Location:
  addons/metadata/suggestions/kaken/data/review_sections.json

Supported shape (hierarchical only):
[
  {
    "large_code": "A189",
    "large_name_ja": "…",
    "large_name_en": "…",              # optional
    "children": [
      {
        "small_code": "A38010" | "38010",
        "small_name_ja": "…",
        "small_name_en": "…"            # optional / may be absent
      }
    ]
  }
]

Notes:
- Only Basic Section (小区分) lookups are used by KAKEN suggestions.
- The loader normalizes codes like "A38010" to "38010" internally.
- Missing fields (e.g., small_name_en) are returned as empty strings.
"""

import json
import os
import re
from typing import Optional, Dict

_CACHE: Optional[Dict[str, Dict[str, str]]] = None


def _mapping_path() -> str:
    base = os.path.dirname(__file__)
    return os.path.join(base, 'data', 'review_sections.json')


def _load() -> Dict[str, Dict[str, str]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = _mapping_path()
    mapping: Dict[str, Dict[str, str]] = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Hierarchical shape only
        if isinstance(data, list):
            for lg in data:
                if not isinstance(lg, dict):
                    continue
                lg_code = str(lg.get('large_code') or '')
                lg_ja = lg.get('large_name_ja') or ''
                lg_en = lg.get('large_name_en') or ''
                for ch in lg.get('children') or []:
                    if not isinstance(ch, dict):
                        continue
                    sc_full = ch.get('small_code') or ''
                    # normalize: accept either letter+5 or 5 digits; store by 5 digits for lookup
                    m = None
                    if isinstance(sc_full, str):
                        m = re.match(r'^[A-Z]?(\d{5})$', sc_full)
                    sc5 = m.group(1) if m else ''
                    if len(sc5) == 5:
                        mapping[sc5] = {
                            'small_name_ja': ch.get('small_name_ja') or '',
                            'small_name_en': ch.get('small_name_en') or '',
                            'large_code': lg_code,
                            'large_name_ja': lg_ja,
                            'large_name_en': lg_en,
                        }
    _CACHE = mapping
    return _CACHE


def lookup_small(code5: str) -> Optional[Dict[str, str]]:
    """Return mapping record for a 5-digit Basic Section (小区分) code."""
    if not code5:
        return None
    return _load().get(str(code5).zfill(5))
