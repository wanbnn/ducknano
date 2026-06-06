# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, patch

import requests

from ducknano.provider_client import ProviderClient


class ProviderClientTests(unittest.TestCase):
    def test_endpoint_with_override_base_url(self):
        client = ProviderClient()
        self.assertEqual(
            client.endpoint("/models", base_url="https://example.com/v1"),
            "https://example.com/v1/models",
        )

    def test_json_headers_with_api_key(self):
        client = ProviderClient()
        self.assertEqual(
            client.json_headers(api_key="secret"),
            {"Content-Type": "application/json", "Authorization": "Bearer secret"},
        )

    @patch("ducknano.provider_client.requests.request")
    def test_model_ids_extracts_and_sorts_ids(self, request_mock):
        response = Mock()
        response.json.return_value = {"data": [{"id": "z-model"}, {"id": "a-model"}, {"object": "model"}]}
        response.raise_for_status.return_value = None
        request_mock.return_value = response

        client = ProviderClient()
        self.assertEqual(client.model_ids(base_url="https://example.com/v1", api_key="k"), ["a-model", "z-model"])
        request_mock.assert_called_once()

    @patch("ducknano.provider_client.time.sleep")
    @patch("ducknano.provider_client.requests.post")
    def test_chat_completions_retries_connection_error(self, post_mock, sleep_mock):
        response = Mock()
        response.status_code = 200
        post_mock.side_effect = [requests.ConnectionError("drop"), response]

        client = ProviderClient()
        result = client.chat_completions({"model": "m", "messages": []}, retries=1)

        self.assertIs(result, response)
        self.assertEqual(post_mock.call_count, 2)
        sleep_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
