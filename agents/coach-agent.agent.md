# Agent Contract — Coach Agent

- **id:** `coach-agent`
- **name:** Personal Habit Coach
- **version:** 1.0.0
- **role:** `specialist`
- **skills:** `patterns.detect`, `insights.generate`, `suggestions.create`

## Responsibility

Analyzes historical habit data via RAG, detects patterns, and generates a
**primary_action** recommendation (run more/less, drink more water, sleep more,
maintain) based on current metrics and user history.

## Skills

- `patterns.detect` — trend analysis over habit logs
- `insights.generate` — contextual insights from history
- `primary_action.recommend` — single best next action for the user

## Execution output

```json
{
  "primary_action": {
    "category": "exercise",
    "direction": "increase",
    "icon": "🏃",
    "title": "Corra um pouco mais",
    "action": "Próxima corrida: 5.5 km",
    "reasoning": "Distância abaixo da média recente",
    "confidence": 0.88
  },
  "insights": [{ "pattern": "...", "confidence": 0.91 }],
  "suggestions": [{ "action": "...", "reasoning": "..." }]
}
```
