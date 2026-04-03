"""
Tool Definitions

OpenAI-compatible tool definitions for MCP Server tools.
These definitions tell the LLM what tools are available and how to call them.
"""

from typing import Any

AVAILABLE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get system information including CPU usage, RAM usage, storage space, and network status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["cpu", "ram", "storage", "network", "all"]
                        },
                        "description": "What information to include. Defaults to 'all'.",
                        "default": ["all"]
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_volume",
            "description": "Control system audio volume. Can set volume level, mute/unmute, or adjust up/down.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["set", "up", "down", "mute", "unmute", "get"],
                        "description": "The volume action to perform."
                    },
                    "level": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Volume level (0-100). Only used with 'set' action."
                    },
                    "step": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Amount to adjust for up/down actions."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_spotify",
            "description": "Control Spotify music playback. Play, pause, skip tracks, get current track info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play", "pause", "next", "previous", "current", "toggle"],
                        "description": "The playback action to perform."
                    },
                    "uri": {
                        "type": "string",
                        "description": "Optional Spotify URI to play (track, album, or playlist)."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_network",
            "description": "Toggle WiFi, Bluetooth, or Airplane mode on/off.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "enum": ["wifi", "bluetooth", "airplane"],
                        "description": "Which network device to toggle."
                    },
                    "state": {
                        "type": "string",
                        "enum": ["on", "off", "toggle"],
                        "description": "Desired state. 'toggle' switches current state."
                    }
                },
                "required": ["device"]
            }
        }
    }
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """Get all available tool definitions for OpenAI API."""
    return AVAILABLE_TOOLS


def get_tool_by_name(name: str) -> dict[str, Any] | None:
    """Get a specific tool definition by name."""
    for tool in AVAILABLE_TOOLS:
        if tool["function"]["name"] == name:
            return tool
    return None


def format_tool_result_for_display(tool_name: str, result: Any) -> str:
    """Format a tool result for user-friendly display."""
    if tool_name == "get_system_info" and isinstance(result, dict):
        lines = ["System Information:"]
        if "cpu" in result:
            lines.append(f"  CPU: {result['cpu']}% usage")
        if "ram" in result:
            ram = result["ram"]
            lines.append(f"  RAM: {ram.get('used_gb', 'N/A')} GB / {ram.get('total_gb', 'N/A')} GB ({ram.get('percent', 'N/A')}%)")
        if "storage" in result:
            for drive in result.get("storage", []):
                lines.append(f"  {drive.get('mount', 'Drive')}: {drive.get('free_gb', 'N/A')} GB free")
        return "\n".join(lines)
    
    if tool_name == "control_volume" and isinstance(result, dict):
        if "level" in result:
            return f"Volume set to {result['level']}%"
        if "muted" in result:
            return "Audio muted" if result["muted"] else "Audio unmuted"
        return str(result)
    
    if tool_name == "control_spotify" and isinstance(result, dict):
        if "track" in result:
            track = result["track"]
            return f"Now playing: {track.get('name', 'Unknown')} by {track.get('artist', 'Unknown')}"
        if "action" in result:
            return f"Spotify: {result['action']}"
        return str(result)
    
    return str(result)
