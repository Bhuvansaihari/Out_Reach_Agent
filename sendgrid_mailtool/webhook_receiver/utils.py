"""
Utility functions for webhook receiver
Updated for production schema: November 2025 version
"""
from typing import Dict
import re


def format_single_requirement(requirement: Dict) -> str:
    """
    Format single requirement details for email content
    
    Args:
        requirement: Requirement dictionary with details
        
    Returns:
        Formatted string with requirement details
    """
    description = requirement.get('requirement_description', 'N/A')
    
    # Truncate long descriptions
    if len(description) > 300:
        description = description[:300] + '...'
    
    # NEW: Using similarity_score instead of matching_score
    similarity_score = requirement.get('similarity_score', 0.0)
    match_percentage = f"{similarity_score * 100:.1f}%" if similarity_score else "N/A"
    
    # NEW: Single payrate field instead of min/max
    payrate = requirement.get('payrate')
    if payrate and payrate > 0:
        pay_rate_str = f"${payrate:.2f}/hr"
    else:
        pay_rate_str = "Negotiable"
    
    # NEW: Duration field
    duration = requirement.get('requirement_duration')
    duration_str = f"{duration} months" if duration else "Not specified"
    
    # NEW: Open date
    open_date = requirement.get('requirement_open_date')
    open_date_str = str(open_date) if open_date else "ASAP"
    
    # Location (handles remote flag)
    location = requirement.get('location', 'Remote')
    
    formatted = f"""
    Job Requirement:
    - Title: {requirement.get('requirement_title', 'N/A')}
    - Client: {requirement.get('client_name', 'N/A')}
    - Location: {location}
    - Pay Rate: {pay_rate_str}
    - Duration: {duration_str}
    - Start Date: {open_date_str}
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


def format_phone_number(phone: str, default_country_code: str = "+1") -> str:
    """
    Format phone number to ensure it has country code
    
    Args:
        phone: Phone number (may or may not have country code)
        default_country_code: Default country code to add (default: +1 for US)
        
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
    
    # For job_application_tracking table
    if 'cand_id' not in record:
        print("❌ Missing cand_id in record")
        return False
    
    if 'requirement_id' not in record:
        print("❌ Missing requirement_id in record")
        return False
    
    return True