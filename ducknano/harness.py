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
from rich.live import Live
from rich import box

from ducknano.config import (
    SYSTEM_PROMPT, PROVIDER_CONFIG, COMPRESSION_THRESHOLD, MAX_CONTEXT_TOKENS,
    console, WORKSPACE_DIR, provider_endpoint, provider_headers, provider_temperature
)
from ducknano.rag import LocalTrigramIndex
from ducknano.memory import MemoryManager
from ducknano.tools import parse_and_execute_commands, preprocess_response
from ducknano.history import HistoryManager

class LlamaHarness:
    def __init__(self, hist_enabled: bool = False):
        self.history: List[Dict[str, str]] = []
        self.workspace_index = LocalTrigramIndex(WORKSPACE_DIR)
        self.memory_manager = MemoryManager()
        self.total_tokens_used = 0
        self.hist_enabled = hist_enabled

        # Gerenciador de histórico persistente
        history_path = os.path.join(WORKSPACE_DIR, ".duck", "history", "session.json")
        self.history_manager = HistoryManager(history_path)

        # Auto-detect LLM model name
        self.model_name = PROVIDER_CONFIG.get("model") or os.environ.get("MODEL_NAME")
        if not self.model_name:
            self.model_name = self._detect_llm_model()

        self.init_history()

        # Se o modo de histórico está ativo, restaurar conversa anterior
        if self.hist_enabled and self.history_manager.exists():
            restored = self.history_manager.load()
            if restored:
                self.history.extend(restored)
                console.print(
                    f"[bold #00ffcc]📂 Histórico restaurado:[/bold #00ffcc] "
                    f"[dim]{len(restored)} mensagens carregadas de sessão anterior.[/dim]"
                )

        # Loop tracking and trajectory logging setup
        self.recent_commands = []
        self.consecutive_repeats = 0
        self.trajectories_dir = os.path.join(WORKSPACE_DIR, ".duck", "trajectories")
        os.makedirs(self.trajectories_dir, exist_ok=True)
        self.session_timestamp = int(time.time())
        self.trajectory_log = []

    def reload_provider_settings(self):
        self.model_name = PROVIDER_CONFIG.get("model") or os.environ.get("MODEL_NAME") or self._detect_llm_model()
        self.workspace_index.rebuild_index()

    def _detect_llm_model(self) -> str:
        # 1. Tenta usar a variável de ambiente se estiver configurada e não for vazia
        env_model = os.environ.get("MODEL_NAME", "").strip()
        if env_model:
            return env_model

        # 2. Caso contrário, tenta consultar o endpoint da API para autodetecção
        try:
            r = requests.get(provider_endpoint("/models"), headers=provider_headers(), timeout=5)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for m in data:
                    m_id = m.get("id", "")
                    if not m_id:
                        continue
                    
                    # Filtra IDs que contenham palavras comuns de modelos de embedding/busca
                    is_embedding = any(
                        term in m_id.lower() 
                        for term in ["embed", "similarity", "rerank", "vector"]
                    )
                    
                    if not is_embedding:
                        return m_id
                
                # Fallback caso haja dados mas todos tenham sido filtrados (improvável)
                if data:
                    return data[0].get("id", "qwopus3.5-9b-coder")
        except Exception:
            pass
        
        # 3. Fallback de segurança se a API estiver inacessível ou sem modelos cadastrados
        return "qwopus3.5-9b-coder"

    def init_history(self, clear_persisted: bool = False):
        """Reinicializa o histórico em memória com os few-shot anchors.
        Se clear_persisted=True, apaga também o histórico salv em disco.
        """
        # Few-Shot prompts demonstrating on-demand tool usage
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Crie um script de soma em python e teste-o."},
            {"role": "assistant", "content": '[CMD:write_file path="sum.py"]\ndef soma(a, b):\n    return a + b\n[/CMD]\nCriando o arquivo sum.py...'},
            {"role": "user", "content": "Current Workspace Files: [sum.py]\n\nResults of executed commands:\nFile created/updated successfully: sum.py"},
            {"role": "assistant", "content": '[CMD:run_bash]\npython -c "import sum; assert sum.soma(2, 3) == 5; print(\'Teste OK\')"\n[/CMD]\nExecutando teste no terminal...'},
            {"role": "user", "content": "Current Workspace Files: [sum.py]\n\nResults of executed commands:\nSTDOUT:\nTeste OK"},
            {"role": "assistant", "content": "O script `sum.py` foi criado e testado com sucesso no workspace."},
            {"role": "user", "content": "Ok, agora que entendeu os comandos, vamos começar do inicio como se fosse uma nova sessão."}
        ]
        if clear_persisted:
            self.history_manager.clear()

    def query_model(self, prompt_messages: List[Dict[str, str]], temperature: float = None) -> Tuple[str, int]:
        payload = {
            "model": self.model_name,
            "messages": prompt_messages,
            "stream": True
        }
        if temperature is not None:
            payload["temperature"] = temperature
        try:
            response = requests.post(
                provider_endpoint("/chat/completions"),
                headers=provider_headers(),
                json=payload,
                timeout=1240,
                stream=True,
            )
            if response.status_code >= 400 and "temperature" in payload:
                error_text = response.text.lower()
                if "temperature" in error_text or "unsupported" in error_text:
                    payload.pop("temperature", None)
                    response = requests.post(
                        provider_endpoint("/chat/completions"),
                        headers=provider_headers(),
                        json=payload,
                        timeout=1240,
                        stream=True,
                    )
            response.raise_for_status()

            reasoning_buf = ""
            content_buf = ""
            total_tokens = 0
            in_reasoning = False

            # --- Thinking panel (streams live) ---
            thinking_text = Text("", style="dim #00cccc")
            thinking_panel = Panel(
                thinking_text,
                title="[bold dim #00cccc]🧠 Thinking[/bold dim #00cccc]",
                border_style="dim #00cccc",
                box=box.ROUNDED,
            )

            # --- Response panel (streams live) ---
            response_text_obj = Text("", style="white")
            response_panel = Panel(
                response_text_obj,
                title="[bold #00ffcc]💬 Model[/bold #00ffcc]",
                border_style="#00ffcc",
                box=box.ROUNDED,
            )

            # We start with the thinking panel; switch to response panel once
            # actual content starts arriving.
            active_panel = thinking_panel
            showed_response_panel = False

            with Live(active_panel, console=console, refresh_per_second=15) as live:
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                    if not line.startswith("data: "):
                        continue
                    data_str = line[len("data: "):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choice = chunk.get("choices", [{}])[0]
                    delta = choice.get("delta", {})

                    # Accumulate usage if provided in the final chunk
                    if "usage" in chunk:
                        total_tokens = chunk["usage"].get("total_tokens", total_tokens)

                    r_delta = delta.get("reasoning_content") or ""
                    c_delta = delta.get("content") or ""

                    if r_delta:
                        reasoning_buf += r_delta
                        thinking_text.append(r_delta)
                        live.update(thinking_panel)

                    if c_delta:
                        if not showed_response_panel:
                            # Switch to response panel once content starts
                            showed_response_panel = True
                            live.update(response_panel)
                        content_buf += c_delta
                        response_text_obj.append(c_delta)
                        live.update(response_panel)

            # If no tokens reported via streaming, estimate from content length
            if total_tokens == 0:
                total_tokens = (len(reasoning_buf) + len(content_buf)) // 4

            # --- ALTERAÇÃO AQUI: Combinar o pensamento com o conteúdo final ---
            full_response = ""
            if reasoning_buf:
                full_response += f"<thought>\n{reasoning_buf}\n</thought>\n"
            full_response += content_buf

            return full_response, total_tokens
        except Exception as e:
            console.print(f"[bold red]Erro ao conectar com provider OpenAI-compatible: {escape(str(e))}[/bold red]")
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

    def step(self, user_input: str, is_recursive: bool = False, depth: int = 0, original_query: str = ""):
        if depth >= 120:
            console.print("[yellow]Safe limit of recursion reached. Halted execution to prevent infinite loop.[/yellow]")
            return

        if not is_recursive:
            self.recent_commands = []
            self.consecutive_repeats = 0
            original_query = user_input  # Salva a query original antes de qualquer modificação
            
            # Inject active workspace files if any exist at the start of the session
            workspace_files = self.workspace_index.files
            if workspace_files:
                files_str = ", ".join(workspace_files)
                user_input = f"Current Workspace Files: [{files_str}]\n\nUser Query: {user_input}"

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
            temp = provider_temperature()
            active_history = self.history.copy()
            
            # Apply dynamic temperature and warning constraints if we are in a loop
            total_attempts = self.consecutive_repeats + retry_count
            if total_attempts > 0:
                if temp is not None:
                    temp = min(0.85, temp + 0.20 * total_attempts)
                
                # Format recent commands to explicitly tell the model what to avoid
                recent_cmds_str = ", ".join([f"'{c}'" for c in self.recent_commands[-5:]]) if self.recent_commands else "None"
                warning_msg = (
                    f"[SYSTEM WARNING / AVISO DO SISTEMA]\n"
                    f"You are repeating commands! / Você está repetindo comandos!\n"
                    f"DO NOT execute any of these recent commands again: / NÃO execute nenhum destes comandos recentes novamente:\n"
                    f"[{recent_cmds_str}]\n"
                    f"You must change your strategy, use different search terms, read a different file, or use a different tool.\n"
                    f"Você deve mudar sua estratégia, usar termos de busca diferentes, ler um arquivo diferente ou usar outra ferramenta.\n"
                    f"----------------------------------------\n"
                )
                if active_history:
                    last_msg = active_history[-1].copy()
                    last_msg["content"] = warning_msg + last_msg["content"]
                    active_history[-1] = last_msg

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
        # The streaming output already rendered the response panel live;
        # no need to reprint it here.
        
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

        # Persistir histórico em disco se modo --hist estiver ativo
        if self.hist_enabled:
            self.history_manager.save(self.history)

        if cmd_results:
            results_str = "\n".join(cmd_results)
            console.print(Panel(
                Text(results_str, style="#ff55ff"),
                title="[bold #ff55ff]⚡ Actions[/bold #ff55ff]",
                border_style="#ff55ff",
                box=box.ROUNDED
            ))
            
            # Inject active workspace files if any exist
            workspace_files = self.workspace_index.files
            files_str = ", ".join(workspace_files) if workspace_files else "None"
            # Inclui a query original para que o modelo não perca o contexto do que foi pedido
            original_query_reminder = f"[Contexto: o usuário perguntou originalmente: {original_query}]\n\n" if original_query else ""
            feedback_msg = (
                f"{original_query_reminder}"
                f"Current Workspace Files: [{files_str}]\n\n"
                f"Results of executed commands:\n{results_str}"
            )
            
            self.step(feedback_msg, is_recursive=True, depth=depth+1, original_query=original_query)


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
    normalized = re.sub(r'\s+', '', cmd)
    # Normalize path separators: treat forward and back slashes as equivalent
    normalized = normalized.replace('\\', '/')
    # Lowercase to avoid case-insensitive duplicates on Windows
    normalized = normalized.lower()
    return normalized
