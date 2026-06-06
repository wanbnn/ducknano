# -*- coding: utf-8 -*-
import argparse

from ducknano.config import console
from ducknano.harness import LlamaHarness
from ducknano.slash_commands import handle_slash_command
from ducknano.terminal_gui import terminal_gui


def main():
    parser = argparse.ArgumentParser(
        description="DuckNano - Mini Agent",
        add_help=True,
    )
    parser.add_argument(
        "--hist",
        choices=["on", "off"],
        default="off",
        metavar="on|off",
        help="Ativa o gerenciador de historico persistente de chat (padrao: off)",
    )
    args = parser.parse_args()
    hist_enabled = args.hist == "on"

    terminal_gui.clear()
    harness = LlamaHarness(hist_enabled=hist_enabled)
    terminal_gui.render_home(
        hist_enabled=hist_enabled,
        rag_status=getattr(harness.workspace_index, "status_message", ""),
    )

    while True:
        try:
            user_input = terminal_gui.read_user_input()
            if not user_input.strip():
                continue

            if user_input.lower() in ("exit", "quit", "sair"):
                console.print("[yellow]Saindo...[/yellow]")
                break

            if user_input.lower() in ("clear", "clear_session", "clear_history", "limpar"):
                harness.init_history(clear_persisted=True)
                terminal_gui.render_intro(
                    hist_enabled=hist_enabled,
                    rag_status=getattr(harness.workspace_index, "status_message", ""),
                )
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
