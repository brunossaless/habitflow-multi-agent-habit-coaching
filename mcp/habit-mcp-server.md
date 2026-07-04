# HabitFlow MCP Kanban Server

Exposes the habit coaching pipeline as MCP tools.

## Tools

| Tool | Actor | Description |
|---|---|---|
| `board_get_tool` | all | Current Kanban snapshot |
| `card_create_tool` | coordinator | Create pipeline card |
| `card_assign_tool` | coordinator | Assign to specialist |
| `card_move_tool` | coordinator, specialist | Move card between columns |
| `card_comment_tool` | all | Add comment |
| `activity_log_tool` | all | Audit trail |
| `activity_get_tool` | all | Read activity log |

## Run (stdio)

```bash
python mcp_server/server.py
```

## Connect from Cursor

```json
{
  "mcpServers": {
    "habitflow-kanban": {
      "command": "python",
      "args": ["/path/to/habitflow-team/mcp_server/server.py"]
    }
  }
}
```
