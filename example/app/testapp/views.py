import random
from html import escape
from pathlib import Path
from pprint import pformat

from django.http import HttpResponse

MODULE_DIR = Path(__file__).resolve(strict=True).parent


def index(request):
    headers = pformat(dict(request.headers))
    params = pformat(dict(request.GET))
    request_context = pformat(request.environ.get("apig_wsgi.request_context", None))
    full_event = pformat(request.environ.get("apig_wsgi.full_event", None))
    environ = pformat(request.environ)

    response = HttpResponse(
        f"""
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
            <h2>Cookies</h2>
            <ul>
                <li>
                  testcookie:
                  <pre>{escape(repr(request.COOKIES.get('testcookie')))}</pre>
                </li>
                <li>
                  testcookie2:
                  <pre>{escape(repr(request.COOKIES.get('testcookie2')))}</pre>
                </li>
                <li>
                  testcookie3:
                  <pre>{escape(repr(request.COOKIES.get('testcookie3')))}</pre>
                </li>
            </ul>
          </body>
        </html>
        """
    )
    response.set_cookie(
        "testcookie", str(random.randint(0, 1_000_000)), samesite="strict"
    )
    response.set_cookie(
        "testcookie2", str(random.randint(0, 1_000_000)), samesite="strict"
    )
    response.set_cookie(
        "testcookie3",
        'escaped double quote \\" escaped comma \\054',
        samesite="strict",
    )
    return response


def favicon(request):
    return HttpResponse(
        (MODULE_DIR / "favicon.ico").read_bytes(),
        content_type="image/x-icon",
    )
