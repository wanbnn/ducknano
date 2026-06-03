# -*- coding: utf-8 -*-
import os
import re
import time
import json
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
        
        # Loop tracking and trajectory logging setup
        self.recent_commands = []
        self.consecutive_repeats = 0
        self.trajectories_dir = os.path.join(WORKSPACE_DIR, ".duck", "trajectories")
        os.makedirs(self.trajectories_dir, exist_ok=True)
        self.session_timestamp = int(time.time())
        self.trajectory_log = []


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

    def query_model(self, prompt_messages: List[Dict[str, str]], temperature: float = 0.1) -> Tuple[str, int]:
        payload = {
            "messages": prompt_messages,
            "temperature": temperature,
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

    def save_trajectory(self):
        filepath = os.path.join(self.trajectories_dir, f"session_{self.session_timestamp}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "session_id": self.session_timestamp,
                    "total_tokens_used": self.total_tokens_used,
                    "steps": self.trajectory_log
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red]Error saving trajectory: {e}[/red]")

    def step(self, user_input: str, is_recursive: bool = False):
        if not is_recursive:
            self.recent_commands = []
            self.consecutive_repeats = 0

        self.history.append({"role": "user", "content": user_input})

        if self.total_tokens_used > COMPRESSION_THRESHOLD:
            self.compress_context()

        max_retries = 3
        retry_count = 0
        response_text = ""
        tokens_used = 0
        current_commands = []
        is_loop = False
        corrected_response = ""

        while retry_count < max_retries:
            temp = 0.1
            active_history = self.history.copy()
            
            # Apply dynamic temperature and warning constraints if we are in a loop
            total_attempts = self.consecutive_repeats + retry_count
            if total_attempts > 0:
                temp = min(0.85, 0.1 + 0.20 * total_attempts)
                
                # Format recent commands to explicitly tell the model what to avoid
                recent_cmds_str = ", ".join([f"'{c}'" for c in self.recent_commands[-5:]]) if self.recent_commands else "None"
                warning_msg = (
                    f"WARNING: You are repeating commands. Your previous actions did not yield new information. "
                    f"DO NOT execute any of these recent commands again: [{recent_cmds_str}]. "
                    "You must change your query, search for different terms, read a different file, or use a different tool."
                )
                active_history.append({"role": "system", "content": warning_msg})

            # Spinner loader enquanto o modelo pensa
            with console.status("[bold #00ffcc]Evaluating...[/bold #00ffcc]", spinner="dots"):
                response_text, tokens_used = self.query_model(active_history, temperature=temp)
            self.total_tokens_used = tokens_used

            corrected_response = preprocess_response(response_text)
            current_commands = extract_commands(corrected_response)

            # Check if this generated response triggers a loop
            is_loop = False
            normalized_recent = [normalize_command(c) for c in self.recent_commands]
            for cmd in current_commands:
                if normalize_command(cmd) in normalized_recent:
                    is_loop = True
                    break

            if is_loop:
                retry_count += 1
                self.consecutive_repeats += 1
                console.print(f"[yellow]Auto-Correction: Loop detected. Discarding response and retrying (attempt {retry_count}/{max_retries})...[/yellow]")
                
                # Log the discarded retry attempt in the trajectory for SFT data
                step_record = {
                    "step_index": len(self.trajectory_log),
                    "timestamp": time.time(),
                    "user_input": user_input,
                    "assistant_response": corrected_response,
                    "consecutive_repeats": self.consecutive_repeats,
                    "commands": current_commands,
                    "results": ["Auto-Correction: Loop intercepted & response discarded."]
                }
                self.trajectory_log.append(step_record)
                self.save_trajectory()
                
                continue
            else:
                # Unique non-looping command generated successfully
                break

        # If retries exceeded and still in loop, we fall back to raising loop error results to break out.
        if is_loop:
            cmd_results = [
                "Error: Loop detected. You are repeating the exact same command block. "
                "Running this again will return the same result. You MUST change your strategy, "
                "use different search terms, or read a different file. DO NOT repeat commands."
            ]
        else:
            self.consecutive_repeats = 0
            # Execute the command results
            cmd_results = parse_and_execute_commands(corrected_response, self.workspace_index, self.memory_manager)
            if current_commands:
                self.recent_commands = (self.recent_commands + current_commands)[-10:]

        # Commit final accepted step to history and trajectory
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

        self.history.append({"role": "assistant", "content": corrected_response})

        # Record final successful step in trajectory
        step_record = {
            "step_index": len(self.trajectory_log),
            "timestamp": time.time(),
            "user_input": user_input,
            "assistant_response": corrected_response,
            "consecutive_repeats": self.consecutive_repeats,
            "commands": current_commands,
            "results": cmd_results
        }
        self.trajectory_log.append(step_record)
        self.save_trajectory()

        if cmd_results:
            results_str = "\n".join(cmd_results)
            console.print(Panel(
                Text(results_str, style="#ff55ff"),
                title="[bold #ff55ff]⚡ Actions[/bold #ff55ff]",
                border_style="#ff55ff",
                box=box.ROUNDED
            ))
            self.step(f"Results of executed commands:\n{results_str}", is_recursive=True)


def extract_commands(text: str) -> List[str]:
    # Match pattern for any CMD block
    pattern = re.compile(r'(\[CMD:[^\]]+\].*?\[/CMD\])', re.DOTALL)
    commands = [m.group(1).strip() for m in pattern.finditer(text)]
    if not commands:
        # Fallback in case [/CMD] was missed
        pattern_fallback = re.compile(r'(\[CMD:[^\]]+\])', re.DOTALL)
        commands = [m.group(1).strip() for m in pattern_fallback.finditer(text)]
    return commands


def normalize_command(cmd: str) -> str:
    # Remove all whitespace and newlines for comparison
    return re.sub(r'\s+', '', cmd)

