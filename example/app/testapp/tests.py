from django.test import SimpleTestCase


class IndexTests(SimpleTestCase):
    def test_foo(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
