History
-------

Pending Release
---------------

.. Insert new release notes below this line

* If ``exc_info`` is passed in, re-raise the exception (previously it would be
  ignored and crash in a different way). This isn't the nicest experience,
  however the behaviour is copied from ``wsgiref``\'s simple server, and most
  WSGI applications implement their own exception conversion to a "500 Internal
  Server Error" page already.

1.2.0 (2018-05-14)
------------------

* Work with base64 encoded ``body`` values in requests from API Gateway.

1.1.2 (2018-05-11)
------------------

* Fix crash using binary support for responses missing a ``Content-Type``
  header.

1.1.1 (2018-05-11)
------------------

* Remove debug ``print()``

1.1.0 (2018-05-10)
------------------

* Add ``binary_support`` flag to enable sending binary responses, if enabled on
  API Gateway.

1.0.0 (2018-03-08)
------------------

* First release on PyPI, working basic integration for WSGI apps on API
  Gateway.
