"""Introspection helpers for the vendored streamrip config schema."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import tomlkit

_VENDOR_CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "vendor"
    / "streamrip"
    / "streamrip"
    / "config.toml"
)

if not _VENDOR_CONFIG_PATH.exists():
    raise ImportError(
        f"Vendored streamrip config not found at {_VENDOR_CONFIG_PATH}. "
        "Ensure the vendor/streamrip submodule is initialised."
    )

STREAMRIP_DEFAULTS: tomlkit.TOMLDocument = tomlkit.parse(
    _VENDOR_CONFIG_PATH.read_text(encoding="utf-8")
)

STREAMRIP_SECTIONS: frozenset[str] = frozenset(STREAMRIP_DEFAULTS.keys())

MDL_EXTRA_SECTIONS: frozenset[str] = frozenset({"spotify"})


def iter_section_keys() -> Iterator[tuple[str, str]]:
    """Yield (section, key) for every leaf key in the streamrip defaults."""
    for section, values in STREAMRIP_DEFAULTS.items():
        if isinstance(values, dict):
            for key in values:
                yield (section, key)
        else:
            yield (section, str(values))
