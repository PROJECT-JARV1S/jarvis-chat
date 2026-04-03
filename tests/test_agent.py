"""
Tests for Chat Agent
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from chat_agent import (
    ChatAgent,
    create_agent,
    AgentConfig,
    OpenAIConfig,
    IntentType,
)


class TestChatAgent:
    """Test the Chat Agent."""
    
    def test_create_agent(self):
        """Test agent creation."""
        agent = create_agent()
        assert agent is not None
        assert isinstance(agent, ChatAgent)
    
    def test_create_agent_with_config(self):
        """Test agent creation with custom config."""
        config = AgentConfig(
            openai=OpenAIConfig(api_key="", model="gpt-4o"),
            debug=True
        )
        agent = create_agent(config)
        assert agent.config.debug == True
    
    def test_process_transcript_empty(self):
        """Test processing empty transcript."""
        agent = create_agent()
        response = agent.process_transcript("")
        
        assert response.text
        assert response.intent.type == IntentType.UNKNOWN
    
    def test_process_transcript_system_info(self):
        """Test processing system info request."""
        agent = create_agent()
        response = agent.process_transcript("What's my CPU usage?")
        
        assert response.intent.type == IntentType.SYSTEM_INFO
        assert len(response.tool_calls) > 0
        assert response.tool_calls[0].name == "get_system_info"
    
    def test_process_transcript_volume(self):
        """Test processing volume control request."""
        agent = create_agent()
        response = agent.process_transcript("Volume up")
        
        assert response.intent.type == IntentType.VOLUME_CONTROL
        assert len(response.tool_calls) > 0
        assert response.tool_calls[0].name == "control_volume"
    
    def test_conversation_context(self):
        """Test that conversation context is maintained."""
        agent = create_agent()
        
        agent.process_transcript("Hello")
        agent.process_transcript("What time is it?")
        
        history = agent.get_conversation_history()
        
        assert len(history) >= 3
        assert any("Hello" in m.content for m in history)
    
    def test_clear_context(self):
        """Test clearing conversation context."""
        agent = create_agent()
        
        agent.process_transcript("Hello")
        agent.process_transcript("What time is it?")
        
        agent.clear_context()
        
        history = agent.get_conversation_history()
        
        assert len(history) == 1
        assert history[0].role.value == "system"
    
    def test_response_has_text(self):
        """Test that responses always have text."""
        agent = create_agent()
        
        commands = [
            "Turn up the volume",
            "What's playing?",
            "Check system status",
            "Hello JARVIS",
        ]
        
        for cmd in commands:
            response = agent.process_transcript(cmd)
            assert response.text, f"No text for: {cmd}"
