from __future__ import annotations

"""Raw HTTP credential classification for the public MCP endpoint."""

import contextvars
from collections.abc import Iterable


X_API_KEY = b"x-api-key"
X_ONTO_API_KEY = b"x-onto-api-key"
AUTHORIZATION = b"authorization"


class InvalidHttpCredentials(ValueError):
    """The request contains an ambiguous or malformed API-key credential set."""


_HTTP_API_KEY: contextvars.ContextVar[bytes | None] = contextvars.ContextVar(
    "onto_http_api_key",
    default=None,
)


def _ascii_lower(value: bytes) -> bytes:
    return bytes(byte + 32 if 0x41 <= byte <= 0x5A else byte for byte in value)


def _is_bearer(value: bytes) -> bool:
    candidate = value.lstrip(b" \t")
    if len(candidate) < 6 or _ascii_lower(candidate[:6]) != b"bearer":
        return False
    return len(candidate) == 6 or candidate[6] in (0x20, 0x09)


def _validate_value(value: bytes) -> None:
    if not value or all(byte in (0x20, 0x09) for byte in value) or b"," in value:
        raise InvalidHttpCredentials


def classify_http_api_key(headers: Iterable[tuple[bytes, bytes]]) -> bytes | None:
    """Resolve one raw API-key credential or fail closed on ambiguity.

    Header names are compared with ASCII case folding. Credential values are
    never stripped or otherwise normalized.
    """

    values: dict[bytes, list[bytes]] = {X_API_KEY: [], X_ONTO_API_KEY: []}
    has_bearer = False

    for raw_name, raw_value in headers:
        name = _ascii_lower(bytes(raw_name))
        value = bytes(raw_value)
        if name in values:
            values[name].append(value)
        elif name == AUTHORIZATION and _is_bearer(value):
            has_bearer = True

    standard = values[X_API_KEY]
    legacy = values[X_ONTO_API_KEY]
    if len(standard) > 1 or len(legacy) > 1:
        raise InvalidHttpCredentials

    supplied = standard + legacy
    if not supplied:
        return None

    for value in supplied:
        _validate_value(value)

    if len(supplied) == 2 and standard[0] != legacy[0]:
        raise InvalidHttpCredentials
    if has_bearer:
        raise InvalidHttpCredentials
    return supplied[0]


def set_http_api_key(value: bytes | None) -> contextvars.Token[bytes | None]:
    return _HTTP_API_KEY.set(value)


def reset_http_api_key(token: contextvars.Token[bytes | None]) -> None:
    _HTTP_API_KEY.reset(token)


def get_http_api_key() -> str | None:
    value = _HTTP_API_KEY.get()
    return value.decode("latin-1") if value is not None else None
