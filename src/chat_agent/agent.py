"""
Chat Agent

Main Chat Agent class that processes voice transcripts,
recognizes intents, and routes to appropriate skills via MCP.
"""

import json
import logging
from typing import AsyncGenerator, Optional
from uuid import uuid4

from openai import AsyncOpenAI, OpenAI

from .config import AgentConfig, load_config
from .intent import get_tool_name_for_intent, map_intent_params_to_tool, recognize_intent
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
from .tools import AVAILABLE_TOOLS, format_tool_result_for_display

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    JARVIS Chat Agent
    
    Processes voice transcripts, recognizes user intents,
    and routes commands to MCP Server tools.
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the Chat Agent.
        
        Args:
            config: Optional configuration. If not provided, loads from environment.
        """
        self.config = config or load_config()
        self.context = ConversationContext()
        
        if self.config.openai.is_configured():
            self.client = OpenAI(api_key=self.config.openai.api_key)
            self.async_client = AsyncOpenAI(api_key=self.config.openai.api_key)
        else:
            self.client = None
            self.async_client = None
            logger.warning("OpenAI API key not configured. Using intent-only mode.")
        
        self.context.add_message(MessageRole.SYSTEM, self.config.system_prompt)
        
        if self.config.debug:
            logging.basicConfig(level=logging.DEBUG)
    
    def process_transcript(self, transcript: str) -> AgentResponse:
        """
        Process a voice transcript and generate a response.
        
        This is the main entry point for voice commands.
        
        Args:
            transcript: The transcribed text from voice input
            
        Returns:
            AgentResponse with text response and any tool calls
        """
        if not transcript or not transcript.strip():
            return AgentResponse(
                text="I didn't catch that. Could you please repeat?",
                intent=Intent(type=IntentType.UNKNOWN, confidence=0.0, raw_text="")
            )
        
        if self.config.log_transcripts:
            logger.info(f"Processing transcript: {transcript}")
        
        intent = recognize_intent(transcript)
        logger.debug(f"Recognized intent: {intent.type} (confidence: {intent.confidence})")
        
        self.context.add_message(MessageRole.USER, transcript)
        
        if self.client is None:
            return self._handle_without_llm(transcript, intent)
        
        return self._handle_with_llm(transcript, intent)
    
    async def process_transcript_async(self, transcript: str) -> AgentResponse:
        """Async version of process_transcript."""
        if not transcript or not transcript.strip():
            return AgentResponse(
                text="I didn't catch that. Could you please repeat?",
                intent=Intent(type=IntentType.UNKNOWN, confidence=0.0, raw_text="")
            )
        
        if self.config.log_transcripts:
            logger.info(f"Processing transcript: {transcript}")
        
        intent = recognize_intent(transcript)
        self.context.add_message(MessageRole.USER, transcript)
        
        if self.async_client is None:
            return self._handle_without_llm(transcript, intent)
        
        return await self._handle_with_llm_async(transcript, intent)
    
    def _handle_without_llm(self, transcript: str, intent: Intent) -> AgentResponse:
        """Handle request using only intent recognition (no LLM)."""
        tool_name = get_tool_name_for_intent(intent)
        
        if tool_name:
            tool_params = map_intent_params_to_tool(intent)
            tool_call = ToolCall(
                id=str(uuid4()),
                name=tool_name,
                arguments=tool_params
            )
            
            response_text = self._generate_intent_response(intent)
            
            self.context.add_message(MessageRole.ASSISTANT, response_text)
            
            return AgentResponse(
                text=response_text,
                intent=intent,
                tool_calls=[tool_call]
            )
        
        response_text = "I'm not sure how to help with that. Could you try rephrasing?"
        self.context.add_message(MessageRole.ASSISTANT, response_text)
        
        return AgentResponse(
            text=response_text,
            intent=intent
        )
    
    def _handle_with_llm(self, transcript: str, intent: Intent) -> AgentResponse:
        """Handle request using the LLM."""
        try:
            response = self.client.chat.completions.create(
                model=self.config.openai.model,
                messages=self.context.get_openai_messages(),
                tools=AVAILABLE_TOOLS,
                tool_choice="auto",
                max_tokens=self.config.openai.max_tokens,
                temperature=self.config.openai.temperature,
            )
            
            message = response.choices[0].message
            
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments) if tc.function.arguments else {}
                    ))
            
            response_text = message.content or ""
            
            if not response_text and tool_calls:
                response_text = self._generate_tool_acknowledgment(tool_calls)
            
            self.context.add_message(MessageRole.ASSISTANT, response_text)
            
            return AgentResponse(
                text=response_text,
                intent=intent,
                tool_calls=tool_calls
            )
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return self._handle_without_llm(transcript, intent)
    
    async def _handle_with_llm_async(self, transcript: str, intent: Intent) -> AgentResponse:
        """Async version of _handle_with_llm."""
        try:
            response = await self.async_client.chat.completions.create(
                model=self.config.openai.model,
                messages=self.context.get_openai_messages(),
                tools=AVAILABLE_TOOLS,
                tool_choice="auto",
                max_tokens=self.config.openai.max_tokens,
                temperature=self.config.openai.temperature,
            )
            
            message = response.choices[0].message
            
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments) if tc.function.arguments else {}
                    ))
            
            response_text = message.content or ""
            
            if not response_text and tool_calls:
                response_text = self._generate_tool_acknowledgment(tool_calls)
            
            self.context.add_message(MessageRole.ASSISTANT, response_text)
            
            return AgentResponse(
                text=response_text,
                intent=intent,
                tool_calls=tool_calls
            )
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return self._handle_without_llm(transcript, intent)
    
    def add_tool_result(self, tool_call_id: str, result: ToolResult) -> str:
        """
        Add a tool result to the conversation and get the assistant's response.
        
        Args:
            tool_call_id: The ID of the tool call
            result: The result from executing the tool
            
        Returns:
            The assistant's response after seeing the tool result
        """
        result_content = json.dumps(result.result) if result.success else f"Error: {result.error}"
        
        self.context.add_message(
            MessageRole.TOOL,
            result_content,
            tool_call_id=tool_call_id,
            name=result.tool_call_id
        )
        
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.config.openai.model,
                    messages=self.context.get_openai_messages(),
                    max_tokens=self.config.openai.max_tokens,
                    temperature=self.config.openai.temperature,
                )
                
                response_text = response.choices[0].message.content or ""
                self.context.add_message(MessageRole.ASSISTANT, response_text)
                return response_text
                
            except Exception as e:
                logger.error(f"LLM error processing tool result: {e}")
        
        return format_tool_result_for_display(result.tool_call_id, result.result)
    
    def _generate_intent_response(self, intent: Intent) -> str:
        """Generate a response based on recognized intent."""
        responses = {
            IntentType.SYSTEM_INFO: "Let me check your system information...",
            IntentType.VOLUME_CONTROL: "Adjusting volume...",
            IntentType.MUSIC_CONTROL: "Controlling playback...",
            IntentType.NETWORK_TOGGLE: "Toggling network setting...",
            IntentType.GENERAL_QUERY: "Let me help you with that.",
        }
        return responses.get(intent.type, "Processing your request...")
    
    def _generate_tool_acknowledgment(self, tool_calls: list[ToolCall]) -> str:
        """Generate an acknowledgment for tool calls."""
        if len(tool_calls) == 1:
            tc = tool_calls[0]
            acknowledgments = {
                "get_system_info": "Checking your system information...",
                "control_volume": "Adjusting the volume...",
                "control_spotify": "Controlling Spotify...",
                "toggle_network": "Updating network settings...",
            }
            return acknowledgments.get(tc.name, f"Running {tc.name}...")
        
        return f"Running {len(tool_calls)} actions..."
    
    def clear_context(self) -> None:
        """Clear the conversation context while keeping the system prompt."""
        self.context.clear(keep_system=True)
    
    def get_conversation_history(self) -> list[ChatMessage]:
        """Get the current conversation history."""
        return self.context.messages.copy()


def create_agent(config: Optional[AgentConfig] = None) -> ChatAgent:
    """
    Factory function to create a Chat Agent.
    
    Args:
        config: Optional configuration
        
    Returns:
        Configured ChatAgent instance
    """
    return ChatAgent(config)
