"""
Database connection and helper functions for webhook receiver
Updated for production schema: auto_apply_cand, parsed_requirements, job_application_tracking
Schema version: November 2025 (with similarity_score, matching_id, is_remote_location)
"""
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from typing import Dict, Optional

load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase: Client = create_client(supabase_url, supabase_key)


def get_application_details(cand_id: int, requirement_id: str) -> Optional[Dict]:
    """
    Get candidate details and requirement details for a specific application
    
    Args:
        cand_id: The candidate's ID (from auto_apply_cand)
        requirement_id: The requirement ID (from parsed_requirements)
        
    Returns:
        Dictionary with candidate info, requirement info, and application details
    """
    try:
        print(f"🔍 Querying database for cand_id: {cand_id}, requirement_id: {requirement_id}")
        
        # Call stored procedure using RPC
        response = supabase.rpc(
            'get_application_details',
            {
                'p_cand_id': cand_id,
                'p_requirement_id': requirement_id
            }
        ).execute()
        
        if not response.data or len(response.data) == 0:
            print(f"⏳ Application not found or both notifications already sent")
            return None
        
        app = response.data[0]
        
        # Build full name
        full_name = f"{app['candidate_first_name']} {app['candidate_last_name']}".strip()
        
        # Extract candidate info
        candidate_info = {
            'cand_id': app['cand_id'],
            'candidate_name': full_name,
            'candidate_first_name': app['candidate_first_name'],
            'candidate_last_name': app['candidate_last_name'],
            'candidate_email': app['candidate_email'],
            'candidate_mobile': app.get('candidate_mobile'),
            'candidate_home': app.get('candidate_home'),
            'candidate_work': app.get('candidate_work'),
            'candidate_experience': app.get('candidate_experience', 0),
            'candidate_zipcode': app.get('candidate_zipcode'),
            'candidate_address': app.get('candidate_address')
        }
        
        # Extract requirement details (UPDATED for new schema)
        requirement_info = {
            'requirement_id': app['requirement_id'],
            'requirement_title': app['requirement_title'],  # from client_job_title
            'requirement_description': app.get('requirement_description', ''),  # from requirement_job_description
            'client_name': app.get('client_name', 'N/A'),
            'requirement_location': app.get('requirement_location', ''),  # from address
            'requirement_zipcode': app.get('requirement_zipcode', ''),  # from req_zipcode
            'is_remote_location': app.get('is_remote_location', False),
            'payrate': app.get('payrate'),  # single payrate field now
            'requirement_duration': app.get('requirement_duration'),
            'requirement_open_date': app.get('requirement_open_date'),
            'matching_id': app.get('matching_id'),
            'similarity_score': float(app['similarity_score']) if app.get('similarity_score') else 0.0
        }
        
        application_id = app['application_id']
        application_status = app.get('application_status', 'MATCHED')
        applied_at = app.get('applied_at')
        email_sent = app.get('email_sent', False)
        sms_sent = app.get('sms_sent', False)
        
        # Build location string
        if requirement_info['is_remote_location']:
            location = 'Remote'
        else:
            location_parts = []
            if requirement_info['requirement_location']:
                location_parts.append(requirement_info['requirement_location'])
            if requirement_info['requirement_zipcode']:
                location_parts.append(requirement_info['requirement_zipcode'])
            location = ', '.join(location_parts) or 'Location TBD'
        
        requirement_info['location'] = location
        
        print(f"✅ Found application: {requirement_info['requirement_title']} for {full_name}")
        print(f"   Similarity Score: {requirement_info['similarity_score']:.4f}")
        print(f"   Status: {application_status}")
        print(f"   Email sent={email_sent}, SMS sent={sms_sent}")
        
        return {
            'candidate': candidate_info,
            'requirement': requirement_info,
            'application_id': application_id,
            'application_status': application_status,
            'applied_at': applied_at,
            'email_sent': email_sent,
            'sms_sent': sms_sent
        }
        
    except Exception as e:
        print(f"❌ Error fetching application details: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def mark_email_sent(application_id: int) -> bool:
    """
    Mark an application as email sent
    
    Args:
        application_id: The application_id to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from datetime import datetime
        
        response = supabase.table('job_application_tracking')\
            .update({
                'email_sent': True,
                'email_sent_at': datetime.now().isoformat()
            })\
            .eq('application_id', application_id)\
            .execute()
        
        print(f"✅ Marked application_id {application_id} as email_sent=True")
        return True
        
    except Exception as e:
        print(f"❌ Error updating email_sent status: {str(e)}")
        return False


def mark_sms_sent(application_id: int) -> bool:
    """
    Mark an application as SMS sent
    
    Args:
        application_id: The application_id to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from datetime import datetime
        
        response = supabase.table('job_application_tracking')\
            .update({
                'sms_sent': True,
                'sms_sent_at': datetime.now().isoformat()
            })\
            .eq('application_id', application_id)\
            .execute()
        
        print(f"✅ Marked application_id {application_id} as sms_sent=True")
        return True
        
    except Exception as e:
        print(f"❌ Error updating sms_sent status: {str(e)}")
        return False