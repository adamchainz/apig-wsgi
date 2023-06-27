from __future__ import annotations

import sys

__all__ = ["WSGIApplication"]

if sys.version_info >= (3, 11):
    from wsgiref.types import WSGIApplication
else:
    # Partial backport of wsgiref.types
    from types import TracebackType
    from typing import Any, Callable, Dict, Iterable, Tuple, Type, Union

    from typing import Protocol

    _ExcInfo = Tuple[Type[BaseException], BaseException, TracebackType]
    _OptExcInfo = Union[_ExcInfo, Tuple[None, None, None]]

    class StartResponse(Protocol):
        """start_response() callable as defined in PEP 3333"""

        def __call__(
            self,
            status: str,
            headers: list[tuple[str, str]],
            exc_info: _OptExcInfo | None = ...,
            # /,
        ) -> Callable[[bytes], object]:
            ...  # pragma: no cover

    WSGIEnvironment = Dict[str, Any]
    WSGIApplication = Callable[[WSGIEnvironment, StartResponse], Iterable[bytes]]
