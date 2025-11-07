from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from .tools.sendgrid_email_tool import SendGridEmailTool
from .tools.twilio_sms_tool import TwilioSMSTool


@CrewBase
class SendgridMailtool():
    """SendgridMailtool crew for sending job match emails and SMS to candidates"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # ===== EMAIL AGENTS =====
    @agent
    def email_content_creator(self) -> Agent:
        """Agent responsible for creating personalized email content"""
        return Agent(
            config=self.agents_config['email_content_creator'],
            verbose=True,
            allow_delegation=False
        )

    @agent
    def email_sender(self) -> Agent:
        """Agent responsible for sending emails via SendGrid"""
        return Agent(
            config=self.agents_config['email_sender'],
            tools=[SendGridEmailTool()],
            verbose=True,
            allow_delegation=False
        )

    # ===== SMS AGENTS =====
    @agent
    def sms_content_creator(self) -> Agent:
        """Agent responsible for creating concise SMS content"""
        return Agent(
            config=self.agents_config['sms_content_creator'],
            verbose=True,
            allow_delegation=False
        )

    @agent
    def sms_sender(self) -> Agent:
        """Agent responsible for sending SMS via Twilio"""
        return Agent(
            config=self.agents_config['sms_sender'],
            tools=[TwilioSMSTool()],
            verbose=True,
            allow_delegation=False
        )

    # ===== EMAIL TASKS =====
    @task
    def create_email_content(self) -> Task:
        """Task to create personalized email content"""
        return Task(
            config=self.tasks_config['create_email_content'],
        )

    @task
    def send_email_task(self) -> Task:
        """Task to send the email using SendGrid"""
        return Task(
            config=self.tasks_config['send_email_task'],
        )

    # ===== SMS TASKS =====
    @task
    def create_sms_content(self) -> Task:
        """Task to create concise SMS content"""
        return Task(
            config=self.tasks_config['create_sms_content'],
        )

    @task
    def send_sms_task(self) -> Task:
        """Task to send SMS using Twilio"""
        return Task(
            config=self.tasks_config['send_sms_task'],
        )

    # ===== SEPARATE CREWS =====
    
    @crew
    def email_crew(self) -> Crew:
        """Creates crew for EMAIL ONLY"""
        return Crew(
            agents=[self.email_content_creator(), self.email_sender()],
            tasks=[self.create_email_content(), self.send_email_task()],
            process=Process.sequential,
            verbose=True,
        )

    @crew
    def sms_crew(self) -> Crew:
        """Creates crew for SMS ONLY"""
        return Crew(
            agents=[self.sms_content_creator(), self.sms_sender()],
            tasks=[self.create_sms_content(), self.send_sms_task()],
            process=Process.sequential,
            verbose=True,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the full crew with both email and SMS (for backward compatibility)"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )