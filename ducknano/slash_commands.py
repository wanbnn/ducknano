# -*- coding: utf-8 -*-
import json
import os
import shlex

from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from ducknano.config import (
    PROVIDER_CONFIG,
    PROVIDER_PRESETS,
    azure_foundry_base_url,
    console,
    save_provider_config,
)
from ducknano.openai_compatible import (
    create_embedding,
    generate_image,
    get_model,
    list_files,
    list_models,
    transcribe_audio,
    upload_file,
)
from ducknano.ui import run_provider_setup


HELP_TEXT = """Comandos OpenAI-compatible:
/setup
/providers
/provider show
/provider use <preset> api_key=... model=...
/provider set base_url=http://localhost:8080/v1 api_key=... model=...
/provider reset
/models
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
    console.print(Panel(
        escape(json.dumps(data, indent=2, ensure_ascii=False)[:8000]),
        title=title,
        border_style="#00ffcc",
    ))


def _provider_table():
    table = Table(show_header=False)
    table.add_column("Campo", style="bold #00ffcc")
    table.add_column("Valor")
    table.add_row("provider", PROVIDER_CONFIG.get("provider", "custom"))
    table.add_row("base_url", PROVIDER_CONFIG.get("base_url", ""))
    table.add_row("api_key", "***" if PROVIDER_CONFIG.get("api_key") else "(vazio)")
    table.add_row("model", PROVIDER_CONFIG.get("model") or "(auto)")
    table.add_row("embedding_model", PROVIDER_CONFIG.get("embedding_model") or "(auto)")
    table.add_row("temperature", str(PROVIDER_CONFIG.get("temperature", "off")))
    console.print(Panel(table, title="Provider", border_style="#00ffcc"))


def _providers_table():
    table = Table()
    table.add_column("Preset", style="bold #00ffcc")
    table.add_column("Nome")
    table.add_column("Base URL")
    table.add_column("Modelo exemplo")
    for key, preset in PROVIDER_PRESETS.items():
        table.add_row(
            key,
            preset.get("name", ""),
            preset.get("base_url") or "(resource_url necessario)",
            preset.get("model") or "(auto)",
        )
    console.print(Panel(table, title="Providers Pre-configurados", border_style="#00ffcc"))


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
        console.print(f"[red]Comando invalido: {escape(str(e))}[/red]")
        return True

    if not parts:
        return True

    command = parts[0].lower()
    args = parts[1:]

    try:
        if command in {"/help", "/?"}:
            console.print(Panel(HELP_TEXT, title="Ajuda", border_style="#00ffcc"))
            return True

        if command == "/setup":
            run_provider_setup(harness)
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
                    console.print("[yellow]Use: /provider use <preset> api_key=... model=...[/yellow]")
                    _providers_table()
                    return True
                preset_key = args[1].strip("\"'").lower()
                if preset_key not in PROVIDER_PRESETS:
                    console.print(f"[yellow]Preset desconhecido: {escape(preset_key)}[/yellow]")
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
                    console.print(f"[dim]{escape(note)}[/dim]")
                return True
            if action == "set":
                values, _ = _parse_key_values(args[1:])
                allowed = {"base_url", "api_key", "model", "embedding_model", "temperature", "provider"}
                updates = {k: v for k, v in values.items() if k in allowed}
                updates.setdefault("provider", "custom")
                if not updates:
                    console.print("[yellow]Use: /provider set base_url=... api_key=... model=...[/yellow]")
                    return True
                save_provider_config(updates)
                if harness:
                    harness.reload_provider_settings()
                _provider_table()
                return True
            console.print("[yellow]Use /provider show, /provider set ou /provider reset.[/yellow]")
            return True

        if command == "/models":
            _print_json("GET /v1/models", list_models())
            return True

        if command == "/model":
            if not args:
                console.print("[yellow]Use: /model <id>[/yellow]")
                return True
            model_id = args[0].strip("\"'")
            save_provider_config({"model": model_id})
            if harness:
                harness.reload_provider_settings()
            _print_json(f"GET /v1/models/{model_id}", get_model(model_id))
            return True

        if command == "/temperature":
            if not args:
                console.print(f"[cyan]temperature = {PROVIDER_CONFIG.get('temperature', 'off')}[/cyan]")
                return True
            value = args[0].strip("\"'").lower()
            if value not in {"off", "none", "null"}:
                float(value)
            save_provider_config({"temperature": value})
            console.print(f"[green]Temperature configurada: {value}[/green]")
            return True

        if command == "/files":
            _print_json("GET /v1/files", list_files())
            return True

        if command == "/upload":
            if not args:
                console.print("[yellow]Use: /upload <path> [purpose][/yellow]")
                return True
            path = os.path.abspath(args[0].strip("\"'"))
            purpose = args[1].strip("\"'") if len(args) > 1 else "assistants"
            _print_json("POST /v1/files", upload_file(path, purpose))
            return True

        if command == "/embeddings":
            if not args:
                console.print("[yellow]Use: /embeddings <texto>[/yellow]")
                return True
            _print_json("POST /v1/embeddings", create_embedding(" ".join(a.strip("\"'") for a in args)))
            return True

        if command == "/transcribe":
            if not args:
                console.print("[yellow]Use: /transcribe <path> [model][/yellow]")
                return True
            path = os.path.abspath(args[0].strip("\"'"))
            model = args[1].strip("\"'") if len(args) > 1 else "whisper-1"
            _print_json("POST /v1/audio/transcriptions", transcribe_audio(path, model))
            return True

        if command == "/image":
            if not args:
                console.print("[yellow]Use: /image <prompt> [model=...] [size=1024x1024][/yellow]")
                return True
            values, positionals = _parse_key_values(args)
            prompt = " ".join(positionals)
            _print_json(
                "POST /v1/images/generations",
                generate_image(prompt, model=values.get("model"), size=values.get("size", "1024x1024")),
            )
            return True

        console.print("[yellow]Comando slash desconhecido. Use /help.[/yellow]")
        return True
    except Exception as e:
        console.print(f"[bold red]Erro no comando {escape(command)}: {escape(str(e))}[/bold red]")
        return True
