# Agent Contract — Collector Agent

- **id:** `collector-agent`
- **name:** Habit Collector
- **version:** 1.0.0
- **role:** `specialist`
- **skills:** `habit.capture`, `habit.persist`

## Responsibility

Captures daily habit check-ins and persists them via MCP `habit.log`.

## Execution output

```json
{
  "log_id": "uuid",
  "entries_saved": 2,
  "artifacts": ["data/checkin-{date}.json"]
}
```
