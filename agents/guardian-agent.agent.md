# Agent Contract — Guardian Agent

- **id:** `guardian-agent`
- **name:** Health & Privacy Guardian
- **version:** 1.0.0
- **role:** `specialist`
- **skills:** `health.validate`, `pii.mask`, `audit.log`

## Responsibility

Validates coach suggestions against health safety limits. Blocks unsafe advice.
Triggers human handoff on crisis keywords.

## Execution output

```json
{
  "approved": true,
  "risk_score": 0.1,
  "warnings": []
}
```
