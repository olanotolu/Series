#!/usr/bin/env python3
"""
Dead Letter Queue (DLQ) Handler

Stores failed messages that cannot be processed for manual review and reprocessing.
"""

import json
import os
from datetime import datetime
from typing import Optional
import traceback


DLQ_DIR = "dlq"


def ensure_dlq_directory():
    """Ensure the DLQ directory exists with date-based subdirectories."""
    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = os.path.join(DLQ_DIR, today)
    os.makedirs(date_dir, exist_ok=True)
    return date_dir


def send_to_dlq(event: dict, error: Exception, error_type: str, partition: int = None, offset: int = None, topic: str = None):
    """
    Send a failed message to the Dead Letter Queue with production-grade structure.
    
    Args:
        event: The original Kafka event/message
        error: The exception that occurred
        error_type: Classification ('recoverable' or 'non_recoverable')
        partition: Kafka partition number (optional)
        offset: Kafka offset number (optional)
        topic: Kafka topic name (optional)
    
    Returns:
        str: Path to the DLQ file
    """
    date_dir = ensure_dlq_directory()
    
    # Extract event_id for filename
    event_id = event.get('event_id', 'unknown')
    if not event_id or event_id == 'unknown':
        # Fallback to offset-based ID if no event_id
        event_id = f"offset_{partition}_{offset}" if partition is not None and offset is not None else f"no_id_{int(datetime.now().timestamp())}"
    
    # Create filename with event_id and offset
    safe_event_id = str(event_id).replace('/', '_').replace('\\', '_')[:50]  # Sanitize
    offset_str = f"_{offset}" if offset is not None else ""
    filename = f"{safe_event_id}{offset_str}.json"
    filepath = os.path.join(date_dir, filename)
    
    # Prepare production-grade DLQ entry
    dlq_entry = {
        "event": event,
        "kafka": {
            "partition": partition,
            "offset": offset,
            "topic": topic
        },
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "stack": traceback.format_exc()
        },
        "dlq_metadata": {
            "timestamp": datetime.now().isoformat(),
            "error_classification": error_type,
            "dlq_version": "1.0"
        }
    }
    
    # Write to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dlq_entry, f, indent=2, ensure_ascii=False)
        print(f"   📋 DLQ: Saved failed message to {filepath}")
        return filepath
    except Exception as e:
        print(f"   ❌ DLQ: Failed to write DLQ entry: {e}")
        return None


def is_recoverable_error(error: Exception) -> bool:
    """
    Classify whether an error is recoverable (should retry) or non-recoverable (DLQ).
    
    Args:
        error: The exception to classify
    
    Returns:
        bool: True if recoverable, False if non-recoverable
    """
    error_type = type(error).__name__
    error_str = str(error).lower()
    
    # Recoverable errors (transient, should retry)
    recoverable_patterns = [
        'timeout',
        'connection',
        'network',
        'temporary',
        'rate limit',
        '503',  # Service Unavailable
        '502',  # Bad Gateway
        '504',  # Gateway Timeout
        '500',  # Internal Server Error (might be transient)
    ]
    
    # Check if error message contains recoverable patterns
    for pattern in recoverable_patterns:
        if pattern in error_str:
            return True
    
    # Check specific exception types
    if error_type in [
        'Timeout',
        'ConnectionError',
        'ConnectTimeout',
        'ReadTimeout',
        'HTTPError'  # Only if it's a 5xx error
    ]:
        # For HTTPError, check if it's a 5xx (server error)
        if error_type == 'HTTPError' and hasattr(error, 'response'):
            status_code = getattr(error.response, 'status_code', None)
            if status_code and 500 <= status_code < 600:
                return True
        elif error_type in ['Timeout', 'ConnectionError', 'ConnectTimeout', 'ReadTimeout']:
            return True
    
    # Non-recoverable errors (permanent, send to DLQ)
    non_recoverable_patterns = [
        'invalid',
        'missing',
        'required',
        'not found',
        'unauthorized',
        'forbidden',
        '400',  # Bad Request
        '401',  # Unauthorized
        '403',  # Forbidden
        '404',  # Not Found
        '422',  # Unprocessable Entity
    ]
    
    for pattern in non_recoverable_patterns:
        if pattern in error_str:
            return False
    
    # Check for specific non-recoverable exception types
    if error_type in [
        'ValueError',
        'KeyError',
        'AttributeError',
        'TypeError',
        'JSONDecodeError'
    ]:
        return False
    
    # Default: if we can't determine, treat as non-recoverable (safer)
    return False


def classify_error(error: Exception) -> str:
    """
    Classify an error as 'recoverable' or 'non_recoverable'.
    
    Args:
        error: The exception to classify
    
    Returns:
        str: 'recoverable' or 'non_recoverable'
    """
    if is_recoverable_error(error):
        return 'recoverable'
    else:
        return 'non_recoverable'

