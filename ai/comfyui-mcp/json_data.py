"""Validate untyped JSON at the boundary of the sidecar's utility scripts."""

from __future__ import annotations

from typing import cast

JsonMapping = dict[str, object]


def mapping(value: object, name: str) -> JsonMapping:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")
    raw = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise TypeError(f"{name} keys must be strings")
    # Preserve the mapping's identity so nested workflow edits update the source.
    return cast(JsonMapping, raw)


def items(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a list")
    return cast(list[object], value)


def text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    return float(value)
