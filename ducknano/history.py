# -*- coding: utf-8 -*-
"""
history.py — Gerenciador de histórico persistente de chat.

Salva apenas mensagens de role 'user' e 'assistant' (nunca 'system' nem
few-shot anchors) em .duck/history/session.json.

Estratégia de restauração: janela deslizante das últimas MAX_RESTORE_MSGS
mensagens para evitar que o arquivo cresça indefinidamente no contexto.
"""
import json
import os
from typing import List, Dict

# Quantas mensagens (user+assistant) restaurar no máximo ao retomar sessão
MAX_RESTORE_MSGS = 4


class HistoryManager:
    def __init__(self, history_path: str):
        self.path = history_path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def load(self) -> List[Dict[str, str]]:
        """
        Carrega o histórico salvo em disco.
        Retorna apenas mensagens user/assistant (nunca system).
        Aplica janela deslizante: retorna no máximo MAX_RESTORE_MSGS entradas.
        """
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filtro de segurança: só user/assistant
            messages = [
                m for m in data
                if isinstance(m, dict) and m.get("role") in ("user", "assistant")
            ]
            # Janela deslizante: pega as últimas MAX_RESTORE_MSGS
            return messages[-MAX_RESTORE_MSGS:]
        except Exception:
            return []

    def save(self, history: List[Dict[str, str]]) -> None:
        """
        Salva o histórico em disco.
        Filtra automaticamente mensagens de system, recalled_mem e few-shot.
        """
        saveable = [
            m for m in history
            if isinstance(m, dict)
            and m.get("role") in ("user", "assistant")
            and not m.get("content", "").startswith("[RECALLED_MEM")
        ]
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(saveable, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # Nunca quebrar a sessão por falha de I/O

    def clear(self) -> None:
        """Apaga o arquivo de histórico em disco."""
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        except Exception:
            pass

    def exists(self) -> bool:
        """Retorna True se existe um histórico salvo."""
        return os.path.exists(self.path)

    def message_count(self) -> int:
        """Retorna quantas mensagens estão salvas no arquivo."""
        msgs = self.load()
        return len(msgs)
