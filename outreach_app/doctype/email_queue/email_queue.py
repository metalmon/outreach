# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import os
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, time_diff_in_seconds, add_to_date
from frappe.utils.background_jobs import enqueue

class EmailQueue(Document):
    def validate(self):
        """Validate email queue entry"""
        if not self.recipient_email:
            frappe.throw("Recipient Email is required")
        
        if not self.subject:
            frappe.throw("Subject is required")
        
        if not self.message:
            frappe.throw("Message is required")
        
        # Set default scheduled time if not provided
        if not self.scheduled_time:
            self.scheduled_time = now_datetime()
        
        # Validate contact if provided
        if self.contact and not frappe.db.exists("Contact", self.contact):
            frappe.throw(f"Contact {self.contact} does not exist")
        
        # Validate email provider if provided
        if self.email_provider and not frappe.db.exists("Email Provider", self.email_provider):
            frappe.throw(f"Email Provider {self.email_provider} does not exist")
        
        # Validate email account if provided
        if self.email_account and not frappe.db.exists("Email Account", self.email_account):
            frappe.throw(f"Email Account {self.email_account} does not exist")
        
        # Validate campaign if provided
        if self.campaign and not frappe.db.exists("Campaign", self.campaign):
            frappe.throw(f"Campaign {self.campaign} does not exist")
        
        # Validate campaign step if provided
        if self.campaign_step and not frappe.db.exists("Campaign Step", self.campaign_step):
            frappe.throw(f"Campaign Step {self.campaign_step} does not exist")
    
    def before_insert(self):
        """Before inserting a new email queue entry"""
        # If contact is provided but no email provider or account is assigned,
        # check if there's an existing sender assignment
        if self.contact and not (self.email_provider and self.email_account):
            self.check_sender_assignment()
        
        # If no email provider is assigned, get the default provider
        if not self.email_provider:
            self.assign_default_provider()
        
        # If no email account is assigned, get the next available account
        if self.email_provider and not self.email_account:
            self.assign_email_account()
        
        # If sender details are not provided, get them from the email account
        if self.email_account and not (self.sender_name and self.sender_email):
            self.get_sender_details()
        
        # Calculate the next send time based on provider settings
        if self.status == "Queued" and self.email_provider:
            self.calculate_next_send_time()
    
    def check_sender_assignment(self):
        """Check if contact has an existing sender assignment"""
        from outreach_app.outreach_app.doctype.sender_assignment.sender_assignment import SenderAssignment
        
        assignment = SenderAssignment.get_assignment_for_contact(self.contact)
        
        if assignment:
            self.email_provider = assignment.email_provider
            self.email_account = assignment.email_account
    
    def assign_default_provider(self):
        """Assign the default email provider"""
        providers = frappe.get_all(
            "Email Provider",
            filters={"is_active": 1},
            limit=1
        )
        
        if providers:
            self.email_provider = providers[0].name
    
    def assign_email_account(self):
        """Assign the next available email account from the provider"""
        provider = frappe.get_doc("Email Provider", self.email_provider)
        account = provider.get_next_available_account(self.contact)
        
        if account:
            self.email_account = account.name
            
            # Create sender assignment if contact is provided
            if self.contact:
                from outreach_app.outreach_app.doctype.sender_assignment.sender_assignment import SenderAssignment
                
                # Check if assignment already exists
                existing_assignment = SenderAssignment.get_assignment_for_contact(self.contact)
                
                if not existing_assignment:
                    # Create new assignment
                    SenderAssignment.create_assignment(
                        self.contact,
                        account.name,
                        provider.name,
                        self.campaign
                    )
    
    def get_sender_details(self):
        """Get sender details from the email account"""
        account = frappe.get_doc("Email Account", self.email_account)
        provider = frappe.get_doc("Email Provider", self.email_provider)
        
        self.sender_email = account.email
        
        # Use default sender name from provider if available
        if provider.default_sender_name:
            self.sender_name = provider.default_sender_name
        else:
            # Extract name from email (before @)
            self.sender_name = account.email.split('@')[0].replace('.', ' ').title()
    
    def calculate_next_send_time(self):
        """Calculate the next send time based on provider settings"""
        provider = frappe.get_doc("Email Provider", self.email_provider)
        
        # Get the last sent email from this provider
        last_sent = frappe.get_all(
            "Email Queue",
            filters={
                "email_provider": self.email_provider,
                "status": "Sent"
            },
            fields=["sent_time"],
            order_by="sent_time desc",
            limit=1
        )
        
        if last_sent:
            last_send_time = get_datetime(last_sent[0].sent_time)
        else:
            last_send_time = now_datetime()
        
        # Calculate next send time
        next_send_time = provider.get_next_send_time(last_send_time)
        
        # Update scheduled time if it's earlier than the calculated next send time
        if get_datetime(self.scheduled_time) < next_send_time:
            self.scheduled_time = next_send_time
            self.status = "Scheduled"
    
    def send(self):
        """Send the email using the assigned email account"""
        if self.status not in ["Queued", "Scheduled"]:
            return False, f"Cannot send email with status {self.status}"
        
        if not self.email_account:
            return False, "No email account assigned"
        
        try:
            self.status = "Sending"
            self.save()
            
            account = frappe.get_doc("Email Account", self.email_account)
            
            # Prepare attachments
            attachments = []
            if self.attachments:
                for attachment in self.attachments:
                    if os.path.exists(attachment.file_path):
                        attachments.append({
                            "fname": attachment.file_name,
                            "fpath": attachment.file_path
                        })
            
            # Send email
            success, message = account.send_email(
                to_email=self.recipient_email,
                subject=self.subject,
                message=self.message,
                html_message=self.html_message,
                attachments=attachments
            )
            
            if success:
                self.status = "Sent"
                self.sent_time = now_datetime()
                
                # Update sender assignment if contact is provided
                if self.contact:
                    from outreach_app.outreach_app.doctype.sender_assignment.sender_assignment import SenderAssignment
                    
                    assignment = SenderAssignment.get_assignment_for_contact(self.contact)
                    if assignment:
                        assignment.update_email_sent(self.campaign)
            else:
                self.status = "Error"
                self.error = message
                self.retry_count += 1
            
            self.save()
            return success, message
        
        except Exception as e:
            self.status = "Error"
            self.error = str(e)
            self.retry_count += 1
            self.save()
            
            frappe.log_error(
                message=f"Failed to send email to {self.recipient_email}: {str(e)}",
                title="Email Queue Error"
            )
            
            return False, str(e)
    
    def retry(self):
        """Retry sending the email"""
        if self.status != "Error":
            return False, f"Cannot retry email with status {self.status}"
        
        if self.retry_count >= 3:
            return False, "Maximum retry count reached"
        
        self.status = "Queued"
        self.save()
        
        return self.send()
    
    def cancel(self):
        """Cancel the email"""
        if self.status in ["Sent", "Cancelled"]:
            return False, f"Cannot cancel email with status {self.status}"
        
        self.status = "Cancelled"
        self.save()
        
        return True, "Email cancelled successfully"
    
    @staticmethod
    def process_queue(limit=100):
        """
        Process the email queue
        This method is called by the scheduler
        """
        # Get emails that are scheduled to be sent now
        current_time = now_datetime()
        
        emails = frappe.get_all(
            "Email Queue",
            filters={
                "status": ["in", ["Queued", "Scheduled"]],
                "scheduled_time": ["<=", current_time]
            },
            fields=["name"],
            order_by="priority desc, scheduled_time asc",
            limit=limit
        )
        
        for email_data in emails:
            # Process each email in a background job
            enqueue(
                "outreach_app.outreach_app.doctype.email_queue.email_queue.send_email",
                queue="short",
                email_queue=email_data.name
            )
    
    @staticmethod
    def clear_old_emails(days=30):
        """
        Clear old emails from the queue
        This method is called by the scheduler
        """
        cutoff_date = add_to_date(now_datetime(), days=-days)
        
        # Get old emails
        old_emails = frappe.get_all(
            "Email Queue",
            filters={
                "status": ["in", ["Sent", "Error", "Expired", "Cancelled"]],
                "modified": ["<", cutoff_date]
            },
            fields=["name"]
        )
        
        # Delete old emails
        for email_data in old_emails:
            frappe.delete_doc("Email Queue", email_data.name)
        
        frappe.db.commit()
        
        return len(old_emails)

def send_email(email_queue):
    """
    Send an email from the queue
    This function is called by the background job
    """
    try:
        email = frappe.get_doc("Email Queue", email_queue)
        email.send()
    except Exception as e:
        frappe.log_error(
            message=f"Failed to process email queue {email_queue}: {str(e)}",
            title="Email Queue Processing Error"
        )
