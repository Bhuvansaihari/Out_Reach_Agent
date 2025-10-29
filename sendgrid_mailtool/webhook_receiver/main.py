"""
FastAPI webhook receiver for Supabase database events
Triggers email and SMS agents when job matches are inserted
Sends ONE email and ONE SMS per job match
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import os
from dotenv import load_dotenv
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sendgrid_mailtool.crew import SendgridMailtool
from webhook_receiver.database import (
    get_candidate_single_match,
    mark_email_sent,
    mark_sms_sent
)
from webhook_receiver.utils import (
    format_single_requirement,
    extract_first_name,
    format_phone_number,
    validate_phone_number,
    validate_webhook_payload
)

load_dotenv()

app = FastAPI(
    title="Email & SMS Webhook Receiver",
    description="Receives Supabase webhooks and triggers email and SMS agents for job matches",
    version="3.0.0"
)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


class WebhookPayload(BaseModel):
    """Supabase webhook payload structure"""
    type: str
    table: str
    record: dict
    schema_name: str = Field(alias="schema")
    old_record: Optional[dict] = None


async def process_notifications_for_match(candidate_id: int, requirement_id: int):
    """
    Process and send email AND SMS to candidate for ONE matched requirement
    
    Args:
        candidate_id: The candidate's ID
        requirement_id: The requirement ID for this match
    """
    try:
        print(f"\n{'='*70}")
        print(f"🔍 PROCESSING MATCH NOTIFICATIONS (EMAIL + SMS)")
        print(f"   Candidate ID: {candidate_id}")
        print(f"   Requirement ID: {requirement_id}")
        print(f"{'='*70}\n")
        
        # Get candidate details and matched requirement
        match_data = get_candidate_single_match(candidate_id, requirement_id)
        
        if not match_data:
            print(f"⏸️  Match not found or both notifications already sent. Skipping.\n")
            return
        
        candidate = match_data['candidate']
        requirement = match_data['requirement']
        match_id = match_data['match_id']
        email_sent = match_data['email_sent']
        sms_sent = match_data['sms_sent']
        
        first_name = extract_first_name(candidate['candidate_name'])
        candidate_mobile = candidate.get('candidate_mobile', '')
        
        # Format phone number if available
        formatted_phone = ''
        if candidate_mobile:
            formatted_phone = format_phone_number(candidate_mobile)
        
        print(f"✅ Match Details:")
        print(f"   - Candidate: {candidate['candidate_name']}")
        print(f"   - Email: {candidate['candidate_email']}")
        print(f"   - Mobile: {candidate_mobile or 'Not available'}")
        print(f"   - Job: {requirement['requirement_title']}")
        print(f"   - Match Score: {requirement['match_score']:.1f}%")
        print(f"   - Email Sent: {email_sent}")
        print(f"   - SMS Sent: {sms_sent}")
        print()
        
        # Prepare COMPLETE inputs for crew (includes all variables for both email and SMS)
        complete_inputs = {
            # Email-specific
            'candidate_email': candidate['candidate_email'],
            'candidate_first_name': first_name,
            'job_count': 1,
            'job_details': format_single_requirement(requirement),
            'from_email': os.getenv('SENDGRID_FROM_EMAIL'),
            'current_year': str(datetime.now().year),
            
            # SMS-specific
            'candidate_mobile': formatted_phone or 'N/A',  # Provide even if empty
            'job_title': requirement['requirement_title'],
            'match_score': f"{requirement['match_score']:.0f}",
        }
        
        # ===== SEND EMAIL (if not already sent) =====
        if not email_sent:
            print(f"{'='*70}")
            print(f"📧 SENDING EMAIL NOTIFICATION")
            print(f"{'='*70}\n")
            
            try:
                # Use complete inputs
                result = SendgridMailtool().crew().kickoff(inputs=complete_inputs)
                print(f"\n✅ Email sent successfully!")
                mark_email_sent(match_id)
            except Exception as e:
                print(f"❌ Error sending email: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⏭️  Email already sent, skipping email notification\n")
        
        # ===== SEND SMS (if not already sent and phone available) =====
        if not sms_sent:
            if not candidate_mobile:
                print(f"⚠️  No mobile number available, skipping SMS\n")
                mark_sms_sent(match_id)
            elif not validate_phone_number(formatted_phone):
                print(f"⚠️  Invalid phone number format: {candidate_mobile}, skipping SMS\n")
                mark_sms_sent(match_id)
            else:
                print(f"\n{'='*70}")
                print(f"📱 SENDING SMS NOTIFICATION")
                print(f"{'='*70}\n")
                
                try:
                    # Use same complete inputs
                    result = SendgridMailtool().crew().kickoff(inputs=complete_inputs)
                    print(f"\n✅ SMS sent successfully!")
                    mark_sms_sent(match_id)
                except Exception as e:
                    print(f"❌ Error sending SMS: {str(e)}")
                    import traceback
                    traceback.print_exc()
        else:
            print(f"⏭️  SMS already sent, skipping SMS notification\n")
        
        print(f"\n{'='*70}")
        print(f"✅ MATCH PROCESSING COMPLETED")
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "candidate_id": candidate_id,
            "requirement_id": requirement_id,
            "match_id": match_id,
            "email_sent": not email_sent,
            "sms_sent": not sms_sent,
            "candidate_email": candidate['candidate_email'],
            "candidate_mobile": candidate_mobile
        }
        
    except Exception as e:
        error_msg = f"❌ Error processing match: {str(e)}"
        print(f"\n{error_msg}\n")
        import traceback
        traceback.print_exc()
        raise Exception(error_msg)


@app.post("/webhook/job-match")
async def webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")
):
    """
    Webhook endpoint for Supabase notifications
    Processes ONE job match at a time (sends both email and SMS)
    """
    try:
        payload = await request.json()
        
        # Verify webhook secret
        if WEBHOOK_SECRET and x_webhook_secret != WEBHOOK_SECRET:
            print(f"❌ Invalid webhook secret")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        
        print(f"\n{'='*70}")
        print(f"📨 WEBHOOK RECEIVED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        print(f"Event: {payload.get('type')} on {payload.get('table')}")
        print(f"{'='*70}\n")
        
        # Validate payload
        if not validate_webhook_payload(payload):
            raise HTTPException(status_code=400, detail="Invalid payload structure")
        
        # Only process INSERT events on candidate_job_matches
        if payload['type'] != "INSERT":
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "reason": f"Event type '{payload['type']}' not processed"}
            )
        
        if payload['table'] != "candidate_job_matches":
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "reason": f"Table '{payload['table']}' not monitored"}
            )
        
        record = payload['record']
        candidate_id = record.get('candidate_id')
        requirement_id = record.get('requirement_id')
        
        if not candidate_id or not requirement_id:
            raise HTTPException(
                status_code=400, 
                detail="candidate_id and requirement_id required"
            )
        
        print(f"✅ Valid INSERT event")
        print(f"   - Candidate ID: {candidate_id}")
        print(f"   - Requirement ID: {requirement_id}")
        print(f"📋 Queuing notification tasks (Email + SMS)...\n")
        
        # Process in background
        background_tasks.add_task(
            process_notifications_for_match, 
            candidate_id, 
            requirement_id
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": f"Email and SMS notifications queued for candidate_id: {candidate_id}, requirement_id: {requirement_id}",
                "candidate_id": candidate_id,
                "requirement_id": requirement_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Email & SMS Webhook Receiver",
        "version": "3.0.0 (Email + SMS per match)",
        "status": "active",
        "capabilities": ["email", "sms"],
        "endpoints": {
            "webhook": "/webhook/job-match",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "email-sms-webhook-receiver",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "supabase": bool(os.getenv("SUPABASE_URL")),
            "sendgrid": bool(os.getenv("SENDGRID_API_KEY")),
            "twilio": bool(os.getenv("TWILIO_ACCOUNT_SID")),
            "webhook_secret": bool(WEBHOOK_SECRET)
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🚀 EMAIL & SMS WEBHOOK RECEIVER - PRODUCTION MODE")
    print("   Mode: EMAIL + SMS PER JOB MATCH")
    print("="*70)
    print(f"📡 Endpoint: http://0.0.0.0:8000/webhook/job-match")
    print(f"❤️  Health: http://0.0.0.0:8000/health")
    print(f"💾 Database: Supabase (PostgreSQL)")
    print(f"📧 Email: SendGrid")
    print(f"📱 SMS: Twilio")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")