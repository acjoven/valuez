"""Unit handling for valuez, backed by `pint <https://pint.readthedocs.io>`_.

This module centralizes the (optional) `pint` integration so the rest of the
platform never imports `pint` directly:

- :func:`validate_unit` checks a unit string against pint's registry at value
  construction time, catching typos/undefined units early. It preserves the
  caller's original spelling (e.g. ``"kg"`` stays ``"kg"``) rather than
  rewriting to pint's canonical form.
- :func:`to_quantity` is a thin, *optional* bridge to pint's ``Quantity`` type.
  Deeper quantity integration (unit conversion, dimensional arithmetic across
  values) is intentionally left as future work.

If `pint` is not installed the module degrades gracefully: units are accepted
as-is (no validation) and :func:`to_quantity` raises a clear error.
"""
from __future__ import annotations

from typing import Any, Optional

try:  # pint is the intended dependency, but stay usable without it.
    import pint  # type: ignore

    _UREG: Optional["pint.UnitRegistry"] = pint.UnitRegistry()
    _PINT_ERROR: Optional[Exception] = None
except Exception as exc:  # pragma: no cover - only hit when pint is absent
    pint = None  # type: ignore
    _UREG = None
    _PINT_ERROR = exc

__all__ = ["pint_available", "unit_registry", "validate_unit", "to_quantity"]


def pint_available() -> bool:
    """Whether pint is importable in this environment."""
    return _UREG is not None


def unit_registry() -> Any:
    """Return the shared pint ``UnitRegistry`` (or ``None`` if pint is absent)."""
    return _UREG


def validate_unit(unit: Optional[str]) -> Optional[str]:
    """Validate a unit string, returning it (stripped) unchanged.

    Returns ``None`` for ``None``/empty input. Raises ``TypeError`` for
    non-strings and ``ValueError`` when pint is available and the unit is not
    recognized. When pint is unavailable the unit is accepted as-is.
    """
    if unit is None:
        return None
    if not isinstance(unit, str):
        raise TypeError("unit must be a string or None")
    stripped = unit.strip()
    if not stripped:
        return None
    if _UREG is not None:
        try:
            _UREG.Unit(stripped)
        except Exception as exc:
            raise ValueError(f"Unrecognized unit {stripped!r}: {exc}") from exc
    return stripped


def to_quantity(magnitude: Any, unit: Optional[str]) -> Any:
    """Wrap a magnitude and unit as a pint ``Quantity`` (optional convenience).

    This is the seam for future quantity integration; it requires pint.
    """
    if _UREG is None:
        raise RuntimeError(
            "pint is not installed; install 'pint' to use quantity support"
        ) from _PINT_ERROR
    if not unit:
        return _UREG.Quantity(magnitude)
    return _UREG.Quantity(magnitude, unit)
