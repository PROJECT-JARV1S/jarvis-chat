"""
JARVIS Chat Agent Module

This module provides the Chat Agent for processing voice transcripts,
recognizing intents, and routing commands to MCP Server tools.

Usage:
    from chat_agent import ChatAgent, create_agent
    
    # Create agent with default config
    agent = create_agent()
    
    # Process a voice transcript
    response = agent.process_transcript("What's my CPU usage?")
    print(response.text)
    
    # Handle tool calls if any
    for tool_call in response.tool_calls:
        result = router.execute_tool_sync(tool_call)
        agent.add_tool_result(tool_call.id, result)
"""

from .agent import ChatAgent, create_agent
from .config import AgentConfig, MCPConfig, OpenAIConfig, load_config
from .intent import recognize_intent, get_tool_name_for_intent
from .models import (
    AgentResponse,
    ChatMessage,
    ConversationContext,
    Intent,
    IntentType,
    MessageRole,
    ToolCall,
    ToolResult,
)
from .router import MCPRouter, create_router
from .tools import AVAILABLE_TOOLS, get_tool_definitions, get_tool_by_name

__version__ = "0.1.0"

__all__ = [
    # Main classes
    "ChatAgent",
    "MCPRouter",
    
    # Factory functions
    "create_agent",
    "create_router",
    "load_config",
    
    # Config classes
    "AgentConfig",
    "MCPConfig",
    "OpenAIConfig",
    
    # Models
    "AgentResponse",
    "ChatMessage",
    "ConversationContext",
    "Intent",
    "IntentType",
    "MessageRole",
    "ToolCall",
    "ToolResult",
    
    # Intent recognition
    "recognize_intent",
    "get_tool_name_for_intent",
    
    # Tool definitions
    "AVAILABLE_TOOLS",
    "get_tool_definitions",
    "get_tool_by_name",
]
