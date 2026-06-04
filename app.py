# -*- coding: utf-8 -*-
import os
import time
import sys
import argparse
from rich.panel import Panel
from rich.markup import escape
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

from ducknano.config import console, WORKSPACE_DIR
from ducknano.harness import LlamaHarness

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
            
    # Painel com informações gerais do sistema
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_row("[bold #00ffcc]Workspace:[/bold #00ffcc]", f"[white]{os.getcwd()}[/white]")
    info_table.add_row("[bold #00ffcc]LLM API:[/bold #00ffcc]", f"[white]{os.environ.get('LLAMA_API_URL', 'http://localhost:8080/v1')}[/white]")
    if hist_enabled:
        hist_path = os.path.join(WORKSPACE_DIR, ".duck", "history", "session.json")
        info_table.add_row(
            "[bold #00ffcc]History:[/bold #00ffcc]",
            f"[bold #00ff99]ON[/bold #00ff99] [dim]({hist_path})[/dim]"
        )
    else:
        info_table.add_row(
            "[bold #00ffcc]History:[/bold #00ffcc]",
            "[dim #888888]OFF (API-managed)[/dim #888888]"
        )
    
    console.print(Align.center(Panel(
        info_table,
        title="[bold #00ffcc]⚙️ Mini Agent - Duck V3.2[/bold #00ffcc]",
        border_style="#00ffcc",
        box=box.ROUNDED,
        expand=False
    )))
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
            user_input = console.input("[bold #00ffcc]user[/bold #00ffcc] [bold #ff55ff]❯[/bold #ff55ff] ")
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
            
            harness.step(user_input)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Operacao cancelada pelo usuario.[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Ocorreu um erro inesperado: {escape(str(e))}[/bold red]")


if __name__ == "__main__":
    main()