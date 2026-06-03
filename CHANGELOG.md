# Changelog — DuckNano

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [Não publicado]

### Adicionado
- `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `.gitignore`, `requirements.txt` e `CHANGELOG.md` para padronização do repositório.

---

## [0.1.0] — Versão Inicial

### Adicionado
- Agente de terminal `LlamaHarness` com suporte à API OpenAI v1 local (llama.cpp).
- Sistema de ferramentas: `read_file`, `write_file`, `edit_file`, `run_bash`, `recall_memory`, `search_workspace`.
- Índice trigrâmico local (`LocalTrigramIndex`) para busca no workspace sem dependências externas.
- Gerenciador de memória persistente (`MemoryManager`) com arquivamento em `.duck/memory/`.
- Compressão automática de contexto ao atingir o limiar de tokens configurado.
- Animação de intro com efeito de plasma colorido via `rich`.
- Launcher Windows (`ducknano.bat`).
- Configuração via variável de ambiente `LLAMA_API_URL`.
