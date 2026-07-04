# HabitFlow Team — Multi-Agent Habit Coaching

Sistema multi-agente para coaching de hábitos, seguindo o modelo da aula:
**Agent Cards + MCP + A2A + Coordenador com delegação**.

Baseado em [kanban-multiagente](https://github.com/naubergois/kanban-multiagente).

## Intuito dos multi-agentes

O HabitFlow Team simula um **time de coaching de hábitos** em que cada agente tem uma responsabilidade clara — como numa equipe real de produto. Em vez de um único modelo fazer tudo, o trabalho é dividido em etapas especializadas:

| Problema | Por que multi-agente? |
|---|---|
| Texto livre do usuário ("corri 5km e bebi 2L") | Um agente **analisa** métricas, outro **persiste** dados — separação de captura e extração |
| Insights personalizados | O **coach** consulta histórico (RAG) sem misturar lógica de persistência |
| Segurança | O **guardian** revisa sugestões *antes* de chegar ao usuário — camada independente |
| Rastreabilidade | Cada card no Kanban mostra **quem executou** o quê — auditoria por agente |

O objetivo pedagógico é demonstrar **dinâmicas de equipe multi-agente**: contratos explícitos (Agent Cards), ferramentas compartilhadas (MCP), comunicação entre agentes (A2A) e um coordenador que **delega** sem executar o trabalho dos especialistas.

## Como os agentes operam

### Visão geral do fluxo

```
Usuário envia check-in ou pede análise
        │
        ▼
┌─────────────────┐
│  Coordinator    │  ← único ponto de entrada; cria cards no Kanban
└────────┬────────┘
         │ A2A: task.delegate
         ▼
┌─────────────────┐     MCP: card.create / card.assign / card.move
│  Especialista   │ ──► executa a tarefa do card
└────────┬────────┘
         │ A2A: task.completed
         ▼
┌─────────────────┐
│  Coordinator    │  ← move card para review → done
└────────┬────────┘
         │ A2A: sprint.report
         ▼
      Usuário recebe feedback
```

### Três camadas de comunicação

1. **Agent Cards** (`a2a/agent-cards/`) — Ficha de cada agente: id, papel, skills e contrato. Define *quem* pode fazer *o quê*.
2. **MCP Server** (`mcp_server/`) — Ferramentas compartilhadas do Kanban (`board.get`, `card.create`, `card.assign`, `card.move`, `activity.log`). É a **fonte de verdade** do estado do pipeline.
3. **A2A** (`a2a/a2a-protocol.md`) — Mensagens entre agentes (`task.delegate`, `task.accepted`, `task.completed`, `review.verdict`). Registra *quem falou com quem* e em qual etapa.

### Papel de cada agente

| Agente | Papel | O que faz na prática |
|---|---|---|
| **coordinator** | Orquestrador | Recebe a entrada do usuário, monta o pipeline de cards, roteia cada card ao especialista certo e só move para `done` após `task.completed`. **Não executa** trabalho de hábito. |
| **collector-agent** | Captura | Persiste o check-in (entradas de hábito, humor, timestamp) no banco SQLite via MCP. |
| **analyzer-agent** | NLP / métricas | Extrai dados estruturados do texto livre — km, litros de água, minutos — com score de confiança. |
| **coach-agent** | Insights | Consulta histórico (últimos 14 dias), detecta padrões (ex.: sono baixo nas terças → menos exercício) e gera sugestões acionáveis. |
| **guardian-agent** | Segurança | Valida guardrails: bloqueia sugestões de sono inseguras e aciona handoff humano se detectar palavras de crise. |
| **notifier-agent** | Entrega | Formata insights e sugestões em mensagem amigável para o usuário. |

### Roteamento (labels → especialista)

O coordenador cria cards com **labels**; o MCP roteia automaticamente:

| Label | Agente |
|---|---|
| `collect`, `persist` | collector-agent |
| `extract` | analyzer-agent |
| `patterns`, `coach` | coach-agent |
| `safety` | guardian-agent |
| `notify` | notifier-agent |

### Pipelines disponíveis

| Modo | Cards | Quando usar |
|---|---|---|
| **Check-in** | Coletar → Extrair métricas → Persistir | Usuário registra um hábito do dia |
| **Análise** | Padrões → Insights → Guardian → Notificar | Pedido de análise semanal |
| **Automático** | Check-in + Análise (7 cards) | Fluxo completo em uma execução |

### Ciclo de vida de um card (Kanban ↔ A2A)

| Coluna Kanban | Evento A2A |
|---|---|
| `todo` | `task.delegate` — coordenador delega ao especialista |
| `in_progress` | `task.accepted` — especialista aceita e executa |
| `review` | `task.completed` — resultado gravado no card |
| `done` | `review.verdict` (pass) — coordenador fecha o card |

Cada movimentação gera eventos visíveis na UI (abas **A2A**, **MCP** e **Exec**).

## Arquitetura

```
habitflow-team/
├── agents/           # Contratos (.agent.md + .agent.json)
├── a2a/              # Protocolo A2A + Agent Cards
├── mcp/              # Contrato das tools MCP
├── mcp_server/       # FastMCP + SQLite (board + habit_logs)
├── runtime/          # Orchestrator (coordenador) + executors (especialistas)
├── web/              # Kanban visual + logs A2A/MCP
└── server.py         # Servidor web + API REST
```

## Quick start

```bash
cd habitflow-team
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # opcional — só para MCP server standalone

python3 server.py
# abra http://localhost:8080  (tenta portas 8080–8089 se ocupada)
```

## API

| Method | Path | Description |
|---|---|---|
| POST | `/api/sprint/run` | Executa pipeline completo |
| GET | `/api/board` | Estado do Kanban |
| GET | `/api/health` | Health check |

### Exemplo

```bash
curl -X POST http://localhost:8080/api/sprint/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Corri 5km e bebi 2L de água", "user_id": "demo-user", "mode": "auto"}'
```

Parâmetro `mode`: `auto` | `checkin` | `analysis`

## Fluxo na UI

1. Digite um check-in ou peça análise semanal
2. Escolha o modo (Automático, Check-in ou Análise semanal)
3. Clique **▶ Rodar Pipeline**
4. Veja os cards migrando no Kanban (5 colunas: backlog → done)
5. Abaixo do board: logs **A2A**, **MCP** e **Execuções**
6. Ao final, o **Feedback do Coach** aparece com insights e sugestões
7. Clique em um card em **Done** para ver o resultado detalhado do especialista

## Testes

```bash
python3 -m pytest tests/ -v
```

## Referências da aula

- Agent Cards: `a2a/agent-cards/`
- MCP tools: `mcp/habit-mcp-server.md`
- A2A protocol: `a2a/a2a-protocol.md`
- Repo referência: https://github.com/naubergois/kanban-multiagente

## Licença

Projeto educacional — desenvolvido para a atividade de dinâmicas de equipe multi-agente.
