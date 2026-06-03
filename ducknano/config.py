# -*- coding: utf-8 -*-
import os
from rich.console import Console

console = Console()

# Configuracoes Gerais
LLAMA_API_URL = os.environ.get("LLAMA_API_URL", "http://localhost:8080/v1/chat/completions")
WORKSPACE_DIR = os.getcwd()
MEMORY_DIR = os.path.join(WORKSPACE_DIR, ".duck", "memory")

MAX_CONTEXT_TOKENS = 24000
COMPRESSION_THRESHOLD = 12000

# Garante a existencia da pasta de memoria persistente
os.makedirs(MEMORY_DIR, exist_ok=True)

# Prompt de Sistema Minimalista com as novas ferramentas de RAG e Memory sob demanda
SYSTEM_PROMPT = """You are an ultra-compact developer agent.
You must NEVER output standard markdown code blocks like ```python.
To interact with the workspace and memory, you MUST use ONLY these plain-text commands:

[CMD:read_file path="relative/path" start_line=1 end_line=100]
[/CMD]

[CMD:write_file path="relative/path"]
example of file content
[/CMD]

[CMD:edit_file path="relative/path"]
SEARCH:
exact lines to find
REPLACE:
new lines to replace with
[/CMD]

[CMD:run_bash]
example shell command
[/CMD]

[CMD:recall_memory query="search query"]
[/CMD]

[CMD:search_workspace query="search query"]
[/CMD]

Note: read_file can read a maximum of 100 lines per call. Format matches must be exact."""
