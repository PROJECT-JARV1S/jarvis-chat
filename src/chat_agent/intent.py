"""
Intent Recognition

Recognize user intents from transcribed text.
Maps voice commands to actionable intents.
"""

import re
from typing import Optional

from .models import Intent, IntentType


INTENT_PATTERNS: dict[IntentType, list[str]] = {
    IntentType.SYSTEM_INFO: [
        r"^system\s*(info|information|status)$",
        r"(cpu|processor)\s*(usage|load|status)?",
        r"(ram|memory)\s*(usage|status)?",
        r"(storage|disk|drive)\s*(space|usage|status)?",
        r"(network|internet)\s*(status|connection)$",
        r"how\s*(much|many)\s*(memory|ram|storage|space)",
        r"what('s|s| is)\s*(the|my)?\s*(cpu|memory|ram|storage)",
    ],
    IntentType.VOLUME_CONTROL: [
        r"(volume|sound)\s*(up|down|louder|quieter|higher|lower)",
        r"(turn|set)\s*(up|down)?\s*(the)?\s*volume",
        r"^(mute|unmute)\s*(the)?\s*(sound|volume|audio)?$",
        r"(increase|decrease|raise|lower)\s*(the)?\s*volume",
        r"volume\s*(to|at)?\s*(\d+)",
        r"(set|change)\s*(the)?\s*volume\s*(to|at)?\s*(\d+)",
        r"make\s*it\s*(louder|quieter)",
    ],
    IntentType.MUSIC_CONTROL: [
        r"(play|pause|stop)\s*(music|song|track|spotify)?",
        r"(next|previous|skip)\s*(track|song)?",
        r"(spotify|music)\s*(play|pause|next|previous|skip)",
        r"what('s|s| is)\s*(playing|this song)",
        r"current\s*(track|song)",
        r"resume\s*(music|playback|spotify)?",
    ],
    IntentType.NETWORK_TOGGLE: [
        r"(turn|toggle|switch)\s*(on|off)\s*(the)?\s*(wifi|wi-fi|bluetooth|airplane)",
        r"(enable|disable)\s*(the)?\s*(wifi|wi-fi|bluetooth|airplane)",
        r"(wifi|wi-fi|bluetooth)\s*(on|off)",
        r"(connect|disconnect)\s*(to)?\s*(wifi|wi-fi|bluetooth)?",
    ],
}

PARAMETER_EXTRACTORS = {
    IntentType.VOLUME_CONTROL: {
        "direction": [
            (r"\bunmute\b", "unmute"),
            (r"\bmute\b", "mute"),
            (r"(up|louder|higher|increase|raise)", "up"),
            (r"(down|quieter|lower|decrease)", "down"),
        ],
        "level": r"(\d+)\s*(%|percent)?",
    },
    IntentType.MUSIC_CONTROL: {
        "action": [
            (r"\b(play|resume)\b", "play"),
            (r"\b(pause|stop)\b", "pause"),
            (r"\b(next|skip)\b", "next"),
            (r"\bprevious\b", "previous"),
        ],
    },
    IntentType.NETWORK_TOGGLE: {
        "device": [
            (r"\b(wifi|wi-fi)\b", "wifi"),
            (r"\bbluetooth\b", "bluetooth"),
            (r"\bairplane\b", "airplane"),
        ],
        "state": [
            (r"\b(on|enable|connect)\b", "on"),
            (r"\b(off|disable|disconnect)\b", "off"),
        ],
    },
}


def recognize_intent(text: str) -> Intent:
    """
    Recognize the user's intent from transcribed text.
    
    Args:
        text: The transcribed user input
        
    Returns:
        Intent object with type, confidence, and parameters
    """
    text_lower = text.lower().strip()
    
    if not text_lower:
        return Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            raw_text=text
        )
    
    best_match: Optional[tuple[IntentType, float]] = None
    
    for intent_type, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                confidence = 0.85
                
                if len(text_lower.split()) <= 5:
                    confidence += 0.1
                    
                if best_match is None or confidence > best_match[1]:
                    best_match = (intent_type, min(confidence, 1.0))
                break
    
    if best_match is None:
        return Intent(
            type=IntentType.GENERAL_QUERY,
            confidence=0.6,
            raw_text=text
        )
    
    intent_type, confidence = best_match
    parameters = extract_parameters(text_lower, intent_type)
    
    return Intent(
        type=intent_type,
        confidence=confidence,
        parameters=parameters,
        raw_text=text
    )


def extract_parameters(text: str, intent_type: IntentType) -> dict:
    """Extract parameters from text based on intent type."""
    params = {}
    
    extractors = PARAMETER_EXTRACTORS.get(intent_type, {})
    
    for param_name, extractor in extractors.items():
        if isinstance(extractor, list):
            for pattern, value in extractor:
                if re.search(pattern, text):
                    params[param_name] = value
                    break
        elif isinstance(extractor, str):
            match = re.search(extractor, text)
            if match:
                params[param_name] = match.group(1)
    
    return params


def get_tool_name_for_intent(intent: Intent) -> Optional[str]:
    """Map an intent to its corresponding MCP tool name."""
    tool_mapping = {
        IntentType.SYSTEM_INFO: "get_system_info",
        IntentType.VOLUME_CONTROL: "control_volume",
        IntentType.MUSIC_CONTROL: "control_spotify",
        IntentType.NETWORK_TOGGLE: "toggle_network",
    }
    return tool_mapping.get(intent.type)


def map_intent_params_to_tool(intent: Intent) -> dict:
    """
    Map intent parameters to tool-expected parameters.
    
    Handles differences between intent extraction naming and tool API naming.
    """
    params = dict(intent.parameters)
    
    if intent.type == IntentType.VOLUME_CONTROL:
        if "direction" in params:
            params["action"] = params.pop("direction")
    
    elif intent.type == IntentType.NETWORK_TOGGLE:
        if "device" in params:
            params["interface"] = params.pop("device")
        if "state" in params:
            params["enable"] = params.pop("state") == "on"
    
    return params
