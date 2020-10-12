import random
from html import escape
from pprint import pformat

from django.http import HttpResponse


def index(request):
    headers = pformat(dict(request.headers))
    params = pformat(dict(request.GET))
    request_context = pformat(request.environ.get("apig_wsgi.request_context", None))
    full_event = pformat(request.environ.get("apig_wsgi.full_event", None))
    environ = pformat(request.environ)

    response = HttpResponse(
        f"""
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
        """
    )
    response.set_cookie(
        "testcookie", str(random.randint(0, 1_000_000)), samesite="strict"
    )
    response.set_cookie(
        "testcookie2", str(random.randint(0, 1_000_000)), samesite="strict"
    )
    return response
