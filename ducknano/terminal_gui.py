# -*- coding: utf-8 -*-
import os
import time

from rich.align import Align
from rich.columns import Columns
from rich.live import Live
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
    Rich-based terminal GUI for DuckNano.

    This class owns the visual shell: dashboard, prompt, setup forms,
    shortcut panels, status panels, and user-facing error rendering.
    """

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def render_intro(self, hist_enabled: bool = False):
        self.clear()
        self._render_banner()
        self.render_home(hist_enabled=hist_enabled)

    def render_home(self, hist_enabled: bool = False):
        console.print(Align.center(Panel(
            "[bold #00ffcc]DuckNano[/bold #00ffcc]\n[dim]OpenAI-compatible terminal GUI[/dim]",
            title="[bold #00ffcc]Terminal GUI[/bold #00ffcc]",
            border_style="#00ffcc",
            box=box.ROUNDED,
            expand=False,
        )))
        self.render_dashboard(hist_enabled=hist_enabled)
        console.print()

    def _render_banner(self):
        banner_lines = [
            "@@@@@@@=     -*##-  :                         =:  .###.     .%@@@@@@@@@",
            "@@@@@@+=     +### :                         -  =: :*##+     :*%@@@@@@@@",
            "@@@@@@=.=.   +###.+ +. .-                -  -+ :+.-+*#*     --#@@@@@@@@",
            "@@@@@@+:=+   +###===*: +- .=.::       : .+- -#+:+=*%###    +-=#@@@@@@@@",
            "@@@@@@*=-:.  =####*+*=:#- =*--=   :  -= -#+.-##=*#%%%%*   -+==*@@@@@@@@",
            "@@@@@@#+++-  =#####*#*-=-:===++- .=  +-.**--++*###%#%%#.  ==+*#@@@@@@@@",
            "@@@@@@@*+=-:+*-:.  -*#*#*******+ :*.+=#+#++*##+:   ..=##*:+++*@@@@@@@@@",
            "@@@@@@@@#+=-+*+        .....:+##-:*-=##+:.        ..=#%#*+-++@@@@@@@@@@",
            "@@@@@@@@@#+-=*##*:  ...        .:.+.=          =++ =%%%#+-++%@@@@@@@@@@",
            "@@@@@@@@@@#+=+*##*           ..--=--::.  -+*###%#:-#%%%#++*#@@@@@@@@@@@",
            "@@@@@@@@@@@*.=+*##*=::-:-=-:.-*#*#%#*##+-.      .+#%%%#*:-@@@@@@@@@@@@@",
            "@@@@@@@@@@@@=:+**#################%##%%####%%%%%%%%#%%#*==@@@@@@@@@@@@@",
            "@@@@@@@@@@@@+-=+**#########%##%%%#%%%%%%%%%%%%%%%%%%+#*-*+@@@@@@@@@@@@@",
            "@@@@@@@%#%@@++:=**#########%%%%%%*=#%%%%%%%%%%%%%%%%+*=-+.       =%@@@@",
            "@*           =#:++####%####%%#*###%%%###%%%%%%%%%%%#==-#:           #@@",
            "+            :**.++**=+###%%%**##%%%%#*#%%%%%%%#-+#*-:%*.           :@@",
            "             .+#*::++-:+##%%%#=+#%#%%*=%%%%%#*-+#*+-:##=             #@",
            "             .=*#*=.==-. =*#%%*:-***:-####*= .====::-:                 ",
            "                -++=.-==: .::--:::.--:==-+-.---=-                      ",
            "                    . :==-:.=+**##+##=#==::..                          ",
            "                        -:--.   .. ..                                  ",
        ]
        colors = [
            "#330033", "#4d004d", "#660066", "#800080", "#990099", "#b300b3",
            "#cc00cc", "#e600e6", "#ff00ff", "#d91aff", "#b333ff", "#8c4dff",
            "#6666ff", "#3d80ff", "#1499ff", "#00ffff", "#00ffcc", "#00ff99",
            "#00ff66", "#33ff33", "#66ff66",
        ]
        with Live(console=console, screen=False, refresh_per_second=20) as live:
            for step in range(24):
                text = Text()
                for y, line in enumerate(banner_lines):
                    for x, char in enumerate(line):
                        idx = int((x * 0.25 + y * 0.5 - step * 0.8) % len(colors))
                        text.append(char, style=colors[idx])
                    text.append("\n")
                grid = Table.grid(padding=0)
                grid.add_column()
                grid.add_row(text)
                live.update(Align.center(grid))
                time.sleep(0.03)

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

    def render_dashboard(self, hist_enabled: bool = False):
        provider_table = Table(show_header=False, box=None, padding=(0, 1))
        provider_table.add_row("[bold #00ffcc]Provider[/bold #00ffcc]", escape(self.provider_name()))
        provider_table.add_row("[bold #00ffcc]Model[/bold #00ffcc]", escape(PROVIDER_CONFIG.get("model") or "auto"))
        provider_table.add_row("[bold #00ffcc]API key[/bold #00ffcc]", escape(self.masked_api_key()))
        provider_table.add_row(
            "[bold #00ffcc]Temperature[/bold #00ffcc]",
            escape(str(PROVIDER_CONFIG.get("temperature", "off"))),
        )

        session_table = Table(show_header=False, box=None, padding=(0, 1))
        session_table.add_row("[bold #00ffcc]Base URL[/bold #00ffcc]", escape(PROVIDER_CONFIG.get("base_url", "")))
        session_table.add_row("[bold #00ffcc]History[/bold #00ffcc]", "on" if hist_enabled else "off")
        session_table.add_row("[bold #00ffcc]Setup[/bold #00ffcc]", "use [bold]/setup[/bold] to configure")
        session_table.add_row("[bold #00ffcc]Help[/bold #00ffcc]", "use [bold]/help[/bold] for commands")

        left = Panel(provider_table, title="Connection", border_style="#00ffcc", box=box.ROUNDED)
        right = Panel(session_table, title="Session", border_style="#ff55ff", box=box.ROUNDED)
        console.print(Columns([left, right], equal=True, expand=True))
        console.print(self.render_shortcuts())

    def render_shortcuts(self):
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold #00ffcc")
        table.add_column()
        table.add_column(style="bold #00ffcc")
        table.add_column()
        table.add_row("/setup", "guided provider setup", "/providers", "list presets")
        table.add_row("/models", "list remote models", "/temperature", "set sampling")
        table.add_row("clear", "reset context", "exit", "quit")
        return Panel(Align.center(table), title="Quick Commands", border_style="dim #00ffcc", box=box.ROUNDED)

    def prompt_markup(self) -> str:
        provider = escape(PROVIDER_CONFIG.get("provider", "custom"))
        model = escape(PROVIDER_CONFIG.get("model") or "auto")
        key_state = "#00ff99" if PROVIDER_CONFIG.get("api_key") else "#ffaa00"
        return (
            f"[dim]{provider}[/dim]"
            f"[dim]/[/dim][bold #00ffcc]{model}[/bold #00ffcc] "
            f"[{key_state}]>[/] "
        )

    def read_user_input(self) -> str:
        return console.input(self.prompt_markup())

    def render_saved_provider(self):
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold #00ffcc]Provider[/bold #00ffcc]", escape(self.provider_name()))
        table.add_row("[bold #00ffcc]Base URL[/bold #00ffcc]", escape(PROVIDER_CONFIG.get("base_url", "")))
        table.add_row("[bold #00ffcc]Model[/bold #00ffcc]", escape(PROVIDER_CONFIG.get("model") or "auto"))
        table.add_row("[bold #00ffcc]API key[/bold #00ffcc]", escape(self.masked_api_key()))
        table.add_row(
            "[bold #00ffcc]Temperature[/bold #00ffcc]",
            escape(str(PROVIDER_CONFIG.get("temperature", "off"))),
        )
        console.print(Panel(table, title="Provider saved", border_style="#00ffcc", box=box.ROUNDED))

    def run_provider_setup(self, harness=None):
        console.print(Panel(
            "Choose a provider preset, then fill only the fields required for your account.",
            title="Provider Setup",
            border_style="#00ffcc",
            box=box.ROUNDED,
        ))

        presets = list(PROVIDER_PRESETS.items())
        table = Table()
        table.add_column("#", justify="right", style="bold #00ffcc")
        table.add_column("Preset", style="bold")
        table.add_column("Name")
        table.add_column("Default model")
        for index, (key, preset) in enumerate(presets, start=1):
            table.add_row(str(index), key, preset.get("name", ""), preset.get("model") or "auto")
        console.print(table)

        choice = Prompt.ask("Provider number or name", default=PROVIDER_CONFIG.get("provider", "local"))
        preset_key = choice.strip().lower()
        if preset_key.isdigit():
            idx = int(preset_key) - 1
            if idx < 0 or idx >= len(presets):
                console.print("[yellow]Invalid provider number.[/yellow]")
                return
            preset_key = presets[idx][0]

        if preset_key not in PROVIDER_PRESETS:
            console.print(f"[yellow]Unknown provider preset: {escape(preset_key)}[/yellow]")
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

    def render_error(self, message: str):
        console.print(Panel(Text(message, style="bold red"), title="Error", border_style="red", box=box.ROUNDED))


terminal_gui = TerminalGUI()
