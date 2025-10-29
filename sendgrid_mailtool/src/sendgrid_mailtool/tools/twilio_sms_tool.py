"""
Twilio SMS Tool for CrewAI
Sends SMS notifications via Twilio API
"""
from crewai.tools.base_tool import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from twilio.rest import Client
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()


class TwilioSMSInput(BaseModel):
    """Input schema for Twilio SMS Tool."""
    to_phone: str = Field(..., description="Recipient phone number (with country code, e.g., +919876543210)")
    message_body: str = Field(..., description="SMS message content (max 1600 characters)")
    from_phone: str = Field(
        default=os.getenv("TWILIO_PHONE_NUMBER", ""),
        description="Sender phone number (defaults to TWILIO_PHONE_NUMBER from .env)"
    )


class TwilioSMSTool(BaseTool):
    name: str = "Twilio SMS Sender"
    description: str = (
        "Sends SMS text messages via Twilio API. "
        "Use this tool to deliver job match notifications via SMS, "
        "recruitment alerts, and candidate communications. "
        "The tool handles SMS delivery, error handling, and "
        "returns delivery status confirmation. "
        "Message length is limited to 1600 characters."
    )
    args_schema: Type[BaseModel] = TwilioSMSInput

    def _run(self, to_phone: str, message_body: str, from_phone: str = None) -> str:
        """
        Send an SMS using Twilio API.
        
        Args:
            to_phone: Recipient phone number (with country code)
            message_body: SMS message content
            from_phone: Sender phone number (optional, uses env variable if not provided)
            
        Returns:
            Status message with delivery confirmation or error details
        """
        try:
            # Validate inputs
            if not to_phone or len(to_phone) < 10:
                return f"Error: Invalid recipient phone number: {to_phone}"
            
            # Ensure phone number has country code
            if not to_phone.startswith('+'):
                return f"Error: Phone number must include country code (e.g., +91 for India): {to_phone}"
            
            if not message_body or len(message_body.strip()) == 0:
                return "Error: SMS message cannot be empty"
            
            if len(message_body) > 1600:
                return f"Error: Message too long ({len(message_body)} chars). Max 1600 characters allowed."
            
            # Get Twilio credentials from environment
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            
            if not account_sid or not auth_token:
                return "Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN not found in environment variables"
            
            sender_phone = os.getenv("TWILIO_PHONE_NUMBER")
            if not sender_phone:
                return "Error: TWILIO_PHONE_NUMBER not found in environment variables"
            
            # Initialize Twilio client
            client = Client(account_sid, auth_token)
            
            # Send SMS
            message = client.messages.create(
                body=message_body,
                from_=sender_phone,
                to=to_phone
            )
            
            # Check response status
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if message.sid:
                return (
                    f"✅ SMS sent successfully!\n"
                    f"Message SID: {message.sid}\n"
                    f"Status: {message.status}\n"
                    f"Recipient: {to_phone}\n"
                    f"Timestamp: {timestamp}\n"
                    f"Message: SMS delivered to Twilio for processing."
                )
            else:
                return (
                    f"⚠️ SMS sent but no SID returned.\n"
                    f"Status: {message.status}\n"
                    f"Recipient: {to_phone}"
                )
                
        except Exception as e:
            error_message = str(e)
            return (
                f"❌ Error sending SMS:\n"
                f"Error Type: {type(e).__name__}\n"
                f"Error Message: {error_message}\n"
                f"Recipient: {to_phone}\n"
                f"Please check your Twilio credentials and phone number format."
            )