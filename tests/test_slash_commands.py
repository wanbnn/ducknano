# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, patch

from ducknano import slash_commands


class SlashCommandTests(unittest.TestCase):
    @patch("ducknano.slash_commands.save_provider_config")
    @patch("ducknano.slash_commands.terminal_gui")
    @patch("ducknano.slash_commands.provider_client")
    def test_models_opens_selector_and_saves_model(self, client_mock, gui_mock, save_mock):
        client_mock.model_ids.return_value = ["b", "a"]
        gui_mock.select_model.return_value = "a"
        harness = Mock()

        handled = slash_commands.handle_slash_command("/models", harness)

        self.assertTrue(handled)
        gui_mock.select_model.assert_called_once()
        save_mock.assert_called_once_with({"model": "a"})
        harness.reload_provider_settings.assert_called_once()
        gui_mock.render_status.assert_called_once()

    @patch("ducknano.slash_commands._print_json")
    @patch("ducknano.slash_commands.provider_client")
    def test_models_json_prints_raw_json(self, client_mock, print_json_mock):
        payload = {"data": [{"id": "m"}]}
        client_mock.list_models.return_value = payload

        handled = slash_commands.handle_slash_command("/models json")

        self.assertTrue(handled)
        print_json_mock.assert_called_once_with("GET /v1/models", payload)


if __name__ == "__main__":
    unittest.main()
