# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from apig_wsgi import make_lambda_handler


def test_basic():
    def foo():
        return 1

    handler = make_lambda_handler(foo)

    assert handler() == 1
