# -*- coding: utf-8 -*-
import os
import shlex

from ducknano.config import (
    PROVIDER_CONFIG,
    PROVIDER_PRESETS,
    azure_foundry_base_url,
    save_provider_config,
)
from ducknano.provider_client import provider_client
from ducknano.terminal_gui import terminal_gui


HELP_TEXT = """Comandos OpenAI-compatible:
/setup
/providers
/provider show
/provider use <preset> api_key=... model=...
/provider set base_url=http://localhost:8080/v1 api_key=... model=...
/provider reset
/models
/models json
/model <id>
/temperature <numero|off>
/files
/upload <path> [purpose]
/embeddings <texto>
/transcribe <path> [model]
/image <prompt> [model=...] [size=1024x1024]
"""


def _parse_key_values(args):
    values = {}
    positionals = []
    for arg in args:
        arg = arg.strip("\"'")
        if "=" in arg:
            key, value = arg.split("=", 1)
            values[key.strip()] = value.strip("\"'")
        else:
            positionals.append(arg)
    return values, positionals


def _print_json(title: str, data):
    terminal_gui.render_json(title, data)


def _provider_table():
    terminal_gui.render_dashboard(hist_enabled=False)


def _providers_table():
    terminal_gui.render_provider_menu()


def _provider_updates_from_preset(preset_key: str, values: dict) -> dict:
    preset = PROVIDER_PRESETS[preset_key]
    updates = {
        "provider": preset_key,
        "base_url": preset.get("base_url", ""),
        "api_key": preset.get("api_key", ""),
        "model": preset.get("model", ""),
        "embedding_model": "",
        "temperature": PROVIDER_CONFIG.get("temperature", "0.1"),
    }

    if preset_key == "azure-foundry":
        if values.get("resource_url"):
            updates["base_url"] = azure_foundry_base_url(values["resource_url"])
        elif values.get("base_url"):
            updates["base_url"] = values["base_url"]
        else:
            raise ValueError(
                "Azure/Foundry precisa de resource_url=https://<resource>.openai.azure.com "
                "ou base_url=https://<resource>.openai.azure.com/openai/v1"
            )

    allowed_overrides = {"base_url", "api_key", "model", "embedding_model", "temperature"}
    updates.update({k: v for k, v in values.items() if k in allowed_overrides})
    if preset_key == "azure-foundry" and values.get("resource_url") and not values.get("base_url"):
        updates["base_url"] = azure_foundry_base_url(values["resource_url"])
    return updates


