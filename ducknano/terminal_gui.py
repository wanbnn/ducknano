# -*- coding: utf-8 -*-
import os
import shutil
from typing import List, Tuple

from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

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

    def render_intro(self, hist_enabled: bool = False):
        self.clear()
        self.render_home(hist_enabled=hist_enabled)

    def render_home(self, hist_enabled: bool = False):
        self.ansi(self.line())
        self.ansi(self.header())
        self.ansi(self.line())
        self.render_dashboard(hist_enabled=hist_enabled)
        self.ansi(self.command_bar())
        self.ansi("")

    def header(self) -> str:
        width = self.width()
        title = f"{self.BOLD}{self.CYAN}DuckNano{self.RESET}"
        subtitle = f"{self.MUTED}OpenAI-compatible terminal GUI{self.RESET}"
        right = f"{self.GREEN}ready{self.RESET}" if PROVIDER_CONFIG.get("api_key") else f"{self.YELLOW}api key missing{self.RESET}"
        raw = f"  {title}  {subtitle}"
        pad = max(1, width - self.strip_ansi_len(raw) - self.strip_ansi_len(right) - 2)
        return f"{raw}{' ' * pad}{right}  "

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

    def render_dashboard(self, hist_enabled: bool = False):
        total = self.width()
        gap = 2
        left_w = (total - gap) // 2
        right_w = total - gap - left_w
        provider_rows = [
            ("provider", self.provider_name()),
            ("model", PROVIDER_CONFIG.get("model") or "auto"),
            ("api key", self.masked_api_key()),
            ("temperature", str(PROVIDER_CONFIG.get("temperature", "off"))),
        ]
        session_rows = [
            ("base url", PROVIDER_CONFIG.get("base_url", "")),
            ("history", "on" if hist_enabled else "off"),
            ("setup", "/setup"),
            ("help", "/help"),
        ]
        left = self.card("Connection", provider_rows, left_w)
        right = self.card("Session", session_rows, right_w)
        for a, b in zip(left, right):
            self.ansi(f"{a}{' ' * gap}{b}")

    def command_bar(self) -> str:
        chips = [
            ("/setup", "configure"),
            ("/providers", "presets"),
            ("/models", "models"),
            ("/temperature", "sampling"),
            ("clear", "reset"),
            ("exit", "quit"),
        ]
        lines = []
        current = ""
        current_len = 0
        for cmd, desc in chips:
            plain = f" {cmd}  {desc}"
            styled = f"{self.BG_ALT}{self.CYAN} {cmd} {self.RESET}{self.MUTED} {desc}{self.RESET}"
            sep = "  " if current else ""
            if current and current_len + len(sep) + len(plain) > self.width():
                lines.append(current)
                current = styled
                current_len = len(plain)
            else:
                current += sep + styled
                current_len += len(sep) + len(plain)
        if current:
            lines.append(current)
        return "\n" + "\n".join(lines)

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
        table = Table(
            show_header=True,
            header_style="bold #00ffcc",
            border_style="#30363d",
            box=None,
            padding=(0, 1),
        )
        table.add_column("#", justify="right", style="#00ffcc")
        table.add_column("Preset", style="bold white")
        table.add_column("Provider")
        table.add_column("Default model")
        for index, (key, preset) in enumerate(PROVIDER_PRESETS.items(), start=1):
            table.add_row(str(index), key, preset.get("name", ""), preset.get("model") or "auto")
        console.print(table)

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
        self.ansi(f"{self.YELLOW}{self.BOLD}warning{self.RESET} {message}")

    def render_error(self, message: str):
        console.print(Panel(Text(message, style="bold red"), title="Error", border_style="red"))


terminal_gui = TerminalGUI()
