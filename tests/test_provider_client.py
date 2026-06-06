# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, patch

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


if __name__ == "__main__":
    unittest.main()
