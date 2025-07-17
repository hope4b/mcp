from __future__ import annotations
from typing import Any, Callable

class Response:
    def __init__(self, json_data: Any = None) -> None:
        self._json = json_data or {}

    def raise_for_status(self) -> None:
        pass

    def json(self) -> Any:
        return self._json

def get(url: str, *args: Any, **kwargs: Any) -> Response:
    if 'response' in kwargs:
        return kwargs['response']
    return Response()