def handle_slash_command(command_line: str, harness=None) -> bool:
    if not command_line.startswith("/"):
        return False

    try:
        parts = shlex.split(command_line, posix=False)
    except ValueError as e:
        terminal_gui.render_error(f"Comando invalido: {e}")
        return True

    if not parts:
        return True

    command = parts[0].lower()
    args = parts[1:]

    try:
        if command in {"/help", "/?"}:
            terminal_gui.render_help(HELP_TEXT)
            return True

        if command == "/setup":
            terminal_gui.run_provider_setup(
                harness,
                load_models=lambda base_url, api_key: provider_client.model_ids(base_url=base_url, api_key=api_key),
            )
            return True

        if command == "/providers":
            _providers_table()
            return True

        if command == "/provider":
            action = args[0].lower() if args else "show"
            if action == "show":
                _provider_table()
                return True
            if action == "reset":
                save_provider_config({
                    "base_url": "http://localhost:8080/v1",
                    "api_key": "",
                    "model": "",
                    "embedding_model": "",
                    "temperature": "0.1",
                    "provider": "local",
                })
                if harness:
                    harness.reload_provider_settings()
                _provider_table()
                return True
            if action == "use":
                if len(args) < 2:
                    terminal_gui.render_warning("Use: /provider use <preset> api_key=... model=...")
                    _providers_table()
                    return True
                preset_key = args[1].strip("\"'").lower()
                if preset_key not in PROVIDER_PRESETS:
                    terminal_gui.render_warning(f"Preset desconhecido: {preset_key}")
                    _providers_table()
                    return True
                values, _ = _parse_key_values(args[2:])
                updates = _provider_updates_from_preset(preset_key, values)
                save_provider_config(updates)
                if harness:
                    harness.reload_provider_settings()
                _provider_table()
                note = PROVIDER_PRESETS[preset_key].get("notes")
                if note:
                    terminal_gui.render_status("note", note, "info")
                return True
            if action == "set":
                values, _ = _parse_key_values(args[1:])
                allowed = {"base_url", "api_key", "model", "embedding_model", "temperature", "provider"}
                updates = {k: v for k, v in values.items() if k in allowed}
                updates.setdefault("provider", "custom")
                if not updates:
                    terminal_gui.render_warning("Use: /provider set base_url=... api_key=... model=...")
                    return True
                save_provider_config(updates)
                if harness:
                    harness.reload_provider_settings()
                _provider_table()
                return True
            terminal_gui.render_warning("Use /provider show, /provider set ou /provider reset.")
            return True

        if command == "/models":
            if args and args[0].strip("\"'").lower() == "json":
                _print_json("GET /v1/models", provider_client.list_models())
                return True
            models = provider_client.model_ids()
            model_id = terminal_gui.select_model(
                sorted(set(models), key=str.lower),
                default_model=PROVIDER_CONFIG.get("model", ""),
            )
            if not model_id:
                terminal_gui.render_warning("Nenhum modelo selecionado.")
                return True
            save_provider_config({"model": model_id})
            if harness:
                harness.reload_provider_settings()
            terminal_gui.render_status("model", f"selected: {model_id}", "ok")
            return True

        if command == "/model":
            if not args:
                terminal_gui.render_warning("Use: /model <id>")
                return True
            model_id = args[0].strip("\"'")
            save_provider_config({"model": model_id})
            if harness:
                harness.reload_provider_settings()
            _print_json(f"GET /v1/models/{model_id}", provider_client.get_model(model_id))
            return True

        if command == "/temperature":
            if not args:
                terminal_gui.render_status("temperature", f"{PROVIDER_CONFIG.get('temperature', 'off')}", "info")
                return True
            value = args[0].strip("\"'").lower()
            if value not in {"off", "none", "null"}:
                float(value)
            save_provider_config({"temperature": value})
            terminal_gui.render_status("temperature", f"configured: {value}", "ok")
            return True

        if command == "/files":
            _print_json("GET /v1/files", provider_client.list_files())
            return True

        if command == "/upload":
            if not args:
                terminal_gui.render_warning("Use: /upload <path> [purpose]")
                return True
            path = os.path.abspath(args[0].strip("\"'"))
            purpose = args[1].strip("\"'") if len(args) > 1 else "assistants"
            _print_json("POST /v1/files", provider_client.upload_file(path, purpose))
            return True

        if command == "/embeddings":
            if not args:
                terminal_gui.render_warning("Use: /embeddings <texto>")
                return True
            _print_json("POST /v1/embeddings", provider_client.embeddings(" ".join(a.strip("\"'") for a in args)))
            return True

        if command == "/transcribe":
            if not args:
                terminal_gui.render_warning("Use: /transcribe <path> [model]")
                return True
            path = os.path.abspath(args[0].strip("\"'"))
            model = args[1].strip("\"'") if len(args) > 1 else "whisper-1"
            _print_json("POST /v1/audio/transcriptions", provider_client.transcribe_audio(path, model))
            return True

        if command == "/image":
            if not args:
                terminal_gui.render_warning("Use: /image <prompt> [model=...] [size=1024x1024]")
                return True
            values, positionals = _parse_key_values(args)
            prompt = " ".join(positionals)
            _print_json(
                "POST /v1/images/generations",
                provider_client.generate_image(prompt, model=values.get("model"), size=values.get("size", "1024x1024")),
            )
            return True

        terminal_gui.render_warning("Comando slash desconhecido. Use /help.")
        return True
    except Exception as e:
        terminal_gui.render_error(f"Erro no comando {command}: {e}")
        return True
