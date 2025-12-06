#!/usr/bin/env python3
"""
Onboarding Flow - Question Sequence for User Profile

Handles the onboarding state machine:
1. Greeting
2. Ask name
3. Ask school
4. Ask age
5. Ask hobbies
6. Complete
"""

from typing import Dict, Optional

# Question sequence
ONBOARDING_STATES = {
    "start": "greeting",
    "name": "name",
    "school": "school",
    "age": "age",
    "hobbies": "hobbies",
    "complete": "complete"
}

def get_onboarding_greeting() -> str:
    """Get the initial greeting message."""
    return "Hi! I'm your AI friend. 👋\n\nI'd love to get to know you better! Let me ask you a few questions."

def get_question(state: str) -> Optional[str]:
    """Get the question for the current onboarding state."""
    questions = {
        "name": "What's your name?",
        "school": "What school do you go to?",
        "age": "What's your age?",
        "hobbies": "What are your hobbies? (You can list multiple)"
    }
    return questions.get(state)

def get_next_state(current_state: str) -> Optional[str]:
    """Get the next state in the onboarding flow."""
    flow = {
        "greeting": "name",
        "name": "school",
        "school": "age",
        "age": "hobbies",
        "hobbies": "complete"
    }
    return flow.get(current_state)

def validate_answer(state: str, answer: str) -> tuple[bool, Optional[str]]:
    """
    Validate the answer for the current state.
    Returns (is_valid, error_message)
    """
    answer = answer.strip()
    
    if not answer:
        return False, "Please provide an answer."
    
    if state == "age":
        try:
            age = int(answer)
            if age < 1 or age > 150:
                return False, "Please enter a valid age (1-150)."
        except ValueError:
            return False, "Please enter your age as a number."
    
    if state == "name":
        if len(answer) < 2:
            return False, "Please enter a valid name (at least 2 characters)."
        if len(answer) > 100:
            return False, "Name is too long. Please keep it under 100 characters."
    
    if state == "school":
        if len(answer) < 2:
            return False, "Please enter a valid school name."
        if len(answer) > 200:
            return False, "School name is too long. Please keep it under 200 characters."
    
    if state == "hobbies":
        if len(answer) < 3:
            return False, "Please tell me at least one hobby."
        if len(answer) > 500:
            return False, "That's a lot of hobbies! Please keep it under 500 characters."
    
    return True, None

def get_completion_message(profile: Dict) -> str:
    """Get the welcome message after onboarding is complete."""
    name = profile.get("name", "there")
    return f"Nice to meet you, {name}! 🎉\n\nI've saved your info. Let's chat!"

def format_profile_summary(profile: Dict) -> str:
    """Format profile data for display in /reset command."""
    lines = ["📋 Your saved profile:"]
    
    if profile.get("name"):
        lines.append(f"   Name: {profile['name']}")
    if profile.get("school"):
        lines.append(f"   School: {profile['school']}")
    if profile.get("age"):
        lines.append(f"   Age: {profile['age']}")
    if profile.get("hobbies"):
        lines.append(f"   Hobbies: {profile['hobbies']}")
    
    if len(lines) == 1:  # Only header, no data
        lines.append("   (No profile data saved yet)")
    
    return "\n".join(lines)

