
# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import random
from frappe.utils import now_datetime, get_datetime, add_to_date, time_diff_in_seconds, cint

def assign_sender(email_queue_doc):
    """
    Assign a sender to an email queue entry
    This function is called before an email queue entry is inserted
    """
    if not email_queue_doc.contact:
        return
    
    # Check if contact already has a sender assignment
    assignment = frappe.get_all(
        "Sender Assignment",
        filters={
            "contact": email_queue_doc.contact,
            "is_active": 1
        },
        fields=["name", "email_account", "email_provider"],
        limit=1
    )
    
    if assignment:
        # Use existing assignment
        email_queue_doc.email_account = assignment[0].email_account
        email_queue_doc.email_provider = assignment[0].email_provider
        return
    
    # No existing assignment, get a provider
    if email_queue_doc.email_provider:
        provider = frappe.get_doc("Email Provider", email_queue_doc.email_provider)
    else:
        # Get default provider
        providers = frappe.get_all(
            "Email Provider",
            filters={"is_active": 1},
            limit=1
        )
        
        if not providers:
            frappe.log_error(
                message="No active email providers found",
                title="Email Distribution Error"
            )
            return
        
        provider = frappe.get_doc("Email Provider", providers[0].name)
        email_queue_doc.email_provider = provider.name
    
    # Get next available account
    account = provider.get_next_available_account(email_queue_doc.contact)
    
    if not account:
        frappe.log_error(
            message=f"No available email accounts found for provider {provider.name}",
            title="Email Distribution Error"
        )
        return
    
    # Assign account to email queue
    email_queue_doc.email_account = account.name
    
    # Create sender assignment
    from outreach_app.outreach_app.doctype.sender_assignment.sender_assignment import SenderAssignment
    SenderAssignment.create_assignment(
        email_queue_doc.contact,
        account.name,
        provider.name,
        email_queue_doc.campaign
    )

def get_least_used_provider():
    """
    Get the provider with the least usage relative to its limits
    Returns the provider document or None
    """
    providers = frappe.get_all(
        "Email Provider",
        filters={"is_active": 1},
        fields=["name"]
    )
    
    if not providers:
        return None
    
    # Calculate usage ratio for each provider
    provider_usage = []
    for provider_data in providers:
        provider = frappe.get_doc("Email Provider", provider_data.name)
        
        # Get all accounts for this provider
        accounts = provider.get_available_accounts()
        
        if not accounts:
            continue
        
        # Calculate total daily usage and limits
        total_daily_count = sum(account.daily_count for account in accounts)
        total_daily_limit = sum(account.daily_limit for account in accounts)
        
        # Avoid division by zero
        if total_daily_limit == 0:
            usage_ratio = 1.0
        else:
            usage_ratio = float(total_daily_count) / float(total_daily_limit)
        
        provider_usage.append({
            "provider": provider,
            "usage_ratio": usage_ratio
        })
    
    if not provider_usage:
        return None
    
    # Sort by usage ratio (ascending)
    provider_usage.sort(key=lambda x: x["usage_ratio"])
    
    return provider_usage[0]["provider"]

def get_optimal_account_for_contact(contact, campaign=None):
    """
    Get the optimal email account for a contact
    First checks for existing assignment, then tries to find the best available account
    Returns the account document or None
    """
    # Check if contact already has a sender assignment
    from outreach_app.outreach_app.doctype.sender_assignment.sender_assignment import SenderAssignment
    
    assignment = SenderAssignment.get_assignment_for_contact(contact)
    
    if assignment:
        # Check if the assigned account is still available
        account = frappe.get_doc("Email Account", assignment.email_account)
        if (account.is_active and 
            account.daily_count < account.daily_limit and 
            account.hourly_count < account.hourly_limit):
            return account
        else:
            # Deactivate the assignment since the account is no longer available
            assignment.is_active = 0
            assignment.save()
    
    # Get the provider with the least usage
    provider = get_least_used_provider()
    
    if not provider:
        return None
    
    # Get the next available account from this provider
    account = provider.get_next_available_account(contact)
    
    if account:
        # Create a new assignment
        SenderAssignment.create_assignment(
            contact,
            account.name,
            provider.name,
            campaign
        )
    
    return account

