# -*- coding: utf-8 -*-
import unittest

from ducknano.config import PROVIDER_CONFIG, _normalize_base_url, azure_foundry_base_url, provider_temperature


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.original_config = PROVIDER_CONFIG.copy()

    def tearDown(self):
        PROVIDER_CONFIG.clear()
        PROVIDER_CONFIG.update(self.original_config)

    def test_normalize_base_url_adds_v1(self):
        self.assertEqual(_normalize_base_url("https://example.com"), "https://example.com/v1")

    def test_normalize_base_url_strips_chat_completions(self):
        self.assertEqual(
            _normalize_base_url("https://example.com/v1/chat/completions"),
            "https://example.com/v1",
        )

    def test_azure_foundry_base_url(self):
        self.assertEqual(
            azure_foundry_base_url("https://demo.openai.azure.com"),
            "https://demo.openai.azure.com/openai/v1",
        )

    def test_provider_temperature_off(self):
        PROVIDER_CONFIG["temperature"] = "off"
        self.assertIsNone(provider_temperature())

    def test_provider_temperature_number(self):
        PROVIDER_CONFIG["temperature"] = "0.7"
        self.assertEqual(provider_temperature(), 0.7)


if __name__ == "__main__":
    unittest.main()
