#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from sendgrid_mailtool.crew import SendgridMailtool

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


# Mock job data (will be replaced with real database data later)
MOCK_JOBS = [
    {
        "title": "Senior Python Developer",
        "company": "TechCorp Solutions",
        "location": "Bangalore, India (Hybrid)",
        "description": "Looking for an experienced Python developer with expertise in AI/ML, FastAPI, and microservices architecture."
    },
    {
        "title": "Machine Learning Engineer",
        "company": "AI Innovations Ltd",
        "location": "Hyderabad, India (Remote)",
        "description": "Seeking ML engineer to build RAG systems, work with vector databases, and develop LLM applications."
    },
    {
        "title": "Full Stack AI Developer",
        "company": "DataDrive Systems",
        "location": "Mumbai, India (On-site)",
        "description": "Full stack role focusing on AI integration, building Streamlit apps, and API development with Python."
    },
    {
        "title": "AI/ML Software Engineer",
        "company": "CloudTech Ventures",
        "location": "Pune, India (Hybrid)",
        "description": "Develop cutting-edge AI solutions using LangChain, vector databases, and modern ML frameworks."
    }
]


def format_job_details(jobs):
    """Format job details for the email content"""
    formatted_jobs = ""
    for idx, job in enumerate(jobs, 1):
        formatted_jobs += f"""
        Job {idx}:
        - Title: {job['title']}
        - Company: {job['company']}
        - Location: {job['location']}
        - Description: {job['description']}
        
        """
    return formatted_jobs.strip()


def run():
    """
    Run the crew to send job match email to a candidate.
    Takes email input from terminal.
    """
    print("\n" + "="*60)
    print("🤖 AUTO-APPLY AGENT - JOB MATCH EMAIL SENDER")
    print("="*60 + "\n")
    
    # Get input from terminal
    try:
        candidate_email = input("Enter candidate email address: ").strip()
        if not candidate_email or "@" not in candidate_email:
            print("❌ Error: Invalid email address provided.")
            return
        
        candidate_first_name = input("Enter candidate first name: ").strip()
        if not candidate_first_name:
            print("❌ Error: First name cannot be empty.")
            return
        
        print(f"\n📧 Preparing to send job matches to {candidate_first_name} ({candidate_email})...")
        print(f"📊 Found {len(MOCK_JOBS)} matching jobs\n")
        
        # Prepare inputs for the crew
        inputs = {
            'candidate_email': candidate_email,
            'candidate_first_name': candidate_first_name,
            'job_count': len(MOCK_JOBS),
            'job_details': format_job_details(MOCK_JOBS),
            'from_email': 'bhuvannaidu2524@gmail.com',
            'current_year': str(datetime.now().year)
        }
        
        print("🚀 Starting email creation and delivery process...\n")
        print("-"*60)
        
        # Execute the crew
        result = SendgridMailtool().crew().kickoff(inputs=inputs)
        
        print("\n" + "-"*60)
        print("✅ Process completed successfully!")
        print("="*60 + "\n")
        
        return result
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An error occurred while running the crew: {e}")
        raise


def train():
    """
    Train the crew for a given number of iterations.
    Usage: python main.py train <n_iterations> <filename>
    """
    if len(sys.argv) < 3:
        print("Usage: python main.py train <n_iterations> <filename>")
        return
    
    inputs = {
        'candidate_email': 'test@example.com',
        'candidate_first_name': 'John',
        'job_count': len(MOCK_JOBS),
        'job_details': format_job_details(MOCK_JOBS),
        'from_email': 'bhuvannaidu2524@gmail.com',
        'current_year': str(datetime.now().year)
    }
    
    try:
        SendgridMailtool().crew().train(
            n_iterations=int(sys.argv[1]), 
            filename=sys.argv[2], 
            inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    Usage: python main.py replay <task_id>
    """
    if len(sys.argv) < 2:
        print("Usage: python main.py replay <task_id>")
        return
        
    try:
        SendgridMailtool().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    Usage: python main.py test <n_iterations> <eval_llm>
    """
    if len(sys.argv) < 3:
        print("Usage: python main.py test <n_iterations> <eval_llm>")
        return
    
    inputs = {
        'candidate_email': 'test@example.com',
        'candidate_first_name': 'Jane',
        'job_count': len(MOCK_JOBS),
        'job_details': format_job_details(MOCK_JOBS),
        'from_email': 'bhuvannaidu2524@gmail.com',
        'current_year': str(datetime.now().year)
    }
    
    try:
        SendgridMailtool().crew().test(
            n_iterations=int(sys.argv[1]), 
            eval_llm=sys.argv[2], 
            inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


if __name__ == "__main__":
    run()