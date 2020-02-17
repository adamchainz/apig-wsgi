import html
from pprint import pformat

from django.http import HttpResponse


def index(request):
    return HttpResponse(
        f"""
        <h1>Hello World!</h1>
        <h2>Query Params</h2>
        <pre>{html.escape(pformat(request.GET))}</pre>
        """
    )