def calculate_next_send_time(email_provider=None, last_send_time=None):
    """
    Calculate the next time an email can be sent based on provider settings
    If email_provider is not provided, use the default provider
    If last_send_time is not provided, use current time
    """
    if not email_provider:
        providers = frappe.get_all(
            "Email Provider",
            filters={"is_active": 1},
            limit=1
        )
        
        if not providers:
            # Use default values if no provider is found
            min_interval = 60
            max_interval = 300
            use_random = True
        else:
            provider = frappe.get_doc("Email Provider", providers[0].name)
            min_interval = provider.min_interval_seconds
            max_interval = provider.max_interval_seconds
            use_random = provider.enable_random_intervals
    else:
        provider = frappe.get_doc("Email Provider", email_provider)
        min_interval = provider.min_interval_seconds
        max_interval = provider.max_interval_seconds
        use_random = provider.enable_random_intervals
    
    if not last_send_time:
        last_send_time = now_datetime()
    
    if use_random:
        # Use a random interval between min and max
        interval_seconds = random.randint(min_interval, max_interval)
    else:
        # Use the minimum interval
        interval_seconds = min_interval
    
    next_send_time = add_to_date(last_send_time, seconds=interval_seconds)
    return next_send_time

def calculate_natural_send_time(email_provider=None):
    """
    Calculate a natural-looking send time to make emails appear more human
    Avoids sending at exact intervals and adds some randomness
    """
    # Get current time
    current_time = now_datetime()
    
    # Add a small random delay (5-30 seconds) to make it look more natural
    natural_delay = random.randint(5, 30)
    
    # Calculate the next send time based on provider settings
    next_time = calculate_next_send_time(email_provider, current_time)
    
    # Add the natural delay
    natural_time = add_to_date(next_time, seconds=natural_delay)
    
    return natural_time

def check_daily_limits_reached(provider_name=None):
    """
    Check if daily limits have been reached for a provider or all providers
    Returns True if limits reached, False otherwise
    """
    if provider_name:
        # Check specific provider
        provider = frappe.get_doc("Email Provider", provider_name)
        accounts = provider.get_available_accounts()
        
        if not accounts:
            return True
        
        # Check if any account is available
        for account in accounts:
            if account.daily_count < account.daily_limit:
                return False
        
        # All accounts have reached their limits
        return True
    else:
        # Check all providers
        providers = frappe.get_all(
            "Email Provider",
            filters={"is_active": 1},
            fields=["name"]
        )
        
        if not providers:
            return True
        
        for provider_data in providers:
            if not check_daily_limits_reached(provider_data.name):
                return False
        
        # All providers have reached their limits
        return True

