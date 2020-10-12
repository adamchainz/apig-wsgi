import json
import os

from django.core.wsgi import get_wsgi_application

from apig_wsgi import make_lambda_handler

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")

application = get_wsgi_application()

apig_wsgi_handler = make_lambda_handler(application, binary_support=True)


def lambda_handler(event, context):
    print(json.dumps(event, indent=2, sort_keys=True))
    response = apig_wsgi_handler(event, context)
    print(json.dumps(response, indent=2, sort_keys=True))
    return response
