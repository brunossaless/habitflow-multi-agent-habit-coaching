# A2A Protocol — HabitFlow Team

Protocol version: **0.3.0**

## Message types

| Type | Direction | Description |
|---|---|---|
| `sprint.start` | user → coordinator | Start habit pipeline with user input |
| `task.delegate` | coordinator → specialist | Assign card to specialist |
| `task.accepted` | specialist → coordinator | Specialist accepts card |
| `task.completed` | specialist → coordinator | Card executed with result |
| `review.request` | specialist → guardian | Request safety review |
| `review.verdict` | guardian → coordinator | Pass/fail verdict |
| `sprint.report` | coordinator → user | Final pipeline report |

## A2A → Kanban column mapping

| A2A state | Kanban column |
|---|---|
| `task.delegate` | `todo` |
| `task.accepted` | `in_progress` |
| `task.completed` | `review` |
| `review.verdict` (pass) | `done` |

## Handoff payload

```json
{
  "type": "task.delegate",
  "from": "coordinator",
  "to": "analyzer-agent",
  "cardId": "HF-002",
  "payload": {
    "user_id": "uuid",
    "note": "Corri 5km em 32 minutos"
  }
}
```
