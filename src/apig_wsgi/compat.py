from __future__ import annotations

import sys

__all__ = ["WSGIApplication"]

if sys.version_info >= (3, 11):
    from wsgiref.types import WSGIApplication
else:
    # Partial backport of wsgiref.types
    from collections.abc import Iterable
    from types import TracebackType
    from typing import Any
    from typing import Callable
    from typing import Protocol
    from typing import Union

    _ExcInfo = tuple[type[BaseException], BaseException, TracebackType]
    _OptExcInfo = Union[_ExcInfo, tuple[None, None, None]]

    class StartResponse(Protocol):
        """start_response() callable as defined in PEP 3333"""

        def __call__(
            self,
            status: str,
            headers: list[tuple[str, str]],
            exc_info: _OptExcInfo | None = ...,
            # /,
        ) -> Callable[[bytes], object]: ...  # pragma: no cover

    WSGIEnvironment = dict[str, Any]
    WSGIApplication = Callable[[WSGIEnvironment, StartResponse], Iterable[bytes]]
