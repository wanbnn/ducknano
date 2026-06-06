# 🦆 DuckNano

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-orange)]()
[![Size](https://img.shields.io/badge/SML-Self--Hosted-green?logo=ollama)]()

```Powershell
irm https://raw.githubusercontent.com/wanbnn/ducknano/main/install.ps1 | iex
```

> **Um agente de desenvolvimento minimalista e poderoso rodando 100% local via llama.cpp**

DuckNano é um agente de IA para terminal que se conecta a qualquer servidor compatível com a API OpenAI (como `llama.cpp`, `LM Studio` ou `Ollama`). Ele possui memória persistente via RAG local, compressão automática de contexto, e um conjunto de ferramentas integradas para ler, escrever, editar arquivos e executar comandos shell — tudo direto no seu workspace, sem depender de nenhuma API externa paga.

---

## ✨ Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| 🧠 **Memória Persistente (RAG)** | Arquiva fragmentos de conversa em disco e os recupera via índice trigrâmico local |
| 🗜️ **Compressão de Contexto** | Compacta automaticamente o histórico quando o limite de tokens se aproxima |
| 📁 **Ferramentas de Workspace** | Lê, escreve e edita arquivos diretamente no diretório de trabalho |
| 💻 **Execução de Shell** | Roda comandos bash/cmd com timeout de segurança e captura de saída |
| 🔍 **Busca no Workspace** | Indexa todos os arquivos do projeto com trigramas para buscas rápidas |
| 🎨 **UI Rica no Terminal** | Dashboard inicial, prompt contextual, setup guiado e painéis coloridos via `rich` |

---

## 🏗️ Arquitetura

```
ducknano/
├── app.py              # Ponto de entrada: UI de intro e loop principal
└── ducknano/
    ├── __init__.py
    ├── config.py       # Configurações globais e system prompt
    ├── harness.py      # Orquestrador: histórico, compressão, chamada ao modelo
    ├── memory.py       # MemoryManager: arquivamento e recuperação de memória (RAG)
    ├── openai_compatible.py # Cliente para endpoints OpenAI-compatible
    ├── rag.py          # LocalTrigramIndex: indexador e buscador de arquivos
    ├── slash_commands.py # Comandos / para provider e endpoints
    ├── terminal_gui.py # GUI de terminal: dashboard, setup, prompt e painéis
    ├── ui.py           # Compatibilidade para imports antigos da UI
    └── tools.py        # Ferramentas: read_file, write_file, edit_file, run_bash, ...
```

### Fluxo de Execução

```
Usuário digita → harness.step()
    ├─ [contexto cheio?] → compress_context() → arquiva no RAG
    ├─ query_model() → chama a API do llama.cpp
    ├─ Exibe resposta no terminal (painel Rich)
    ├─ parse_and_execute_commands() → executa ferramentas
    └─ [há resultados?] → step() recursivo com os resultados
```

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.10+
- Um servidor de LLM local compatível com a API OpenAI v1 (ex: [llama.cpp](https://github.com/ggerganov/llama.cpp), [LM Studio](https://lmstudio.ai/), [Ollama](https://ollama.com/))

### Instalando dependências

```bash
pip install requests rich
```

### Configuração

Por padrão, o DuckNano aponta para `http://localhost:8080/v1`. Para usar um endereço diferente, configure pelo chat:

```text
/setup
/providers
/provider use openai api_key=sk-... model=gpt-4.1
/provider use openrouter api_key=sk-or-... model=openai/gpt-4.1
/provider use nvidia api_key=nvapi-...
/provider use minimax api_key=...
/provider use kimi api_key=...
/provider use azure-foundry resource_url=https://SEU-RESOURCE.openai.azure.com api_key=... model=deployment-ou-modelo
/temperature 0.2
```

Também é possível usar variáveis de ambiente antes de iniciar:

```bash
# Linux / macOS
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_API_KEY="opcional"
export MODEL_NAME="nome-do-modelo"

# Windows (PowerShell)
$env:OPENAI_BASE_URL="http://localhost:11434/v1"
$env:OPENAI_API_KEY="opcional"
$env:MODEL_NAME="nome-do-modelo"
```

---

## ▶️ Uso

```bash
# Rodar diretamente
python app.py

# Ou via launcher no Windows
ducknano.bat
```

### Comandos Especiais no Chat

| Comando | Ação |
|---|---|
| `exit` / `quit` / `sair` | Encerra o agente |
| `clear` / `limpar` | Reinicia o histórico e limpa a tela |
| `/setup` | Abre uma UI guiada para configurar provider, API key, modelo e temperature |
| `/providers` | Lista presets: Local, OpenAI, NVIDIA NIM, OpenRouter, Azure/Foundry, MiniMax e Kimi |
| `/provider show` | Mostra o provider OpenAI-compatible ativo |
| `/provider use <preset> api_key=... model=...` | Aplica um provider pre-configurado |
| `/provider set base_url=... api_key=... model=...` | Configura um provider `/v1` |
| `/models` | Executa `GET /v1/models` |
| `/model <id>` | Define o modelo e consulta `GET /v1/models/{id}` |
| `/temperature <numero\|off>` | Configura `temperature` quando o provider suporta |
| `/files` | Executa `GET /v1/files` |
| `/upload <path> [purpose]` | Executa `POST /v1/files` |
| `/embeddings <texto>` | Executa `POST /v1/embeddings` |
| `/transcribe <path> [model]` | Executa `POST /v1/audio/transcriptions` |
| `/image <prompt> [model=...] [size=1024x1024]` | Executa `POST /v1/images/generations` |

### Ferramentas do Agente (usadas automaticamente pelo LLM)

```
[CMD:read_file path="arquivo.py" start_line=1 end_line=50]
[/CMD]

[CMD:write_file path="novo_arquivo.py"]
conteúdo do arquivo
[/CMD]

[CMD:edit_file path="arquivo.py"]
SEARCH:
linha exata a encontrar
REPLACE:
nova linha
[/CMD]

[CMD:run_bash]
comando de terminal
[/CMD]

[CMD:recall_memory query="busca na memória"]
[/CMD]

[CMD:search_workspace query="busca no projeto"]
[/CMD]
```

---

## ⚙️ Configuração Avançada

Edite `ducknano/config.py` para ajustar os limites de contexto:

```python
MAX_CONTEXT_TOKENS = 24000      # Janela máxima de contexto
COMPRESSION_THRESHOLD = 12000   # Tokens para acionar a compressão
```

A memória persistente é salva em `.duck/memory/` no diretório de trabalho atual.

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Veja o [CONTRIBUTING.md](CONTRIBUTING.md) para diretrizes.

---

## 🔒 Segurança

Este projeto executa comandos shell arbitrários fornecidos pelo LLM. Leia o [SECURITY.md](SECURITY.md) para entender os riscos e boas práticas.

---

## 📄 Licença

Distribuído sob os termos do proprietário do repositório. Consulte o proprietário para informações de licenciamento.
