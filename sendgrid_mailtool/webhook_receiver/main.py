"""
FastAPI webhook receiver for Supabase database events
Triggers email and SMS agents when job applications are tracked
Sends ONE email and ONE SMS per application
Production version for: auto_apply_cand + parsed_requirements + job_application_tracking
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
    get_application_details,
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
    title="Email & SMS Webhook Receiver - Production",
    description="Receives Supabase webhooks and triggers email and SMS agents for job applications",
    version="4.0.0"
)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


class WebhookPayload(BaseModel):
    """Supabase webhook payload structure"""
    type: str
    table: str
    record: dict
    schema_name: str = Field(alias="schema")
    old_record: Optional[dict] = None


async def process_notifications_for_application(cand_id: int, requirement_id: str):
    """
    Process and send email AND SMS to candidate for ONE job application
    
    Args:
        cand_id: The candidate's ID (from auto_apply_cand)
        requirement_id: The requirement ID (from parsed_requirements)
    """
    try:
        print(f"\n{'='*70}")
        print(f"🔍 PROCESSING APPLICATION NOTIFICATIONS (EMAIL + SMS)")
        print(f"   Candidate ID: {cand_id}")
        print(f"   Requirement ID: {requirement_id}")
        print(f"{'='*70}\n")
        
        # Get application details with candidate and requirement info
        app_data = get_application_details(cand_id, requirement_id)
        
        if not app_data:
            print(f"⏸️  Application not found or both notifications already sent. Skipping.\n")
            return
        
        candidate = app_data['candidate']
        requirement = app_data['requirement']
        application_id = app_data['application_id']
        email_sent = app_data['email_sent']
        sms_sent = app_data['sms_sent']
        
        first_name = candidate['candidate_first_name']
        
        # Get mobile number (try mobile first, then work, then home)
        candidate_mobile = (
            candidate.get('candidate_mobile') or 
            candidate.get('candidate_work') or 
            candidate.get('candidate_home') or 
            ''
        )
        
        # Format phone number if available
        formatted_phone = ''
        if candidate_mobile:
            formatted_phone = format_phone_number(candidate_mobile)
        
        print(f"✅ Application Details:")
        print(f"   - Candidate: {candidate['candidate_name']}")
        print(f"   - Email: {candidate['candidate_email']}")
        print(f"   - Mobile: {candidate_mobile or 'Not available'}")
        print(f"   - Experience: {candidate['candidate_experience']} years")
        print(f"   - Job: {requirement['requirement_title']}")
        print(f"   - Client: {requirement['client_name']}")
        print(f"   - Location: {requirement['location']}")
        print(f"   - Match Score: {requirement['similarity_score'] * 100:.1f}%")
        print(f"   - Email Sent: {email_sent}")
        print(f"   - SMS Sent: {sms_sent}")
        print()
        
        # Prepare COMPLETE inputs for both email and SMS
        complete_inputs = {
            # Email-specific
            'candidate_email': candidate['candidate_email'],
            'candidate_first_name': first_name,
            'job_count': 1,
            'job_details': format_single_requirement(requirement),
            'from_email': os.getenv('SENDGRID_FROM_EMAIL'),
            'current_year': str(datetime.now().year),
            
            # SMS-specific
            'candidate_mobile': formatted_phone or 'N/A',
            'job_title': requirement['requirement_title'],
            'match_score': f"{requirement['similarity_score'] * 100:.0f}",
        }
        
        # ===== SEND EMAIL (if not already sent) =====
        if not email_sent:
            print(f"{'='*70}")
            print(f"📧 SENDING EMAIL NOTIFICATION")
            print(f"{'='*70}\n")
            
            try:
                # Use email_crew() instead of crew()
                result = SendgridMailtool().email_crew().kickoff(inputs=complete_inputs)
                print(f"\n✅ Email sent successfully!")
                mark_email_sent(application_id)
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
                mark_sms_sent(application_id)
            elif not validate_phone_number(formatted_phone):
                print(f"⚠️  Invalid phone number format: {candidate_mobile}, skipping SMS\n")
                mark_sms_sent(application_id)
            else:
                print(f"\n{'='*70}")
                print(f"📱 SENDING SMS NOTIFICATION")
                print(f"{'='*70}\n")
                
                try:
                    # Use sms_crew() instead of crew()
                    result = SendgridMailtool().sms_crew().kickoff(inputs=complete_inputs)
                    print(f"\n✅ SMS sent successfully!")
                    mark_sms_sent(application_id)
                except Exception as e:
                    print(f"❌ Error sending SMS: {str(e)}")
                    import traceback
                    traceback.print_exc()
        else:
            print(f"⏭️  SMS already sent, skipping SMS notification\n")
        
        print(f"\n{'='*70}")
        print(f"✅ APPLICATION PROCESSING COMPLETED")
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "cand_id": cand_id,
            "requirement_id": requirement_id,
            "application_id": application_id,
            "email_sent": not email_sent,
            "sms_sent": not sms_sent,
            "candidate_email": candidate['candidate_email'],
            "candidate_mobile": candidate_mobile
        }
        
    except Exception as e:
        error_msg = f"❌ Error processing application: {str(e)}"
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
    Processes ONE job application at a time (sends both email and SMS)
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
        
        # Only process INSERT events on job_application_tracking
        if payload['type'] != "INSERT":
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "reason": f"Event type '{payload['type']}' not processed"}
            )
        
        if payload['table'] != "job_application_tracking":
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "reason": f"Table '{payload['table']}' not monitored"}
            )
        
        record = payload['record']
        cand_id = record.get('cand_id')
        requirement_id = record.get('requirement_id')
        
        if not cand_id or not requirement_id:
            raise HTTPException(
                status_code=400, 
                detail="cand_id and requirement_id required"
            )
        
        print(f"✅ Valid INSERT event")
        print(f"   - Candidate ID: {cand_id}")
        print(f"   - Requirement ID: {requirement_id}")
        print(f"📋 Queuing notification tasks (Email + SMS)...\n")
        
        # Process in background
        background_tasks.add_task(
            process_notifications_for_application, 
            cand_id, 
            requirement_id
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": f"Email and SMS notifications queued for cand_id: {cand_id}, requirement_id: {requirement_id}",
                "cand_id": cand_id,
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
        "service": "Email & SMS Webhook Receiver - Production",
        "version": "4.0.0 (Email + SMS per application)",
        "status": "active",
        "schema": {
            "candidates": "auto_apply_cand",
            "requirements": "parsed_requirements",
            "tracking": "job_application_tracking"
        },
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
        "service": "email-sms-webhook-receiver-production",
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "supabase": bool(os.getenv("SUPABASE_URL")),
            "sendgrid": bool(os.getenv("SENDGRID_API_KEY")),
            "twilio": bool(os.getenv("TWILIO_ACCOUNT_SID")),
            "webhook_secret": bool(WEBHOOK_SECRET)
        },
        "database_tables": {
            "candidates": "auto_apply_cand",
            "requirements": "parsed_requirements",
            "tracking": "job_application_tracking"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🚀 EMAIL & SMS WEBHOOK RECEIVER - PRODUCTION v4.0")
    print("   Mode: EMAIL + SMS PER APPLICATION")
    print("="*70)
    print(f"📡 Endpoint: http://0.0.0.0:8000/webhook/job-match")
    print(f"❤️  Health: http://0.0.0.0:8000/health")
    print(f"💾 Database: Supabase (PostgreSQL)")
    print(f"📊 Tables: auto_apply_cand + parsed_requirements + job_application_tracking")
    print(f"📧 Email: SendGrid")
    print(f"📱 SMS: Twilio")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")