"""
Database connection and helper functions for webhook receiver
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


def get_candidate_single_match(candidate_id: int, requirement_id: int) -> Optional[Dict]:
    """
    Get candidate details and ONE specific matched requirement
    
    Args:
        candidate_id: The candidate's ID
        requirement_id: The requirement ID for this match
        
    Returns:
        Dictionary with candidate info and single requirement, or None if not found
    """
    try:
        print(f"🔍 Querying database for candidate_id: {candidate_id}, requirement_id: {requirement_id}")
        
        # Call stored procedure using RPC
        response = supabase.rpc(
            'get_candidate_single_match',
            {
                'p_candidate_id': candidate_id,
                'p_requirement_id': requirement_id
            }
        ).execute()
        
        if not response.data or len(response.data) == 0:
            print(f"⏳ Match not found or already fully notified (both email and SMS sent)")
            return None
        
        match = response.data[0]
        
        # Extract candidate info
        candidate_info = {
            'candidate_id': match['candidate_id'],
            'candidate_name': match['candidate_name'],
            'candidate_email': match['candidate_email'],
            'candidate_mobile': match.get('candidate_mobile'),
            'overall_experience': match.get('overall_experience')
        }
        
        # Extract requirement details
        requirement = {
            'requirement_id': match['requirement_id'],
            'requirement_title': match['requirement_title'],
            'requirement_description': match['requirement_description'],
            'match_score': float(match['match_score']) if match['match_score'] else 0.0
        }
        
        match_id = match['match_id']
        email_sent = match.get('email_sent', False)
        sms_sent = match.get('sms_sent', False)
        
        print(f"✅ Found match: {requirement['requirement_title']} for {candidate_info['candidate_name']}")
        print(f"   Status: Email sent={email_sent}, SMS sent={sms_sent}")
        
        return {
            'candidate': candidate_info,
            'requirement': requirement,
            'match_id': match_id,
            'email_sent': email_sent,
            'sms_sent': sms_sent
        }
        
    except Exception as e:
        print(f"❌ Error fetching match: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def mark_email_sent(match_id: int) -> bool:
    """
    Mark a single job match as email sent
    
    Args:
        match_id: The match_id to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from datetime import datetime
        
        response = supabase.table('candidate_job_matches')\
            .update({
                'email_sent': True,
                'email_sent_at': datetime.now().isoformat()
            })\
            .eq('match_id', match_id)\
            .execute()
        
        print(f"✅ Marked match_id {match_id} as email_sent=True")
        return True
        
    except Exception as e:
        print(f"❌ Error updating email_sent status: {str(e)}")
        return False


def mark_sms_sent(match_id: int) -> bool:
    """
    Mark a single job match as SMS sent
    
    Args:
        match_id: The match_id to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from datetime import datetime
        
        response = supabase.table('candidate_job_matches')\
            .update({
                'sms_sent': True,
                'sms_sent_at': datetime.now().isoformat()
            })\
            .eq('match_id', match_id)\
            .execute()
        
        print(f"✅ Marked match_id {match_id} as sms_sent=True")
        return True
        
    except Exception as e:
        print(f"❌ Error updating sms_sent status: {str(e)}")
        return False