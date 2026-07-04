# Agent Contract — Coach Agent

- **id:** `coach-agent`
- **name:** Personal Habit Coach
- **version:** 1.0.0
- **role:** `specialist`
- **skills:** `patterns.detect`, `insights.generate`, `suggestions.create`

## Responsibility

Analyzes historical habit data via RAG, detects patterns, generates personalized
insights and actionable micro-habit suggestions.

## Execution output

```json
{
  "insights": [{ "pattern": "...", "confidence": 0.91 }],
  "suggestions": [{ "action": "...", "reasoning": "..." }]
}
```
