"""
Utility functions for webhook receiver
"""
from typing import Dict
import re


def format_single_requirement(requirement: Dict) -> str:
    """
    Format single requirement details for email content
    
    Args:
        requirement: Requirement dictionary with title, description, match_score
        
    Returns:
        Formatted string with requirement details
    """
    description = requirement.get('requirement_description', 'N/A')
    match_score = requirement.get('match_score', 0.0)
    match_percentage = f"{match_score:.1f}%" if match_score else "N/A"
    
    formatted = f"""
    Job Requirement:
    - Title: {requirement.get('requirement_title', 'N/A')}
    - Match Score: {match_percentage}
    - Description: {description}
    """
    
    return formatted.strip()


def extract_first_name(full_name: str) -> str:
    """
    Extract first name from full name
    
    Args:
        full_name: Full name of candidate
        
    Returns:
        First name
    """
    if not full_name:
        return "Candidate"
    
    parts = full_name.strip().split()
    return parts[0] if parts else "Candidate"


def format_phone_number(phone: str, default_country_code: str = "+91") -> str:
    """
    Format phone number to ensure it has country code
    
    Args:
        phone: Phone number (may or may not have country code)
        default_country_code: Default country code to add (default: +91 for India)
        
    Returns:
        Formatted phone number with country code
    """
    if not phone:
        return None
    
    # Remove all non-digit characters except +
    phone = re.sub(r'[^\d+]', '', phone)
    
    # If already has +, return as is
    if phone.startswith('+'):
        return phone
    
    # Add default country code
    return f"{default_country_code}{phone}"


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False
    
    # Must start with + and have at least 10 digits
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, phone))


def validate_webhook_payload(payload: dict) -> bool:
    """
    Validate webhook payload structure
    
    Args:
        payload: The webhook payload dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['type', 'table', 'record']
    
    for field in required_fields:
        if field not in payload:
            print(f"❌ Missing required field: {field}")
            return False
    
    record = payload.get('record', {})
    if 'candidate_id' not in record:
        print("❌ Missing candidate_id in record")
        return False
    
    if 'requirement_id' not in record:
        print("❌ Missing requirement_id in record")
        return False
    
    return True