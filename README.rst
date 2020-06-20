=========
apig-wsgi
=========

.. image:: https://github.com/adamchainz/apig-wsgi/workflows/CI/badge.svg?branch=master
   :target: https://github.com/adamchainz/apig-wsgi/actions?workflow=CI

.. image:: https://img.shields.io/pypi/v/apig-wsgi.svg
   :target: https://pypi.org/project/apig-wsgi/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/python/black

Wrap a WSGI application in an AWS Lambda handler function for running on
API Gateway or an ALB.

A quick example:

.. code-block:: python

    from apig_wsgi import make_lambda_handler
    from myapp.wsgi import app

    # Configure this as your entry point in AWS Lambda
    lambda_handler = make_lambda_handler(app)


Installation
============

Use **pip**:

.. code-block:: sh

    python -m pip install apig-wsgi

Python 3.5 to 3.8 supported.

Usage
=====

``make_lambda_handler(app, binary_support=False, non_binary_content_type_prefixes=None)``
-----------------------------------------------------------------------------------------

``app`` should be a WSGI app, for example from Django's ``wsgi.py`` or Flask's
``Flask()`` object.

If you want to support sending binary responses, set ``binary_support`` to
``True``. ALB's support binary responses by default, but on API Gateway you
need to make sure you have ``'*/*'`` in the 'binary media types' configuration
on your Rest API. You will need to configure this through API Gateway directly,
CloudFormation, SAM, or whatever tool your project is using. Whilst API Gateway
supports a list of binary media types, using ``'*/*'`` is the best way to
configure this, since it is used to match the request 'Accept' header as well,
which WSGI applications are likely to ignore.

Note that binary responses aren't sent if your response has a 'Content-Type'
starting 'text/', 'application/json' or 'application/vnd.api+json' - this
is to support sending larger text responses. To support other content types
than the ones specified above, you can set ``non_binary_content_type_prefixes``
to a list of content type prefixes of your choice.

If the event from API Gateway contains the ``requestContext`` key, for example
from custom request authorizers, this will be available in the WSGI environ
at the key ``apig_wsgi.request_context``.

If you want to inspect the full event from API Gateway, it's available in the
WSGI environ at the key ``apig_wsgi.full_event``.

If you need the
`Lambda Context object <https://docs.aws.amazon.com/lambda/latest/dg/python-context.html>`__,
it's available in the WSGI environ at the key ``apig_wsgi.context``.

Multiple values for headers and query parameters are supported. They are
enabled automatically on API Gateway but need
`explict activation on ALB's <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html#multi-value-headers>`__.

Example
=======

An example application with Ansible deployment is provided in the ``example/``
directory in the repository. See the ``README.rst`` there for guidance.
