"""
Tests for Intent Recognition
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from chat_agent import recognize_intent, IntentType


class TestIntentRecognition:
    """Test intent recognition from various voice commands."""
    
    def test_system_info_intents(self):
        """Test system info related commands."""
        commands = [
            "What's my CPU usage?",
            "How much RAM am I using?",
            "system info",
            "Show me storage space",
            "What's the CPU status?",
        ]
        
        for cmd in commands:
            intent = recognize_intent(cmd)
            assert intent.type == IntentType.SYSTEM_INFO, f"Failed for: {cmd}"
            assert intent.confidence >= 0.8
    
    def test_volume_control_intents(self):
        """Test volume control commands."""
        test_cases = [
            ("volume up", "up"),
            ("turn down the volume", "down"),
            ("mute", "mute"),
            ("unmute the sound", "unmute"),
            ("make it louder", "up"),
            ("set volume to 50", None),
        ]
        
        for cmd, expected_direction in test_cases:
            intent = recognize_intent(cmd)
            assert intent.type == IntentType.VOLUME_CONTROL, f"Failed for: {cmd}"
            
            if expected_direction:
                assert intent.parameters.get("direction") == expected_direction
    
    def test_music_control_intents(self):
        """Test music/Spotify control commands."""
        test_cases = [
            ("play music", "play"),
            ("pause the music", "pause"),
            ("next track", "next"),
            ("previous song", "previous"),
            ("what's playing?", None),
            ("spotify play", "play"),
        ]
        
        for cmd, expected_action in test_cases:
            intent = recognize_intent(cmd)
            assert intent.type == IntentType.MUSIC_CONTROL, f"Failed for: {cmd}"
            
            if expected_action:
                assert intent.parameters.get("action") == expected_action
    
    def test_network_toggle_intents(self):
        """Test network toggle commands."""
        test_cases = [
            ("turn off wifi", "wifi", "off"),
            ("enable bluetooth", "bluetooth", "on"),
            ("wifi off", "wifi", "off"),
            ("disable wifi", "wifi", "off"),
        ]
        
        for cmd, expected_device, expected_state in test_cases:
            intent = recognize_intent(cmd)
            assert intent.type == IntentType.NETWORK_TOGGLE, f"Failed for: {cmd}"
            assert intent.parameters.get("device") == expected_device, f"Wrong device for: {cmd}"
            
            if expected_state:
                assert intent.parameters.get("state") == expected_state, f"Wrong state for: {cmd}"
    
    def test_general_query_fallback(self):
        """Test that unrecognized queries fall back to general."""
        commands = [
            "What's the weather like?",
            "Tell me a joke",
            "Hello JARVIS",
        ]
        
        for cmd in commands:
            intent = recognize_intent(cmd)
            assert intent.type == IntentType.GENERAL_QUERY
    
    def test_empty_input(self):
        """Test handling of empty input."""
        intent = recognize_intent("")
        assert intent.type == IntentType.UNKNOWN
        assert intent.confidence == 0.0
    
    def test_confidence_scores(self):
        """Test that confidence scores are in valid range."""
        commands = [
            "volume up",
            "what's the weather",
            "play music",
            "",
        ]
        
        for cmd in commands:
            intent = recognize_intent(cmd)
            assert 0.0 <= intent.confidence <= 1.0
