"""
Utility functions for webhook receiver
Updated for production schema: November 2025 version
Changes: min_payrate/max_payrate, requirement_duration as TEXT
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
    
    # Using similarity_score
    similarity_score = requirement.get('similarity_score', 0.0)
    match_percentage = f"{similarity_score * 100:.1f}%" if similarity_score else "N/A"
    
    # NEW: Build pay rate from min/max
    min_pay = requirement.get('min_payrate')
    max_pay = requirement.get('max_payrate')
    
    if min_pay and max_pay:
        if min_pay == max_pay:
            pay_rate_str = f"${float(min_pay):.2f}/hr"
        else:
            pay_rate_str = f"${float(min_pay):.2f} - ${float(max_pay):.2f}/hr"
    elif min_pay:
        pay_rate_str = f"${float(min_pay):.2f}+/hr"
    elif max_pay:
        pay_rate_str = f"Up to ${float(max_pay):.2f}/hr"
    else:
        pay_rate_str = "Negotiable"
    
    # Duration field (now TEXT - can be "3 months", "6-12 months", etc.)
    duration = requirement.get('requirement_duration')
    if duration:
        # If it's already a formatted string, use as-is
        duration_str = str(duration).strip()
    else:
        duration_str = "Not specified"
    
    # Open date
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