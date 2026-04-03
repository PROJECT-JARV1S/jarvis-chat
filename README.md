# JARVIS Chat Agent

Intent recognition and tool routing for voice commands. Processes voice transcripts, recognizes user intents, and routes commands to MCP Server tools via HTTP/JSON-RPC.

## Features

- Intent recognition with confidence scoring
- LLM integration (OpenAI/Copilot SDK, optional)
- HTTP/JSON-RPC communication with MCP Server
- Conversation context management
- Async/await support
- Cross-platform (Windows, macOS, Linux)

## Installation

```bash
cd jarvis-chat
uv sync
```

## Quick Start

### Command Line

```bash
# Interactive mode
uv run main.py

# With MCP Server
uv run main.py --server

# Single command
uv run main.py --server "What's my CPU usage?"
```

### As a Library

```python
from chat_agent import ChatAgent, create_router

agent = ChatAgent()
router = create_router()

response = agent.process_transcript("Turn up the volume")
print(response.text)
```

## Configuration

Create `.env` file:

```env
OPENAI_API_KEY=sk-your-key-here          # Optional, for LLM mode
MCP_HOST=127.0.0.1
MCP_PORT=5050
LOG_LEVEL=INFO
```

## Supported Intents

| Intent | Example |
|--------|---------|
| system_info | "What's my CPU usage?" |
| volume_control | "Volume up" |
| music_control | "Play music" |
| network_toggle | "Turn off WiFi" |
| general_query | Other queries |

## Testing

```bash
uv run pytest tests/ -v
```

Tests: 15/15 passing

## Troubleshooting

**Module not found:**
```bash
cd jarvis-chat && uv sync
```

**MCP Server connection failed:**
Start the server first:
```bash
cd jarvis-skills && python server.py
```

**Intent not recognized:**
- System works without LLM (pattern matching fallback)
- Add OPENAI_API_KEY to enable LLM mode

## Requirements

- Python 3.13+
- uv package manager

## Development

```bash
uv add <package-name>        # Add dependency
uv run pytest                # Run tests
```

## License

MIT
