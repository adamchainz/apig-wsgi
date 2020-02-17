from html import escape
from pprint import pformat

from django.http import HttpResponse


def index(request):
    headers = pformat(dict(request.headers))
    params = pformat(dict(request.GET))
    request_context = pformat(request.environ.get("apig_wsgi.request_context", None))
    full_event = pformat(request.environ.get("apig_wsgi.full_event", None))
    return HttpResponse(
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
        """
    )
