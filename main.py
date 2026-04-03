"""
JARVIS Chat Agent CLI

Simple command-line interface for testing the Chat Agent.

Usage:
    uv run main.py                  # Interactive mode (mock handlers)
    uv run main.py --server         # Interactive mode (MCP server)
    uv run main.py "command"        # Single command (mock handlers)
    uv run main.py --server "cmd"   # Single command (MCP server)
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from chat_agent import create_agent, create_router, IntentType
from chat_agent.config import MCPConfig


def main():
    """Main entry point for the Chat Agent CLI."""
    parser = argparse.ArgumentParser(description="JARVIS Chat Agent CLI")
    parser.add_argument("--server", "-s", action="store_true", 
                        help="Use MCP server (default: mock handlers)")
    parser.add_argument("--url", default="http://127.0.0.1:5050",
                        help="MCP server URL (default: http://127.0.0.1:5050)")
    parser.add_argument("command", nargs="*", help="Command to execute")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("JARVIS Chat Agent v0.1.0")
    print("=" * 50)
    
    agent = create_agent()
    
    if args.server:
        config = MCPConfig(url=args.url)
        router = create_router(config)
        print(f"Using MCP Server at {args.url}")
    else:
        router = create_router()
        router.set_direct_mode(True)
        register_mock_handlers(router)
        print("Using mock handlers (use --server for real MCP)")
    
    if args.command:
        transcript = " ".join(args.command)
        process_transcript(agent, router, transcript)
        return
    
    print("\nInteractive mode. Type 'quit' or 'exit' to stop.")
    print("Type 'clear' to clear conversation history.\n")
    
    while True:
        try:
            transcript = input("You: ").strip()
            
            if not transcript:
                continue
                
            if transcript.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
                
            if transcript.lower() == "clear":
                agent.clear_context()
                print("[Conversation cleared]\n")
                continue
            
            process_transcript(agent, router, transcript)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            break


def process_transcript(agent, router, transcript: str):
    """Process a single transcript and print results."""
    response = agent.process_transcript(transcript)
    
    print(f"\nJARVIS: {response.text}")
    
    if response.intent:
        print(f"  [Intent: {response.intent.type.value}, Confidence: {response.intent.confidence:.2f}]")
    
    if response.tool_calls:
        print(f"  [Tool calls: {len(response.tool_calls)}]")
        
        for tool_call in response.tool_calls:
            print(f"    - {tool_call.name}({tool_call.arguments})")
            
            result = router.execute_tool_sync(tool_call)
            
            if result.success:
                print(f"    Result: {result.result}")
                agent.add_tool_result(tool_call.id, result)
                friendly = format_result(tool_call.name, result.result)
                print(f"\nJARVIS: {friendly}")
            else:
                print(f"    Error: {result.error}")
    
    print()


def format_result(tool_name: str, result: dict) -> str:
    """Format tool result into human-friendly response."""
    if tool_name == "get_system_info":
        cpu = result.get("cpu", "N/A")
        ram = result.get("ram", {})
        ram_pct = ram.get("percent", "N/A")
        ram_used = ram.get("used_gb", "N/A")
        ram_total = ram.get("total_gb", "N/A")
        network = result.get("network", {})
        connected = "connected" if network.get("connected") else "disconnected"
        interface = network.get("interface", "Unknown")
        
        return (
            f"Your CPU usage is {cpu}%. "
            f"RAM: {ram_used}GB / {ram_total}GB ({ram_pct}% used). "
            f"Network: {connected} via {interface}."
        )
    
    elif tool_name == "control_volume":
        if "level" in result:
            return f"Volume set to {result['level']}%."
        elif "muted" in result:
            return "Muted." if result["muted"] else "Unmuted."
        return "Volume adjusted."
    
    elif tool_name == "control_spotify":
        action = result.get("action", "")
        if action == "play":
            return "Playing music."
        elif action == "pause":
            return "Music paused."
        elif action == "next":
            return "Skipping to next track."
        elif action == "previous":
            return "Going to previous track."
        elif "track" in result:
            track = result["track"]
            return f"Now playing: {track.get('name', 'Unknown')} by {track.get('artist', 'Unknown')}."
        return "Spotify command executed."
    
    elif tool_name == "toggle_network":
        interface = result.get("interface", "Network")
        enabled = result.get("enabled", False)
        status = "enabled" if enabled else "disabled"
        return f"{interface} {status}."
    
    return str(result)


def register_mock_handlers(router):
    """Register mock handlers for testing without MCP Server."""
    
    def get_system_info(include=None):
        return {
            "cpu": 45.2,
            "ram": {
                "total_gb": 16.0,
                "used_gb": 8.5,
                "percent": 53.1
            },
            "storage": [
                {"mount": "C:", "total_gb": 500, "free_gb": 234.5},
                {"mount": "D:", "total_gb": 1000, "free_gb": 567.8}
            ],
            "network": {
                "connected": True,
                "interface": "Ethernet"
            }
        }
    
    def control_volume(action=None, level=None, step=10, direction=None):
        if direction:
            action = direction
        
        if action == "get":
            return {"level": 65, "muted": False}
        elif action == "mute":
            return {"muted": True}
        elif action == "unmute":
            return {"muted": False}
        elif action == "set" and level is not None:
            return {"level": level}
        elif action == "up":
            return {"level": min(100, 65 + step)}
        elif action == "down":
            return {"level": max(0, 65 - step)}
        return {"error": "Unknown action"}
    
    def control_spotify(action, uri=None):
        if action == "current":
            return {
                "track": {
                    "name": "Bohemian Rhapsody",
                    "artist": "Queen",
                    "album": "A Night at the Opera"
                },
                "playing": True
            }
        elif action in ("play", "pause", "next", "previous", "toggle"):
            return {"action": action, "success": True}
        return {"error": "Unknown action"}
    
    def toggle_network(device, state=None):
        return {
            "device": device,
            "state": state or "toggled",
            "success": True
        }
    
    router.register_handler("get_system_info", get_system_info)
    router.register_handler("control_volume", control_volume)
    router.register_handler("control_spotify", control_spotify)
    router.register_handler("toggle_network", toggle_network)


if __name__ == "__main__":
    main()

