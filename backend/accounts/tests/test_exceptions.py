from django.http import Http404
from django.test import SimpleTestCase

from accounts.exceptions import api_exception_handler


class ExceptionHandlerTests(SimpleTestCase):
    def test_django_http404_uses_error_format(self):
        response = api_exception_handler(Http404(), {})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(list(response.data), ["errors"])
        self.assertIn("detail", response.data["errors"])
