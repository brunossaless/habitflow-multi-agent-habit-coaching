# Agent Contract — Analyzer Agent

- **id:** `analyzer-agent`
- **name:** Habit Analyzer
- **version:** 1.0.0
- **role:** `specialist`
- **skills:** `metrics.extract`, `text.parse`

## Responsibility

Extracts structured metrics from free-text notes (distance, water, sleep, duration).

## Execution output

```json
{
  "metrics": { "distance_km": 5, "water_liters": 2 },
  "confidence": 0.94,
  "requires_confirmation": false
}
```
