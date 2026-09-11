"""Tests for mycurl."""

import unittest

from mycurl.client import MyCurlClient, RequestConfig


class TestMyCurl(unittest.TestCase):
    def test_get_request(self):
        config = RequestConfig(url="https://httpbin.org/get", method="GET")
        client = MyCurlClient(config)
        response = client.execute()
        self.assertEqual(response.status_code, 200)

    def test_post_request(self):
        config = RequestConfig(
            url="https://httpbin.org/post",
            method="POST",
            data="name=test&value=123",
        )
        client = MyCurlClient(config)
        response = client.execute()
        self.assertEqual(response.status_code, 200)

    def test_custom_headers(self):
        import json

        config = RequestConfig(
            url="https://httpbin.org/headers",
            headers={"X-Custom": "test-value"},
        )
        client = MyCurlClient(config)
        response = client.execute()
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.body)
        self.assertEqual(body["headers"].get("X-Custom"), "test-value")

    def test_json_request(self):
        config = RequestConfig(
            url="https://httpbin.org/post",
            method="POST",
            json_data={"key": "value"},
        )
        client = MyCurlClient(config)
        response = client.execute()
        self.assertEqual(response.status_code, 200)

    def test_status_code(self):
        config = RequestConfig(url="https://httpbin.org/status/404")
        client = MyCurlClient(config)
        response = client.execute()
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()