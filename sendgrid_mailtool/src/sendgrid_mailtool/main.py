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
        print(f"   - Match Score: {requirement['matching_score'] * 100:.1f}%")
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
            'match_score': f"{requirement['matching_score'] * 100:.0f}",
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