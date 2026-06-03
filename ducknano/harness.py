# -*- coding: utf-8 -*-
import requests
from typing import List, Dict, Tuple
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape
from rich import box

from ducknano.config import (
    SYSTEM_PROMPT, LLAMA_API_URL, COMPRESSION_THRESHOLD, MAX_CONTEXT_TOKENS, console, WORKSPACE_DIR
)
from ducknano.rag import LocalTrigramIndex
from ducknano.memory import MemoryManager
from ducknano.tools import parse_and_execute_commands, preprocess_response

class LlamaHarness:
    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.workspace_index = LocalTrigramIndex(WORKSPACE_DIR)
        self.memory_manager = MemoryManager()
        self.total_tokens_used = 0
        self.init_history()

    def init_history(self):
        # Few-Shot prompts demonstrating on-demand tool usage
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "Hello! Everything is great, and you? How can I help with your development today?"},
            {"role": "user", "content": "Do you remember which test script we created earlier?"},
            {"role": "assistant", "content": '[CMD:recall_memory query="test script"]\n[/CMD]\nRecalling memory...'},
            {"role": "user", "content": "Results of executed commands:\nRecalled memory:\n[USER]: Create the test script test_permissions.py.\n[ASSISTANT]: Script created successfully."},
            {"role": "assistant", "content": "Yes, we created the script `test_permissions.py` to test the TrigramIndex earlier."},
            {"role": "user", "content": "Show me what is in the file test_permissions.py."},
            {"role": "assistant", "content": '[CMD:read_file path="test_permissions.py" start_line=1 end_line=100][/CMD]\nReading file...'},
            {"role": "user", "content": "Results of executed commands:\nLines 1 to 1 of 1 in test_permissions.py:\n001: print(\"Test OK\")"},
            {"role": "assistant", "content": "The file `test_permissions.py` only contains `print(\"Test OK\")`."}
        ]

    def query_model(self, prompt_messages: List[Dict[str, str]]) -> Tuple[str, int]:
        payload = {
            "messages": prompt_messages,
            "temperature": 0.1,
            "stream": False
        }
        try:
            response = requests.post(LLAMA_API_URL, json=payload, timeout=1240)
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            total_tokens = usage.get("total_tokens", len(content) // 4)
            
            return content, total_tokens
        except Exception as e:
            console.print(f"[bold red]Erro ao conectar com llama.cpp: {escape(str(e))}[/bold red]")
            return "", 0

    def compress_context(self):
        """
        Compacta as mensagens intermediarias antigas para economizar tokens,
        garantindo que a pergunta atual (ultima mensagem) nunca seja afetada.
        """
        if len(self.history) <= 12:
            return  # Nao ha historico intermediario suficiente para compactar

        console.print("[yellow]Compactando contexto ativo para economizar tokens...[/yellow]")
        
        # 1. Isola e protege a pergunta atual do usuario (ultima mensagem do historico)
        current_query = self.history[-1]
        
        # 2. Captura apenas as mensagens antigas (do indice 11 ate a penultima mensagem)
        messages_to_evict = [msg for msg in self.history[11:-1] if not msg["content"].startswith("[RECALLED_MEM]")]
        
        if not messages_to_evict:
            return

        # 3. Envia as mensagens antigas para o RAG (.duck/memory) antes de apaga-las
        self.memory_manager.archive_interaction_chunk(messages_to_evict)
        
        # 4. Create a short summary of what was discussed in those old messages
        conversation_log = [f"{m['role'].upper()}: {m['content']}" for m in messages_to_evict]
        summary_prompt = "Compress the history above into an ultra-compact state summary in a few lines."
        
        compression_messages = [
            {"role": "system", "content": "You are an efficient summarizer."},
            {"role": "user", "content": "\n".join(conversation_log) + f"\n\n{summary_prompt}"}
        ]
        
        summary_content, _ = self.query_model(compression_messages)
        
        # 5. Reconstrói o historico preservando a ancoragem (0 a 10), injetando o resumo,
        # e recolocando a pergunta atual do usuario de forma intacta no final do prompt
        self.history = self.history[:11] + [
            {"role": "user", "content": f"[RECALLED_MEM: Resumo das acoes anteriores: {summary_content}]"},
            current_query
        ]
        console.print("[green]Contexto reestruturado preservando a pergunta atual.[/green]")

    def step(self, user_input: str):
        self.history.append({"role": "user", "content": user_input})

        if self.total_tokens_used > COMPRESSION_THRESHOLD:
            self.compress_context()

        # Spinner loader enquanto o modelo pensa
        with console.status("[bold #00ffcc]Evaluating...[/bold #00ffcc]", spinner="dots"):
            response_text, tokens_used = self.query_model(self.history)
        self.total_tokens_used = tokens_used
        
        # Painel da resposta do assistente
        console.print(Panel(
            Text(response_text, style="white"),
            title="[bold #00ffcc]💬 Model[/bold #00ffcc]",
            border_style="#00ffcc",
            box=box.ROUNDED
        ))
        
        # Barra visual de tokens do contexto
        pct = min(1.0, self.total_tokens_used / MAX_CONTEXT_TOKENS)
        filled_chars = int(pct * 20)
        bar = "█" * filled_chars + "░" * (20 - filled_chars)
        console.print(f"[dim]Context: [{bar}] {self.total_tokens_used}/{MAX_CONTEXT_TOKENS} tokens[/dim]\n")

        corrected_response = preprocess_response(response_text)
        self.history.append({"role": "assistant", "content": corrected_response})

        cmd_results = parse_and_execute_commands(corrected_response, self.workspace_index, self.memory_manager)
        
        if cmd_results:
            results_str = "\n".join(cmd_results)
            console.print(Panel(
                Text(results_str, style="#ff55ff"),
                title="[bold #ff55ff]⚡ Actions[/bold #ff55ff]",
                border_style="#ff55ff",
                box=box.ROUNDED
            ))
            self.step(f"Results of executed commands:\n{results_str}")
