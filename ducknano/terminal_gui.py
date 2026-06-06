# -*- coding: utf-8 -*-
import json
import os
import shutil
import sys
from typing import List, Tuple

import requests
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich import box

from ducknano.config import (
    PROVIDER_CONFIG,
    PROVIDER_PRESETS,
    azure_foundry_base_url,
    console,
    save_provider_config,
)


class TerminalGUI:
    """
    ANSI-first terminal GUI for DuckNano.

    The goal is to make the terminal feel like a small control surface:
    compact header, status cards, command chips, and guided setup forms.
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[38;5;51m"
    CYAN_DARK = "\033[38;5;37m"
    GREEN = "\033[38;5;48m"
    MAGENTA = "\033[38;5;201m"
    YELLOW = "\033[38;5;220m"
    RED = "\033[38;5;203m"
    WHITE = "\033[38;5;255m"
    MUTED = "\033[38;5;245m"
    PANEL = "\033[38;5;238m"
    BG = "\033[48;5;234m"
    BG_ALT = "\033[48;5;236m"

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def width(self) -> int:
        return max(72, min(120, shutil.get_terminal_size((100, 30)).columns))

    def ansi(self, text: str):
        console.file.write(text + "\n")
        console.file.flush()

    def strip_ansi_len(self, text: str) -> int:
        length = 0
        in_escape = False
        for char in text:
            if char == "\033":
                in_escape = True
            elif in_escape and char == "m":
                in_escape = False
            elif not in_escape:
                length += 1
        return length

    def fit(self, text: str, width: int) -> str:
        if len(text) <= width:
            return text.ljust(width)
        if width <= 1:
            return " " * width
        return text[: max(0, width - 3)] + "..."

    def line(self, char: str = "-") -> str:
        return f"{self.PANEL}{char * self.width()}{self.RESET}"

    def provider_name(self) -> str:
        key = PROVIDER_CONFIG.get("provider", "custom")
        preset = PROVIDER_PRESETS.get(key)
        return preset.get("name", key) if preset else key

    def masked_api_key(self) -> str:
        api_key = PROVIDER_CONFIG.get("api_key") or ""
        if not api_key:
            return "not set"
        if len(api_key) <= 8:
            return "***"
        return f"{api_key[:4]}...{api_key[-4:]}"

    def render_intro(self, hist_enabled: bool = False, rag_status: str = ""):
        self.clear()
        self.render_home(hist_enabled=hist_enabled, rag_status=rag_status)

    def render_home(self, hist_enabled: bool = False, rag_status: str = ""):
        self.render_header()
        self.render_dashboard(hist_enabled=hist_enabled, rag_status=rag_status)
        console.print(self.command_bar())
        console.print()

    def render_header(self):
        status = "[bold #00ff99]ready[/bold #00ff99]" if PROVIDER_CONFIG.get("api_key") else "[bold #ffcc00]api key missing[/bold #ffcc00]"
        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            "[bold #00ffcc]DuckNano[/bold #00ffcc] [dim]OpenAI-compatible terminal GUI[/dim]",
            status,
        )
        console.print(Panel(grid, border_style="#30363d", box=box.ROUNDED, padding=(0, 2)))

    def card(self, title: str, rows: List[Tuple[str, str]], width: int) -> List[str]:
        inner = width - 2
        title_text = f" {title} "
        top = f"{self.PANEL}+{title_text}{'-' * max(0, inner - len(title_text))}+{self.RESET}"
        bottom = f"{self.PANEL}+{'-' * inner}+{self.RESET}"
        lines = [top]
        for label, value in rows:
            label_plain = self.fit(label, 13)
            value_plain = self.fit(value, inner - 17)
            content = (
                f" {self.MUTED}{label_plain}{self.RESET} "
                f"{self.WHITE}{value_plain}{self.RESET}"
            )
            visual_pad = inner - self.strip_ansi_len(content)
            lines.append(f"{self.PANEL}|{self.RESET}{content}{' ' * max(0, visual_pad)}{self.PANEL}|{self.RESET}")
        lines.append(bottom)
        return lines

    def render_dashboard(self, hist_enabled: bool = False, rag_status: str = ""):
        layout = Table.grid(expand=True, padding=(0, 1))
        layout.add_column(ratio=1)
        layout.add_column(ratio=1)

        connection = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        connection.add_column("key", style="#8b949e", width=13)
        connection.add_column("value", style="white", overflow="fold")
        connection.add_row("provider", self.provider_name())
        connection.add_row("model", PROVIDER_CONFIG.get("model") or "auto")
        connection.add_row("api key", self.masked_api_key())
        connection.add_row("temperature", str(PROVIDER_CONFIG.get("temperature", "off")))

        session = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        session.add_column("key", style="#8b949e", width=13)
        session.add_column("value", style="white", overflow="fold")
        session.add_row("base url", PROVIDER_CONFIG.get("base_url", ""))
        session.add_row("history", "on" if hist_enabled else "off")
        session.add_row("rag", rag_status.replace("RAG: ", "") if rag_status else "ready")
        session.add_row("setup", "/setup")
        session.add_row("help", "/help")

        layout.add_row(
            Panel(connection, title="Connection", border_style="#30363d", box=box.ROUNDED),
            Panel(session, title="Session", border_style="#30363d", box=box.ROUNDED),
        )
        console.print(layout)

    def render_status(self, label: str, message: str, kind: str = "info"):
        color = {
            "info": self.CYAN,
            "ok": self.GREEN,
            "warn": self.YELLOW,
            "error": self.RED,
        }.get(kind, self.CYAN)
        label_text = self.fit(label.upper(), 10)
        msg = self.fit(message, self.width() - 15)
        self.ansi(f"{self.BG_ALT}{color} {label_text}{self.RESET} {self.WHITE}{msg}{self.RESET}")

    def render_help(self, help_text: str):
        self.ansi("")
        self.ansi(self.line())
        self.ansi(f"  {self.BOLD}{self.CYAN}Commands{self.RESET}  {self.MUTED}slash commands and local controls{self.RESET}")
        self.ansi(self.line())
        for raw in help_text.strip().splitlines():
            raw = raw.strip()
            if not raw:
                continue
            parts = raw.split(maxsplit=1)
            command = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            self.ansi(f"  {self.CYAN}{self.fit(command, 32)}{self.RESET}{self.MUTED}{rest}{self.RESET}")
        self.ansi(self.line())

    def render_json(self, title: str, data):
        body = json.dumps(data, indent=2, ensure_ascii=False)
        self.ansi("")
        self.ansi(self.line())
        self.ansi(f"  {self.BOLD}{self.CYAN}{title}{self.RESET}")
        self.ansi(self.line())
        limit = 12000
        if len(body) > limit:
            body = body[:limit] + "\n... truncated ..."
        console.print(body, markup=False, highlight=False)
        self.ansi(self.line())

    def command_bar(self):
        chips = [
            ("/setup", "configure"),
            ("/providers", "presets"),
            ("/models", "select model"),
            ("/temperature", "sampling"),
            ("clear", "reset"),
            ("exit", "quit"),
        ]
        grid = Table.grid(padding=(0, 2))
        for _ in range(3):
            grid.add_column()
        cells = [
            f"[reverse #30363d][#00ffcc] {cmd} [/][/] [dim]{desc}[/dim]"
            for cmd, desc in chips
        ]
        grid.add_row(*cells[:3])
        grid.add_row(*cells[3:])
        return Panel(grid, border_style="#30363d", box=box.ROUNDED, padding=(0, 1))

    def prompt_markup(self) -> str:
        provider = escape(PROVIDER_CONFIG.get("provider", "custom"))
        model = escape(PROVIDER_CONFIG.get("model") or "auto")
        key_color = "#00ff99" if PROVIDER_CONFIG.get("api_key") else "#ffcc00"
        return (
            f"[dim]{provider}[/dim] "
            f"[bold #00ffcc]{model}[/bold #00ffcc] "
            f"[{key_color}]>[/] "
        )

    def read_user_input(self) -> str:
        return console.input(self.prompt_markup())

    def render_saved_provider(self):
        self.ansi("")
        self.ansi(self.line())
        self.ansi(f"  {self.GREEN}{self.BOLD}Provider saved{self.RESET}")
        self.render_dashboard(hist_enabled=False)
        self.ansi(self.line())

    def render_provider_menu(self):
        self.ansi(f"  {self.MUTED}{self.fit('#', 4)} {self.fit('preset', 16)} {self.fit('provider', 34)} default model{self.RESET}")
        self.ansi(f"  {self.PANEL}{'-' * min(self.width() - 2, 86)}{self.RESET}")
        for index, (key, preset) in enumerate(PROVIDER_PRESETS.items(), start=1):
            self.ansi(
                f"  {self.CYAN}{self.fit(str(index), 4)}{self.RESET} "
                f"{self.WHITE}{self.fit(key, 16)}{self.RESET} "
                f"{self.MUTED}{self.fit(preset.get('name', ''), 34)}{self.RESET} "
                f"{self.WHITE}{self.fit(preset.get('model') or 'auto', 24)}{self.RESET}"
            )

    def fetch_provider_models(self, base_url: str, api_key: str) -> List[str]:
        url = f"{base_url.rstrip('/')}/models"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json().get("data", [])
        model_ids = []
        for item in data:
            if isinstance(item, dict) and item.get("id"):
                model_ids.append(str(item["id"]))
        return sorted(set(model_ids), key=str.lower)

    def read_key(self) -> str:
        if os.name == "nt":
            import msvcrt
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                code = msvcrt.getwch()
                return {
                    "H": "up",
                    "P": "down",
                    "K": "left",
                    "M": "right",
                    "I": "page_up",
                    "Q": "page_down",
                    "G": "home",
                    "O": "end",
                }.get(code, "")
            if key == "\r":
                return "enter"
            if key == "\x1b":
                return "esc"
            return key

        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
            if key == "\x1b":
                seq = sys.stdin.read(2)
                if seq == "[A":
                    return "up"
                if seq == "[B":
                    return "down"
                if seq == "[H":
                    return "home"
                if seq == "[F":
                    return "end"
                if seq.startswith("["):
                    extra = sys.stdin.read(1)
                    if seq + extra == "[5~":
                        return "page_up"
                    if seq + extra == "[6~":
                        return "page_down"
                return "esc"
            if key in ("\r", "\n"):
                return "enter"
            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def select_model(self, models: List[str], default_model: str = "") -> str:
        if not models or not sys.stdin.isatty():
            return ""

        query = ""
        filtered = models
        selected = 0
        if default_model in filtered:
            selected = filtered.index(default_model)
        page_size = max(8, min(14, shutil.get_terminal_size((100, 30)).lines - 10))

        while True:
            if not filtered:
                selected = 0
            else:
                selected = max(0, min(selected, len(filtered) - 1))
            start = max(0, min(selected - page_size // 2, len(filtered) - page_size))
            end = min(len(filtered), start + page_size)
            self.clear()
            self.ansi(self.line())
            self.ansi(f"  {self.BOLD}{self.CYAN}Select model{self.RESET}  {self.MUTED}GET /v1/models returned {len(models)} models{self.RESET}")
            self.ansi(self.line())
            self.ansi(f"  {self.MUTED}Type to filter. Up/Down selects. Enter confirms. Backspace edits. Esc manual input.{self.RESET}")
            self.ansi(f"  {self.CYAN}filter{self.RESET} {self.WHITE}{query or '(all models)'}{self.RESET}\n")

            if not filtered:
                self.ansi(f"   {self.YELLOW}No models match this filter.{self.RESET}")

            for index in range(start, end):
                model = self.fit(filtered[index], self.width() - 8)
                if filtered and index == selected:
                    self.ansi(f"{self.BG_ALT}{self.CYAN}{self.BOLD} > {model}{self.RESET}")
                else:
                    self.ansi(f"   {self.WHITE}{model}{self.RESET}")

            self.ansi("")
            count_text = f"{selected + 1}/{len(filtered)}" if filtered else f"0/{len(models)}"
            self.ansi(f"  {self.MUTED}{count_text}{self.RESET}")
            key = self.read_key()
            if key == "up":
                selected = max(0, selected - 1)
            elif key == "down":
                selected = min(len(filtered) - 1, selected + 1) if filtered else 0
            elif key == "page_up":
                selected = max(0, selected - page_size)
            elif key == "page_down":
                selected = min(len(filtered) - 1, selected + page_size) if filtered else 0
            elif key == "home":
                selected = 0
            elif key == "end":
                selected = len(filtered) - 1 if filtered else 0
            elif key == "enter" and filtered:
                self.clear()
                return filtered[selected]
            elif key == "esc":
                self.clear()
                return ""
            elif key in ("\b", "\x7f", "backspace"):
                query = query[:-1]
                filtered = [m for m in models if query.lower() in m.lower()]
                selected = 0
            elif len(key) == 1 and key.isprintable():
                query += key
                filtered = [m for m in models if query.lower() in m.lower()]
                selected = 0

    def run_provider_setup(self, harness=None):
        self.ansi("")
        self.ansi(self.line())
        self.ansi(f"  {self.BOLD}{self.CYAN}Provider setup{self.RESET}  {self.MUTED}choose a preset and fill account details{self.RESET}")
        self.ansi(self.line())
        self.render_provider_menu()

        presets = list(PROVIDER_PRESETS.items())
        choice = Prompt.ask("Provider number or name", default=PROVIDER_CONFIG.get("provider", "local"))
        preset_key = choice.strip().lower()
        if preset_key.isdigit():
            idx = int(preset_key) - 1
            if idx < 0 or idx >= len(presets):
                self.render_warning("Invalid provider number.")
                return
            preset_key = presets[idx][0]

        if preset_key not in PROVIDER_PRESETS:
            self.render_warning(f"Unknown provider preset: {preset_key}")
            return

        preset = PROVIDER_PRESETS[preset_key]
        base_url = preset.get("base_url", "")
        if preset_key == "azure-foundry":
            resource_url = Prompt.ask(
                "Azure resource URL",
                default=PROVIDER_CONFIG.get("base_url", "").replace("/openai/v1", ""),
            )
            base_url = azure_foundry_base_url(resource_url)
        elif preset_key == "local":
            base_url = Prompt.ask("Base URL", default=base_url or "http://localhost:8080/v1")

        current_key = PROVIDER_CONFIG.get("api_key", "")
        key_prompt = "API key (leave empty to keep current)" if current_key else "API key"
        api_key = Prompt.ask(key_prompt, default="", password=True)
        if not api_key and current_key:
            api_key = current_key

        default_model = PROVIDER_CONFIG.get("model") or preset.get("model") or ""
        model = ""
        self.render_status("models", f"Fetching {base_url.rstrip('/')}/models...", "info")
        try:
            models = self.fetch_provider_models(base_url, api_key)
            model = self.select_model(models, default_model=default_model)
        except Exception as e:
            self.render_warning(f"Could not load models automatically: {e}")

        if not model:
            model = Prompt.ask("Model or deployment name", default=default_model or "auto")
        if model == "auto":
            model = ""

        temperature = Prompt.ask("Temperature number or off", default=str(PROVIDER_CONFIG.get("temperature", "0.1")))

        save_provider_config({
            "provider": preset_key,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "embedding_model": "",
            "temperature": temperature,
        })
        if harness:
            harness.reload_provider_settings()
        self.render_saved_provider()

    def render_warning(self, message: str):
        self.render_status("warning", message, "warn")

    def render_error(self, message: str):
        self.render_status("error", message, "error")


terminal_gui = TerminalGUI()
