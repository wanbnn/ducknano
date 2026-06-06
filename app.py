# -*- coding: utf-8 -*-
import os
import time
import argparse
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

from ducknano.config import console
from ducknano.harness import LlamaHarness
from ducknano.slash_commands import handle_slash_command
from ducknano.terminal_gui import terminal_gui

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_intro(hist_enabled: bool = False):
    clear_screen()
    
    banner_lines = [
        "@@@@@@@=     -*##-  :                         =:  .###.     .%@@@@@@@@@",
        "@@@@@@+=     +### :                         -  =: :*##+     :*%@@@@@@@@",
        "@@@@@@=.=.   +###.+ +. .-                -  -+ :+.-+*#*     --#@@@@@@@@",
        "@@@@@@+:=+   +###===*: +- .=.::       : .+- -#+:+=*%###    +-=#@@@@@@@@",
        "@@@@@@*=-:.  =####*+*=:#- =*--=   :  -= -#+.-##=*#%%%%*   -+==*@@@@@@@@",
        "@@@@@@#+++-  =#####*#*-=-:===++- .=  +-.**--++*###%#%%#.  ==+*#@@@@@@@@",
        "@@@@@@@*+=-:+*-:.  -*#*#*******+ :*.+=#+#+**##+:   ..=##*:+++*@@@@@@@@@",
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
        "                                                                       ",
        "                                                                       ",
        ".                                                                      "
    ]
    
    colors = [
        "#330033", "#4d004d", "#660066", "#800080", "#990099", "#b300b3",
        "#cc00cc", "#e600e6", "#ff00ff", "#d91aff", "#b333ff", "#8c4dff",
        "#6666ff", "#3d80ff", "#1499ff", "#00ffff", "#00ffcc", "#00ff99", 
        "#00ff66", "#33ff33", "#66ff66"
    ]
    
    # Efeito de onda procedural de plasma
    with Live(console=console, screen=False, refresh_per_second=20) as live:
        for step in range(35):
            text = Text()
            for y, line in enumerate(banner_lines):
                for x, char in enumerate(line):
                    # Onda diagonal de plasma baseada nas coordenadas x, y e no frame step
                    idx = int((x * 0.25 + y * 0.5 - step * 0.8) % len(colors))
                    text.append(char, style=colors[idx])
                text.append("\n")
            
            grid = Table.grid(padding=0)
            grid.add_column()
            grid.add_row(text)
            
            live.update(Align.center(grid))
            time.sleep(0.04)
            
    console.print(Align.center(Panel(
        "[bold #00ffcc]DuckNano[/bold #00ffcc]\n[dim]OpenAI-compatible terminal agent[/dim]",
        title="[bold #00ffcc]Mini Agent[/bold #00ffcc]",
        border_style="#00ffcc",
        box=box.ROUNDED,
        expand=False
    )))
    terminal_gui.render_dashboard(hist_enabled=hist_enabled)
    console.print()

def main():
    parser = argparse.ArgumentParser(
        description="DuckNano — Mini Agent",
        add_help=True
    )
    parser.add_argument(
        "--hist",
        choices=["on", "off"],
        default="off",
        metavar="on|off",
        help="Ativa o gerenciador de histórico persistente de chat (padrão: off)"
    )
    args = parser.parse_args()
    hist_enabled = args.hist == "on"

    show_intro(hist_enabled=hist_enabled)
    harness = LlamaHarness(hist_enabled=hist_enabled)
    
    while True:
        try:
            user_input = console.input(terminal_gui.prompt_markup())
            if not user_input.strip():
                continue
            if user_input.lower() in ("exit", "quit", "sair"):
                console.print("[yellow]Saindo...[/yellow]")
                break
            if user_input.lower() in ("clear", "clear_session", "clear_history", "limpar"):
                harness.init_history(clear_persisted=True)
                show_intro(hist_enabled=hist_enabled)
                console.print("[green]Contexto ativo reiniciado e tela limpa.[/green]\n")
                continue
            if handle_slash_command(user_input, harness):
                continue
            
            harness.step(user_input)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Operacao cancelada pelo usuario.[/yellow]")
        except Exception as e:
            terminal_gui.render_error(f"Ocorreu um erro inesperado: {e}")


if __name__ == "__main__":
    main()
