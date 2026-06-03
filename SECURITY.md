# Política de Segurança — DuckNano

## ⚠️ Aviso Importante

O DuckNano é uma ferramenta de **desenvolvimento local** que concede ao modelo de linguagem (LLM) a capacidade de executar comandos shell arbitrários (`run_bash`), ler e escrever arquivos no seu sistema de arquivos. **Use com discernimento.**

---

## 🛡️ Modelo de Ameaças

### O que o agente pode fazer

- **Ler** qualquer arquivo dentro do `WORKSPACE_DIR` (diretório de trabalho no momento do lançamento).
- **Escrever e sobrescrever** arquivos dentro do `WORKSPACE_DIR`.
- **Executar comandos shell** com os mesmos privilégios do usuário que iniciou o processo.
- **Acessar a rede** via comandos shell (ex: `curl`, `wget`, `pip install`).

### O que o agente NÃO faz por padrão

- Não envia dados para nenhuma API externa (toda a inferência é local).
- Não persiste credenciais nem tokens de acesso.
- Não tem acesso a variáveis de ambiente além de `LLAMA_API_URL`.

---

## 🔒 Boas Práticas de Uso

1. **Execute sempre em um diretório de projeto isolado.** O `WORKSPACE_DIR` é definido pelo diretório atual (`os.getcwd()`). Nunca execute o agente a partir de diretórios sensíveis como `~`, `C:\`, `/etc`, etc.

2. **Não forneça ao LLM informações sensíveis** no chat (senhas, tokens de API, chaves privadas). Mesmo que o modelo seja local, os chunks de memória são persistidos em disco em texto plano em `.duck/memory/`.

3. **Revise comandos shell suspeitos.** O agente imprime cada comando `[CMD:run_bash]` antes de executá-lo. Se um comando parecer inesperado, interrompa com `Ctrl+C`.

4. **Use modelos de confiança.** O comportamento do agente depende inteiramente do modelo carregado. Modelos de fontes desconhecidas podem gerar ações maliciosas.

5. **Timeout de 30 segundos.** Comandos shell têm um limite de execução de 30s para evitar travamentos, mas comandos que causam danos podem ser concluídos nesse intervalo.

6. **Proteja os arquivos de memória.** A pasta `.duck/memory/` contém o histórico de conversas em texto plano. Adicione-a ao `.gitignore` para não vazar informações de sessões passadas.

---

## 🚨 Reportando Vulnerabilidades

Este é um projeto pessoal/de uso local. Se você identificar um vetor de ataque relevante (ex: escape de diretório no `read_file`, injeção de comandos via `path`), por favor:

1. **Não abra uma issue pública** com detalhes do exploit.
2. Entre em contato diretamente com o mantenedor do repositório via e-mail ou mensagem privada.
3. Inclua:
   - Descrição do problema
   - Passos para reproduzir
   - Impacto potencial
   - Sugestão de correção (opcional, mas apreciada)

Agradecemos a divulgação responsável.

---

## 🔐 Versões Suportadas

| Versão | Suporte de Segurança |
|---|---|
| `main` (atual) | ✅ Recebe correções |
| Versões anteriores | ❌ Sem suporte |
