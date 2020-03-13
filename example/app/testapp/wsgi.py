import json
import os

from apig_wsgi import make_lambda_handler
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testapp.settings')

application = get_wsgi_application()

apig_wsgi_handler = make_lambda_handler(application)


def lambda_handler(event, context):
    print(json.dumps(event, indent=2, sort_keys=True))
    return apig_wsgi_handler(event, context)
