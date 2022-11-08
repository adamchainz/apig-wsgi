from __future__ import annotations

import os
import random
from html import escape
from pathlib import Path
from pprint import pformat

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse

MODULE_DIR = Path(__file__).resolve(strict=True).parent

UNSAFE_OS_ENVIRON_KEYS = frozenset(
    (
        "_X_AMZN_TRACE_ID",
        "AWS_ACCESS_KEY_ID",
        "AWS_LAMBDA_FUNCTION_NAME",
        "AWS_LAMBDA_LOG_GROUP_NAME",
        "AWS_LAMBDA_LOG_STREAM_NAME",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    )
)


def index(request: WSGIRequest) -> HttpResponse:
    headers = pformat(dict(request.headers))
    params = pformat(dict(request.GET))
    request_context = pformat(request.environ.get("apig_wsgi.request_context", None))
    full_event = pformat(request.environ.get("apig_wsgi.full_event", None))
    environ = pformat(request.environ)
    os_environ = pformat(
        {
            k: ("*****" if k in UNSAFE_OS_ENVIRON_KEYS else v)
            for k, v in os.environ.items()
        }
    )

    response = HttpResponse(
        f"""
        <!doctype html>
        <html>
          <head>
            <title>apig-wsgi test app</title>
            <link rel="shortcut icon" type="image/x-icon" href="./favicon.ico">
          </head>
          <body>
            <h1>Hello World!</h1>
            <h2>Headers</h2>
            <pre>{escape(headers)}</pre>
            <h2>Query Params</h2>
            <pre>{escape(params)}</pre>
            <h2>Request Context</h2>
            <pre>{escape(request_context)}</pre>
            <h2>Full event</h2>
            <pre>{escape(full_event)}</pre>
            <h2>WSGI Environ</h2>
            <pre>{escape(environ)}</pre>
            <h2>Environment Variables</h2>
            <pre>{escape(os_environ)}</pre>
          </body>
        </html>
        """
    )
    response.set_cookie(
        "testcookie", str(random.randint(0, 1_000_000)), samesite="Strict"
    )
    response.set_cookie(
        "testcookie2", str(random.randint(0, 1_000_000)), samesite="Strict"
    )
    return response


def favicon(request: WSGIRequest) -> HttpResponse:
    return HttpResponse(
        (MODULE_DIR / "favicon.ico").read_bytes(),
        content_type="image/x-icon",
    )
