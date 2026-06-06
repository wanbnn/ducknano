# -*- coding: utf-8 -*-
import os
import json
from rich.console import Console

console = Console()

# Configuracoes Gerais
WORKSPACE_DIR = os.getcwd()
MEMORY_DIR = os.path.join(WORKSPACE_DIR, ".duck", "memory")
EMBEDDING_CACHE_FILE = os.path.join(MEMORY_DIR, "embeddings_cache.json")
PROVIDER_CONFIG_FILE = os.path.join(WORKSPACE_DIR, ".duck", "provider_config.json")

DEFAULT_PROVIDER_CONFIG = {
    "base_url": os.environ.get("OPENAI_BASE_URL", "http://localhost:8080/v1"),
    "api_key": os.environ.get("OPENAI_API_KEY", ""),
    "model": os.environ.get("MODEL_NAME", ""),
    "embedding_model": os.environ.get("EMBEDDING_MODEL", ""),
    "temperature": os.environ.get("MODEL_TEMPERATURE", "0.1"),
    "provider": os.environ.get("OPENAI_PROVIDER", "custom"),
}

PROVIDER_PRESETS = {
    "local": {
        "name": "Local OpenAI-compatible",
        "base_url": "http://localhost:8080/v1",
        "api_key": "",
        "model": "",
        "notes": "llama.cpp, LM Studio, Ollama ou outro servidor local.",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4.1",
        "notes": "Adicione api_key=sk-...",
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": "",
        "model": "",
        "notes": "Adicione api_key=$NVIDIA_API_KEY e escolha um modelo via /models.",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "",
        "model": "openai/gpt-4.1",
        "notes": "Adicione api_key=sk-or-... e ajuste model=provider/model.",
    },
    "azure-foundry": {
        "name": "Azure AI Foundry / Azure OpenAI",
        "base_url": "",
        "api_key": "",
        "model": "",
        "notes": "Use resource_url=https://<resource>.openai.azure.com ou base_url=https://<resource>.openai.azure.com/openai/v1.",
    },
    "minimax": {
        "name": "MiniMax API",
        "base_url": "https://api.minimax.io/v1",
        "api_key": "",
        "model": "",
        "notes": "Adicione api_key=... e escolha um modelo via /models.",
    },
    "kimi": {
        "name": "Kimi API / Moonshot",
        "base_url": "https://api.moonshot.ai/v1",
        "api_key": "",
        "model": "kimi-k2.6",
        "notes": "Adicione api_key=... se sua conta usar Moonshot/Kimi Open Platform.",
    },
}


def _normalize_base_url(base_url: str) -> str:
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        base_url = "http://localhost:8080/v1"
    if base_url.endswith("/chat/completions"):
        base_url = base_url[: -len("/chat/completions")]
    if not base_url.endswith("/v1"):
        base_url = base_url + "/v1"
    return base_url


def azure_foundry_base_url(resource_url: str) -> str:
    resource_url = (resource_url or "").strip().rstrip("/")
    if not resource_url:
        return ""
    if resource_url.endswith("/openai/v1"):
        return resource_url
    return f"{resource_url}/openai/v1"


def load_provider_config() -> dict:
    config = DEFAULT_PROVIDER_CONFIG.copy()
    legacy_url = os.environ.get("LLAMA_API_URL", "").strip()
    if legacy_url:
        config["base_url"] = _normalize_base_url(legacy_url)

    if os.path.exists(PROVIDER_CONFIG_FILE):
        try:
            with open(PROVIDER_CONFIG_FILE, "r", encoding="utf-8") as f:
                persisted = json.load(f)
            if isinstance(persisted, dict):
                config.update({k: v for k, v in persisted.items() if v is not None})
        except Exception:
            pass

    config["base_url"] = _normalize_base_url(config.get("base_url", ""))
    return config


PROVIDER_CONFIG = load_provider_config()


def save_provider_config(config: dict) -> dict:
    PROVIDER_CONFIG.update(config)
    PROVIDER_CONFIG["base_url"] = _normalize_base_url(PROVIDER_CONFIG.get("base_url", ""))
    os.makedirs(os.path.dirname(PROVIDER_CONFIG_FILE), exist_ok=True)
    with open(PROVIDER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(PROVIDER_CONFIG, f, indent=2, ensure_ascii=False)
    return PROVIDER_CONFIG.copy()


def provider_endpoint(path: str) -> str:
    return f"{PROVIDER_CONFIG['base_url']}/{path.lstrip('/')}"


def provider_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    api_key = (PROVIDER_CONFIG.get("api_key") or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def provider_temperature():
    value = str(PROVIDER_CONFIG.get("temperature", "")).strip()
    if not value or value.lower() in {"none", "off", "null"}:
        return None
    try:
        return float(value)
    except ValueError:
        return 0.1


LLAMA_API_URL = os.environ.get("LLAMA_API_URL", provider_endpoint("/chat/completions"))
EMBEDDINGS_API_URL = os.environ.get("EMBEDDINGS_API_URL", provider_endpoint("/embeddings"))

MAX_CONTEXT_TOKENS = int(os.environ.get("MAX_CONTEXT_TOKENS", "80000"))
COMPRESSION_THRESHOLD = int(os.environ.get("COMPRESSION_THRESHOLD", "60000"))

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

Note: read_file can read a maximum of 100 lines per call. Format matches must be exact.

ENVIRONMENT: You are running on Windows with PowerShell. Shell commands must use PowerShell syntax. PowerShell supports `mkdir -p` (via New-Item), `ls`, `cat`, `rm -r`, etc. DO NOT use CMD.exe-only syntax.

CRITICAL REFLECTION RULE: Before executing any tool, write a brief single-line thought/reflection explaining what you have tried previously and why this next command is different and necessary.
CRITICAL LOOP PREVENTION: If a search or tool command returns no relevant results, empty results, or results containing only build/cache files (like `.next/`, `node_modules/`), you MUST change your search query, use a different tool, or read a different file. NEVER repeat the same command or query consecutively.
CRITICAL SUCCESS RULE: If a command result shows "Command executed successfully." or the expected output, the task is DONE. Do NOT repeat or retry a successful command. Respond to the user confirming completion."""
