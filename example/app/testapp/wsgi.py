from __future__ import annotations

import json
import os
from typing import Any

from django.core.wsgi import get_wsgi_application

from apig_wsgi import make_lambda_handler

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")

application = get_wsgi_application()

apig_wsgi_handler = make_lambda_handler(application, binary_support=True)


def lambda_handler(event: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    print(json.dumps(event, indent=2, sort_keys=True))
    response = apig_wsgi_handler(event, context)
    print(json.dumps(response, indent=2, sort_keys=True))
    return response
