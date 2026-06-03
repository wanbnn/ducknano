# Guia de Contribuição — DuckNano

Obrigado pelo interesse em contribuir! DuckNano é um projeto pequeno e focado — contribuições que mantenham a filosofia minimalista são muito bem-vindas.

---

## 🧭 Filosofia do Projeto

Antes de abrir um PR, tenha em mente os princípios que guiam o DuckNano:

- **Zero dependências externas de IA** — tudo roda localmente, sem APIs pagas.
- **Código simples antes de código inteligente** — prefira clareza a otimização prematura.
- **Terminal-first** — a interface é o terminal; não há planos para uma UI gráfica.
- **Sem dependências desnecessárias** — o projeto usa apenas `requests` e `rich`. Pense bem antes de adicionar uma nova dependência.

---

## 🐛 Reportando Bugs

1. Verifique se o bug já foi reportado nas [Issues](../../issues).
2. Abra uma issue com o template abaixo:

```
**Descrição do bug**
Uma descrição clara e concisa do problema.

**Passos para reproduzir**
1. Rodei `python app.py`
2. Digitei '...'
3. Erro: ...

**Comportamento esperado**
O que deveria ter acontecido.

**Ambiente**
- OS: [ex: Windows 11, Ubuntu 24.04]
- Python: [ex: 3.11.2]
- Servidor LLM: [ex: llama.cpp v0.0.3060, LM Studio 0.3.x]
- Modelo: [ex: Qwen2.5-Coder-7B-Q4_K_M]
```

---

## 💡 Sugerindo Melhorias

Para sugestões de novas funcionalidades, abra uma issue com o prefixo `[Feature Request]` e descreva:

- **O problema que você quer resolver** (não apenas a solução)
- **A solução proposta**
- **Alternativas consideradas**

---

## 🔧 Contribuindo com Código

### 1. Fork e clone

```bash
git clone https://github.com/SEU_USUARIO/ducknano.git
cd ducknano
```

### 2. Crie uma branch descritiva

```bash
# Para correções de bugs
git checkout -b fix/descricao-do-bug

# Para novas funcionalidades
git checkout -b feat/nome-da-funcionalidade
```

### 3. Configure o ambiente

```bash
pip install requests rich
```

> **Dica:** Recomenda-se usar um ambiente virtual:
> ```bash
> python -m venv .venv
> .venv\Scripts\activate  # Windows
> source .venv/bin/activate  # Linux/macOS
> ```

### 4. Faça suas alterações

- Mantenha cada commit focado em uma única mudança lógica.
- Escreva mensagens de commit claras seguindo o padrão [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: adiciona suporte ao comando list_dir
fix: corrige escape de path no read_file no Windows
docs: atualiza exemplos de uso no README
refactor: extrai lógica de parsing para função separada
```

### 5. Verifique seu código

Antes de abrir o PR, certifique-se de que:

- [ ] O código roda sem erros (`python app.py`)
- [ ] Não há arquivos temporários ou de debug adicionados
- [ ] A pasta `.duck/` e arquivos de cache não foram commitados
- [ ] Imports desnecessários foram removidos
- [ ] Comentários em português ou inglês são claros e úteis

### 6. Abra o Pull Request

- Use o título no formato: `[tipo]: breve descrição`
- Descreva **o quê** mudou e **por quê**
- Se fechar uma issue, referencie com `Closes #123`

---

## 📐 Convenções de Código

- **Encoding**: todos os arquivos Python começam com `# -*- coding: utf-8 -*-`
- **Tipagem**: use type hints sempre que possível (`-> str`, `List[Dict]`, etc.)
- **Strings de erro**: em inglês, para facilitar buscas
- **Saídas de terminal**: via `console.print()` do `rich` (nunca `print()` direto)
- **Sem dependências de stdlib além do necessário**: evite adicionar imports sem necessidade

---

## 📁 Estrutura de Arquivos para Novas Funcionalidades

| Tipo de adição | Onde colocar |
|---|---|
| Nova ferramenta do agente (CMD) | `ducknano/tools.py` |
| Nova configuração global | `ducknano/config.py` |
| Nova classe de suporte | Novo arquivo em `ducknano/` |
| Mudança na UI do terminal | `app.py` |

---

## 🙏 Código de Conduta

Este projeto adota um ambiente respeitoso e colaborativo. Seja gentil nos comentários de code review e nas issues. Críticas construtivas são bem-vindas; grosseria não.
