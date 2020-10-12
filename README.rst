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

Python 3.5 to 3.9 supported.

----

**Deploying a Django Project?**
Check out my book `Speed Up Your Django Tests <https://gumroad.com/l/suydt>`__ which covers loads of best practices so you can write faster, more accurate tests.

----

Usage
=====

Use apig-wsgi in your lambda function that you attach to one of:

* An ALB.
* An API Gateway “REST API”.
* An API Gateway “HTTP API”.

Both “format version 1” and “format version 2” are supported
(`documentation <https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html>`__).
apig-wsgi will automatically detect the version in use. At time of writing,
“format version 2” is only supported on HTTP API’s.

``make_lambda_handler(app, binary_support=None, non_binary_content_type_prefixes=None)``
----------------------------------------------------------------------------------------

``app`` should be a WSGI app, for example from Django's ``wsgi.py`` or Flask's
``Flask()`` object.

``binary_support`` configures whether responses containing binary are
supported. The default, ``None``, means to automatically detect this from the
format version of the event - on it defaults to ``True`` for format version 2,
and ``False`` for format version 1. Depending on how you're deploying your
lambda function, you may need extra configuration before you can enable binary
responses:

* ALB’s support binary responses by default.
* API Gateway HTTP API’s support binary responses by default (and default to
  event format version 2).
* API Gateway REST API’s (the “old” style) require you to add ``'*/*'`` in the
  “binary media types” configuration. You will need to configure this through
  API Gateway directly, CloudFormation, SAM, or whatever tool your project is
  using. Whilst this supports a list of binary media types, using ``'*/*'`` is
  the best way to configure it, since it is used to match the request 'Accept'
  header as well, which WSGI applications often ignore. You may need to delete
  and recreate your stages for this value to be copied over.

Note that binary responses aren't sent if your response has a 'Content-Type'
starting 'text/', 'application/json' or 'application/vnd.api+json' - this
is to support sending larger text responses, since the base64 encoding would
otherwise inflate the content length. To avoid base64 encoding other content
types, you can set ``non_binary_content_type_prefixes`` to a list of content
type prefixes of your choice (which replaces the default list).

If the event from API Gateway contains the ``requestContext`` key, for example
on format version 2 or from custom request authorizers, this will be available
in the WSGI environ at the key ``apig_wsgi.request_context``.

If you want to inspect the full event from API Gateway, it's available in the
WSGI environ at the key ``apig_wsgi.full_event``.

If you need the
`Lambda Context object <https://docs.aws.amazon.com/lambda/latest/dg/python-context.html>`__,
it's available in the WSGI environ at the key ``apig_wsgi.context``.

If you’re using “format version 1”, multiple values for request and response
headers and query parameters are supported. They are enabled automatically on
API Gateway but need `explict activation on
ALB’s <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html#multi-value-headers>`__.
If you need to determine from within your application if multiple header values
are enabled, you can can check the ``apgi_wsgi.multi_value_headers`` key in the
WSGI environ, which is ``True`` if they are enabled and ``False`` otherwise.

Example
=======

An example application with Ansible deployment is provided in the ``example/``
directory in the repository. See the ``README.rst`` there for guidance.
