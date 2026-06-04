# 🦆 DuckNano

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
| 🎨 **UI Rica no Terminal** | Animação de intro, painéis coloridos e barra de contexto via `rich` |

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
    ├── rag.py          # LocalTrigramIndex: indexador e buscador de arquivos
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

Por padrão, o DuckNano aponta para `http://localhost:8080/v1/chat/completions`. Para usar um endereço diferente, exporte a variável de ambiente antes de iniciar:

```bash
# Linux / macOS
export LLAMA_API_URL="http://localhost:11434/v1/chat/completions"

# Windows (PowerShell)
$env:LLAMA_API_URL="http://localhost:11434/v1/chat/completions"
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
