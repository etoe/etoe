"""Lossless serialization of ÆToE notation into programming-language identifiers."""

from __future__ import annotations

import base64

_PREFIX = "etoe_"
_B64_PREFIX = "etoe_b64_"


def encode_identifier(text: str) -> str:
    """Encode arbitrary UTF-8 notation as a Python-compatible identifier."""
    payload = text.encode("utf-8").hex()
    return _PREFIX + payload


def decode_identifier(identifier: str) -> str:
    if not identifier.startswith(_PREFIX) or identifier.startswith(_B64_PREFIX):
        raise ValueError("Not an etoe hex identifier")
    return bytes.fromhex(identifier[len(_PREFIX):]).decode("utf-8")


def encode_base64url_identifier(text: str) -> str:
    """Encode UTF-8 using base64url and escape '-'/'_' for identifier safety."""
    raw = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")
    safe = raw.replace("_", "_u").replace("-", "_h")
    return _B64_PREFIX + safe


def decode_base64url_identifier(identifier: str) -> str:
    if not identifier.startswith(_B64_PREFIX):
        raise ValueError("Not an etoe base64url identifier")
    safe = identifier[len(_B64_PREFIX):]
    raw = safe.replace("_h", "-").replace("_u", "_")
    raw += "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8")
