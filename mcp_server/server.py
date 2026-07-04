#!/usr/bin/env python3
"""FastMCP server — exposes HabitFlow Kanban as MCP tools."""

from mcp.server.fastmcp import FastMCP

from mcp_server.store import (
    activity_log,
    board_get,
    card_assign,
    card_comment,
    card_create,
    card_move,
    get_activity,
    init_db,
)

mcp = FastMCP("habitflow-kanban")
init_db()


@mcp.tool()
def board_get_tool() -> dict:
    """Return current Kanban board with all columns and cards."""
    return board_get()


@mcp.tool()
def card_create_tool(actor: str, title: str, labels: list, description: str = "", points: int = 1) -> dict:
    """Create a card in backlog. Coordinator only."""
    if actor != "coordinator":
        raise ValueError("Only coordinator can create cards")
    return card_create(actor, title, labels, description, points)


@mcp.tool()
def card_assign_tool(actor: str, card_id: str, assignee: str) -> dict:
    """Assign card to specialist. Coordinator only."""
    if actor != "coordinator":
        raise ValueError("Only coordinator can assign cards")
    return card_assign(actor, card_id, assignee)


@mcp.tool()
def card_move_tool(actor: str, card_id: str, to_column: str) -> dict:
    """Move card to another column."""
    return card_move(actor, card_id, to_column)


@mcp.tool()
def card_comment_tool(actor: str, card_id: str, text: str) -> dict:
    """Append comment to a card."""
    return card_comment(actor, card_id, text)


@mcp.tool()
def activity_log_tool(actor: str, action: str, card_id: str, payload: dict) -> dict:
    """Log agent activity for audit trail."""
    activity_log(actor, action, card_id, payload)
    return {"logged": True}


@mcp.tool()
def activity_get_tool(limit: int = 50) -> list:
    """Get recent activity log entries."""
    return get_activity(limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")
