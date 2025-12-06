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

def extract_value(state: str, answer: str) -> str:
    """
    Extract the actual value from common phrases.
    Examples:
    - "my name is siddharth" -> "siddharth"
    - "I'm 30" -> "30"
    - "i go to abc university" -> "abc university"
    """
    answer = answer.strip().lower()
    
    if state == "name":
        # Patterns: "my name is X", "I'm X", "I am X", "name is X", "call me X"
        patterns = [
            r"my name is (.+)",
            r"i'?m (.+)",
            r"i am (.+)",
            r"name is (.+)",
            r"call me (.+)",
            r"name's (.+)",
            r"^(.+)$"  # Fallback: just return the whole thing
        ]
        import re
        for pattern in patterns:
            match = re.search(pattern, answer, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # Remove trailing punctuation
                extracted = extracted.rstrip('.,!?')
                if len(extracted) >= 2:
                    return extracted.capitalize() if extracted.islower() else extracted
        return answer.capitalize() if answer.islower() else answer
    
    elif state == "age":
        # Patterns: "I'm 30", "I am 30", "30 years old", "age is 30", just "30"
        import re
        # Try to find a number
        match = re.search(r'\d+', answer)
        if match:
            return match.group(0)
        return answer
    
    elif state == "school":
        # Patterns: "i go to X", "I attend X", "I study at X", "school is X", just "X"
        import re
        patterns = [
            r"i go to (.+)",
            r"i attend (.+)",
            r"i study at (.+)",
            r"school is (.+)",
            r"^(.+)$"
        ]
        for pattern in patterns:
            match = re.search(pattern, answer, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                extracted = extracted.rstrip('.,!?')
                if len(extracted) >= 2:
                    return extracted
        return answer
    
    elif state == "hobbies":
        # Just return as-is, but clean up
        answer = answer.rstrip('.,!?')
        return answer
    
    return answer


def validate_answer(state: str, answer: str) -> tuple[bool, Optional[str]]:
    """
    Validate the answer for the current state.
    Returns (is_valid, error_message)
    """
    answer = answer.strip()
    
    if not answer:
        return False, "Please provide an answer."
    
    if state == "age":
        # Extract number first
        import re
        age_match = re.search(r'\d+', answer)
        if not age_match:
            return False, "Please enter your age as a number."
        try:
            age = int(age_match.group(0))
            if age < 1 or age > 150:
                return False, "Please enter a valid age (1-150)."
        except ValueError:
            return False, "Please enter your age as a number."
    
    if state == "name":
        # Extract name first
        extracted = extract_value(state, answer)
        if len(extracted) < 2:
            return False, "Please enter a valid name (at least 2 characters)."
        if len(extracted) > 100:
            return False, "Name is too long. Please keep it under 100 characters."
    
    if state == "school":
        # Extract school first
        extracted = extract_value(state, answer)
        if len(extracted) < 2:
            return False, "Please enter a valid school name."
        if len(extracted) > 200:
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