def distribute_emails_for_campaign(campaign, limit=100):
    """
    Distribute emails for a campaign
    Creates email queue entries for contacts in the campaign
    Respects daily limits and sender consistency
    Returns the number of emails queued
    """
    if not frappe.db.exists("Campaign", campaign):
        frappe.throw(f"Campaign {campaign} does not exist")
    
    # Get campaign contacts that are ready for the next email
    campaign_contacts = frappe.get_all(
        "Campaign Contact",
        filters={
            "campaign": campaign,
            "status": ["in", ["Pending", "In Progress"]],
            "next_message_date": ["<=", now_datetime()]
        },
        fields=["name", "contact", "current_step", "next_message_date"],
        limit=limit
    )
    
    if not campaign_contacts:
        return 0
    
    # Check if daily limits have been reached
    if check_daily_limits_reached():
        frappe.log_error(
            message=f"Daily email limits reached for all providers",
            title="Email Distribution Error"
        )
        return 0
    
    emails_queued = 0
    
    for campaign_contact in campaign_contacts:
        # Get contact details
        contact = frappe.get_doc("Contact", campaign_contact.contact)
        
        # Get campaign step
        campaign_step = frappe.get_doc("Campaign Step", campaign_contact.current_step)
        
        # Get message template
        template = frappe.get_doc("Message Template", campaign_step.message_template)
        
        # Get the optimal account for this contact
        account = get_optimal_account_for_contact(contact.name, campaign)
        
        if not account:
            frappe.log_error(
                message=f"No available email account found for contact {contact.name}",
                title="Email Distribution Error"
            )
            continue
        
        # Get provider
        provider = frappe.get_doc("Email Provider", account.parent)
        
        # Calculate natural send time
        send_time = calculate_natural_send_time(provider.name)
        
        # Create personalized message
        subject, message = personalize_message(template, contact)
        
        # Create email queue entry
        email_queue = frappe.get_doc({
            "doctype": "Email Queue",
            "status": "Scheduled",
            "priority": "Medium",
            "scheduled_time": send_time,
            "recipient": contact.full_name,
            "recipient_email": contact.email_id,
            "contact": contact.name,
            "campaign": campaign,
            "campaign_step": campaign_step.name,
            "email_provider": provider.name,
            "email_account": account.name,
            "subject": subject,
            "message": message
        })
        
        email_queue.insert()
        emails_queued += 1
        
        # Update campaign contact
        update_campaign_contact(campaign_contact.name, campaign_step)
    
    return emails_queued

def personalize_message(template, contact):
    """
    Personalize a message template for a contact
    Returns the personalized subject and message
    """
    subject = template.subject
    message = template.body
    
    # Basic personalization variables
    variables = {
        "first_name": contact.first_name or "",
        "last_name": contact.last_name or "",
        "full_name": contact.full_name or "",
        "email": contact.email_id or "",
        "company": contact.company_name or ""
    }
    
    # Replace variables in subject and message
    for var_name, var_value in variables.items():
        subject = subject.replace(f"{{{var_name}}}", var_value)
        message = message.replace(f"{{{var_name}}}", var_value)
    
    return subject, message

def update_campaign_contact(campaign_contact_name, current_step):
    """
    Update a campaign contact after queuing an email
    Sets the next message date and updates the current step if needed
    """
    campaign_contact = frappe.get_doc("Campaign Contact", campaign_contact_name)
    
    # Get the campaign sequence
    campaign = frappe.get_doc("Campaign", campaign_contact.campaign)
    sequence = frappe.get_doc("Campaign Sequence", campaign.sequence)
    
    # Find the next step
    next_step = None
    found_current = False
    
    for step in sequence.steps:
        if found_current:
            next_step = step
            break
        
        if step.name == current_step.name:
            found_current = True
    
    # Update campaign contact
    if next_step:
        # Calculate next message date based on delay
        next_date = add_to_date(now_datetime(), days=cint(next_step.delay_days))
        
        campaign_contact.current_step = next_step.name
        campaign_contact.next_message_date = next_date
        campaign_contact.status = "In Progress"
    else:
        # No more steps, mark as completed
        campaign_contact.status = "Completed"
    
    campaign_contact.last_message_date = now_datetime()
    campaign_contact.save()

def reset_daily_counters():
    """
    Reset daily counters for all email accounts
    This function is called daily via scheduler
    """
    providers = frappe.get_all("Email Provider")
    
    for provider_data in providers:
        provider = frappe.get_doc("Email Provider", provider_data.name)
        provider.reset_daily_counters()
        
    frappe.db.commit()
    frappe.log_error(
        message="Daily email counters have been reset",
        title="Email Counter Reset"
    )

def reset_hourly_counters():
    """
    Reset hourly counters for all email accounts
    This function is called hourly via scheduler
    """
    providers = frappe.get_all("Email Provider")
    
    for provider_data in providers:
        provider = frappe.get_doc("Email Provider", provider_data.name)
        provider.reset_hourly_counters()
        
    frappe.db.commit()
