from crewai.tools.base_tool import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()


class SendGridEmailInput(BaseModel):
    """Input schema for SendGrid Email Tool."""
    to_email: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject line")
    html_content: str = Field(..., description="HTML content of the email")
    from_email: str = Field(
        default=os.getenv("SENDGRID_FROM_EMAIL", ""),
        description="Sender email address (defaults to SENDGRID_FROM_EMAIL from .env)"
    )


class SendGridEmailTool(BaseTool):
    name: str = "SendGrid Email Sender"
    description: str = (
        "Sends professional HTML emails via SendGrid API. "
        "Use this tool to deliver job match notifications, "
        "recruitment emails, and candidate communications. "
        "The tool handles email delivery, error handling, and "
        "returns delivery status confirmation."
    )
    args_schema: Type[BaseModel] = SendGridEmailInput

    def _run(self, to_email: str, subject: str, html_content: str, from_email: str = None) -> str:
        """
        Send an email using SendGrid API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML content of the email
            from_email: Sender email address (optional, uses env variable if not provided)
            
        Returns:
            Status message with delivery confirmation or error details
        """
        try:
            # Validate inputs
            if not to_email or "@" not in to_email:
                return f"Error: Invalid recipient email address: {to_email}"
            
            if not subject or len(subject.strip()) == 0:
                return "Error: Email subject cannot be empty"
            
            if not html_content or len(html_content.strip()) == 0:
                return "Error: Email content cannot be empty"
            
            # Get API key and sender email from environment
            api_key = os.getenv("SENDGRID_API_KEY")
            if not api_key:
                return "Error: SENDGRID_API_KEY not found in environment variables"
            
            sender_email = from_email or os.getenv("SENDGRID_FROM_EMAIL")
            if not sender_email:
                return "Error: SENDGRID_FROM_EMAIL not found in environment variables"
            
            reply_to_email = os.getenv("SENDGRID_REPLY_TO_EMAIL", sender_email)
            
            # Initialize SendGrid client
            sg = sendgrid.SendGridAPIClient(api_key=api_key)
            
            # Create email object
            from_email_obj = Email(sender_email)
            to_email_obj = To(to_email)
            content = HtmlContent(html_content)
            
            # Build mail object
            mail = Mail(
                from_email=from_email_obj,
                to_emails=to_email_obj,
                subject=subject,
                html_content=content
            )
            
            # Set reply-to if available
            if reply_to_email:
                mail.reply_to = Email(reply_to_email)
            
            # Send email
            response = sg.client.mail.send.post(request_body=mail.get())
            
            # Check response status
            if response.status_code in [200, 201, 202]:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return (
                    f"✅ Email sent successfully!\n"
                    f"Status Code: {response.status_code}\n"
                    f"Recipient: {to_email}\n"
                    f"Subject: {subject}\n"
                    f"Timestamp: {timestamp}\n"
                    f"Message: Email delivered to SendGrid for processing."
                )
            else:
                return (
                    f"⚠️ Email sent but received unexpected status code.\n"
                    f"Status Code: {response.status_code}\n"
                    f"Response Body: {response.body}\n"
                    f"Response Headers: {response.headers}"
                )
                
        except Exception as e:
            error_message = str(e)
            return (
                f"❌ Error sending email:\n"
                f"Error Type: {type(e).__name__}\n"
                f"Error Message: {error_message}\n"
                f"Recipient: {to_email}\n"
                f"Please check your SendGrid API key, sender authentication, "
                f"and ensure the sender email is verified in SendGrid."
            )