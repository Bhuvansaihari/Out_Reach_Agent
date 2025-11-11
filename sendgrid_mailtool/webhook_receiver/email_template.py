"""
Email template renderer for job match notifications
"""
from datetime import datetime
from typing import Dict
import os


def load_email_template() -> str:
    """Load the HTML email template from file"""
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'src', 'sendgrid_mailtool', 'templates', 'job_match_email.html'
    )
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback: return inline template if file not found
        print(f"⚠️  Template file not found at: {template_path}")
        print("Using inline template as fallback")
        return get_inline_template()


def get_inline_template() -> str:
    """Returns inline HTML template as fallback"""
    # Return the full HTML template here as a string
    # (same content as the file above)
    return """<!doctype html>..."""  # Full template here


def render_email_template(
    candidate_name: str,
    job_title: str,
    company_name: str,
    location: str,
    job_type: str,
    match_score: str,
    short_description: str,
    application_status: str,
    applied_at: str = None
) -> str:
    """
    Render the email template with actual data
    
    Args:
        candidate_name: Candidate's full name
        job_title: Job/requirement title
        company_name: Client/company name
        location: Job location
        job_type: Type of job (Full-time, Contract, etc.)
        match_score: Match percentage (e.g., "87")
        short_description: Brief job description
        application_status: Application status (e.g., "MATCHED", "APPLIED")
        applied_at: Timestamp of application (defaults to now)
        
    Returns:
        Rendered HTML email content
    """
    template = load_email_template()
    
    # Format timestamp
    if not applied_at:
        applied_at = datetime.now().strftime("%b %d, %Y at %I:%M %p")
    
    # Truncate description if too long
    if len(short_description) > 250:
        short_description = short_description[:250] + '...'
    
    # Default values for links (you can make these dynamic later)
    job_link = "https://rangam.com/job-applications"
    support_link = "https://rangam.com/support"
    manage_subscription_link = "https://rangam.com/settings"
    privacy_link = "https://rangam.com/privacy"
    unsubscribe_link = "https://rangam.com/unsubscribe"
    
    # Replace all template variables
    rendered = template.replace('{{candidate_name}}', candidate_name)
    rendered = rendered.replace('{{job_title}}', job_title)
    rendered = rendered.replace('{{company_name}}', company_name)
    rendered = rendered.replace('{{location}}', location)
    rendered = rendered.replace('{{job_type}}', job_type)
    rendered = rendered.replace('{{match_score}}', str(match_score))
    rendered = rendered.replace('{{short_description}}', short_description)
    rendered = rendered.replace('{{application_status}}', application_status)
    rendered = rendered.replace('{{applied_at}}', applied_at)
    rendered = rendered.replace('{{job_link}}', job_link)
    rendered = rendered.replace('{{support_link}}', support_link)
    rendered = rendered.replace('{{manage_subscription_link}}', manage_subscription_link)
    rendered = rendered.replace('{{privacy_link}}', privacy_link)
    rendered = rendered.replace('{{unsubscribe_link}}', unsubscribe_link)
    
    return rendered


def get_email_subject(job_title: str, company_name: str, match_score: str) -> str:
    """
    Generate dynamic email subject line
    
    Args:
        job_title: Job/requirement title
        company_name: Client/company name
        match_score: Match percentage
        
    Returns:
        Email subject line
    """
    return f"✓ Applied: {job_title} at {company_name} ({match_score}% match)"