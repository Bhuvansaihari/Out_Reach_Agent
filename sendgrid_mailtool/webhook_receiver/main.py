"""
FastAPI webhook receiver for Supabase database events
Triggers email and SMS agents when job applications are tracked
Sends ONE email and ONE SMS per application
Production version with ASYNCIO CONCURRENCY for parallel processing
"""
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import os
from dotenv import load_dotenv
from datetime import datetime
import sys
import html
import re
import asyncio
from functools import partial

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from the project
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
from webhook_receiver.email_template import (
    render_email_template,
    get_email_subject
)

load_dotenv()

app = FastAPI(
    title="Email & SMS Webhook Receiver - Production",
    description="Receives Supabase webhooks with asyncio concurrency for parallel processing",
    version="5.1.0"
)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Semaphore to limit concurrent tasks (prevent overwhelming the system)
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "50"))  # Process 50 candidates at once
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)


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
    Now with semaphore control for concurrency limiting
    """
    async with semaphore:  # Limit concurrent executions
        try:
            print(f"\n{'='*70}")
            print(f"🔍 PROCESSING APPLICATION NOTIFICATIONS (EMAIL + SMS)")
            print(f"   Candidate ID: {cand_id}")
            print(f"   Requirement ID: {requirement_id}")
            print(f"   Active Tasks: {MAX_CONCURRENT_TASKS - semaphore._value}/{MAX_CONCURRENT_TASKS}")
            print(f"{'='*70}\n")
            
            # Run synchronous database call in thread pool
            loop = asyncio.get_event_loop()
            app_data = await loop.run_in_executor(
                None, 
                get_application_details, 
                cand_id, 
                requirement_id
            )
            
            if not app_data:
                print(f"⏸️  Application not found or both notifications already sent. Skipping.\n")
                return
            
            candidate = app_data['candidate']
            requirement = app_data['requirement']
            application_id = app_data['application_id']
            application_status = app_data['application_status']
            email_sent = app_data['email_sent']
            sms_sent = app_data['sms_sent']
            
            first_name = candidate['candidate_first_name']
            full_name = candidate['candidate_name']
            
            # Get mobile number
            candidate_mobile = (
                candidate.get('candidate_mobile') or 
                candidate.get('candidate_work') or 
                candidate.get('candidate_home') or 
                ''
            )
            
            # Format phone number
            formatted_phone = ''
            if candidate_mobile:
                formatted_phone = format_phone_number(candidate_mobile)
            
            # Calculate match score as integer
            match_score_int = int(requirement['similarity_score'] * 100)
            
            # Prepare job type
            job_type = "Contract"  # Default
            if requirement.get('requirement_duration'):
                job_type = f"Contract ({requirement['requirement_duration']})"
            
            # Strip HTML tags from description for email
            description = requirement.get('requirement_description', '')
            clean_description = re.sub(r'<[^>]+>', '', description)
            clean_description = html.unescape(clean_description)
            
            # Truncate to 250 chars
            if len(clean_description) > 250:
                clean_description = clean_description[:250].strip() + '...'
            
            print(f"✅ Application Details:")
            print(f"   - Candidate: {full_name}")
            print(f"   - Email: {candidate['candidate_email']}")
            print(f"   - Mobile: {candidate_mobile or 'Not available'}")
            print(f"   - Job: {requirement['requirement_title']}")
            print(f"   - Client: {requirement['client_name']}")
            print(f"   - Location: {requirement['location']}")
            print(f"   - Match Score: {match_score_int}%")
            print(f"   - Email Sent: {email_sent}")
            print(f"   - SMS Sent: {sms_sent}")
            print()
            
            # ===== RENDER EMAIL TEMPLATE =====
            rendered_email_html = render_email_template(
                candidate_name=first_name,
                job_title=requirement['requirement_title'],
                company_name=requirement.get('client_name', 'N/A'),
                location=requirement.get('location', 'Remote'),
                job_type=job_type,
                match_score=str(match_score_int),
                short_description=clean_description,
                application_status=application_status.upper()
            )
            
            email_subject = get_email_subject(
                job_title=requirement['requirement_title'],
                company_name=requirement.get('client_name', 'N/A'),
                match_score=str(match_score_int)
            )
            
            # Prepare inputs for crew
            complete_inputs = {
                # Email-specific (with rendered template)
                'candidate_email': candidate['candidate_email'],
                'candidate_first_name': first_name,
                'rendered_email_html': rendered_email_html,
                'email_subject': email_subject,
                'job_title': requirement['requirement_title'],
                'company_name': requirement.get('client_name', 'N/A'),
                'location': requirement.get('location', 'Remote'),
                'application_status': application_status.upper(),
                'applied_at': datetime.now().strftime("%b %d, %Y at %I:%M %p"),
                'from_email': os.getenv('SENDGRID_FROM_EMAIL'),
                'current_year': str(datetime.now().year),
                
                # SMS-specific
                'candidate_mobile': formatted_phone or 'N/A',
                'match_score': str(match_score_int),
                
                # Backward compatibility
                'job_count': 1,
                'job_details': format_single_requirement(requirement),
            }
            
            # ===== SEND EMAIL (in thread pool to avoid blocking) =====
            if not email_sent:
                print(f"{'='*70}")
                print(f"📧 SENDING EMAIL NOTIFICATION")
                print(f"{'='*70}\n")
                
                try:
                    # Run crew in thread pool
                    email_func = partial(
                        SendgridMailtool().email_crew().kickoff,
                        inputs=complete_inputs
                    )
                    result = await loop.run_in_executor(None, email_func)
                    
                    print(f"\n✅ Email sent successfully!")
                    await loop.run_in_executor(None, mark_email_sent, application_id)
                except Exception as e:
                    print(f"❌ Error sending email: {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"⏭️  Email already sent, skipping\n")
            
            # ===== SEND SMS (in thread pool to avoid blocking) =====
            if not sms_sent:
                if not candidate_mobile:
                    print(f"⚠️  No mobile number available, skipping SMS\n")
                    await loop.run_in_executor(None, mark_sms_sent, application_id)
                elif not validate_phone_number(formatted_phone):
                    print(f"⚠️  Invalid phone number format, skipping SMS\n")
                    await loop.run_in_executor(None, mark_sms_sent, application_id)
                else:
                    print(f"\n{'='*70}")
                    print(f"📱 SENDING SMS NOTIFICATION")
                    print(f"{'='*70}\n")
                    
                    try:
                        # Run crew in thread pool
                        sms_func = partial(
                            SendgridMailtool().sms_crew().kickoff,
                            inputs=complete_inputs
                        )
                        result = await loop.run_in_executor(None, sms_func)
                        
                        print(f"\n✅ SMS sent successfully!")
                        await loop.run_in_executor(None, mark_sms_sent, application_id)
                    except Exception as e:
                        print(f"❌ Error sending SMS: {str(e)}")
                        import traceback
                        traceback.print_exc()
            else:
                print(f"⏭️  SMS already sent, skipping\n")
            
            print(f"\n{'='*70}")
            print(f"✅ APPLICATION PROCESSING COMPLETED")
            print(f"{'='*70}\n")
            
            return {
                "success": True,
                "cand_id": cand_id,
                "requirement_id": requirement_id,
                "application_id": application_id,
                "email_sent": not email_sent,
                "sms_sent": not sms_sent
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
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")
):
    """
    Webhook endpoint for Supabase notifications
    NOW WITH ASYNCIO CONCURRENCY - processes multiple candidates in parallel!
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
        print(f"📋 Creating async task for parallel processing...\n")
        
        # Create task with asyncio for TRUE CONCURRENCY
        asyncio.create_task(
            process_notifications_for_application(cand_id, requirement_id)
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": f"Email and SMS notifications queued with concurrency for cand_id: {cand_id}, requirement_id: {requirement_id}",
                "cand_id": cand_id,
                "requirement_id": requirement_id,
                "timestamp": datetime.now().isoformat(),
                "concurrency": {
                    "max_concurrent_tasks": MAX_CONCURRENT_TASKS,
                    "enabled": True
                }
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
        "version": "5.1.0 (Asyncio Concurrency)",
        "status": "active",
        "concurrency": {
            "enabled": True,
            "max_concurrent_tasks": MAX_CONCURRENT_TASKS,
            "performance": f"Can process {MAX_CONCURRENT_TASKS} candidates simultaneously"
        },
        "schema": {
            "candidates": "auto_apply_cand",
            "requirements": "parsed_requirements",
            "tracking": "job_application_tracking"
        },
        "capabilities": ["email", "sms", "html_templates", "parallel_processing"],
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
        "concurrency": {
            "max_concurrent_tasks": MAX_CONCURRENT_TASKS,
            "available_slots": semaphore._value,
            "active_tasks": MAX_CONCURRENT_TASKS - semaphore._value
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
    print("🚀 EMAIL & SMS WEBHOOK RECEIVER - PRODUCTION v5.1")
    print("   Mode: EMAIL + SMS PER APPLICATION")
    print("   Processing: ASYNCIO CONCURRENCY (PARALLEL)")
    print("   Template: Professional HTML Email Template")
    print("="*70)
    print(f"📡 Endpoint: http://0.0.0.0:8000/webhook/job-match")
    print(f"❤️  Health: http://0.0.0.0:8000/health")
    print(f"💾 Database: Supabase (PostgreSQL)")
    print(f"📊 Tables: auto_apply_cand + parsed_requirements + job_application_tracking")
    print(f"📧 Email: SendGrid (Professional HTML Template)")
    print(f"📱 SMS: Twilio")
    print(f"⚡ Concurrency: {MAX_CONCURRENT_TASKS} simultaneous tasks")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")