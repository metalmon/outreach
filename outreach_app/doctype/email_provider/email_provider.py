# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import random
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, time_diff_in_seconds

class EmailProvider(Document):
    def validate(self):
        """Validate provider settings"""
        if self.min_interval_seconds > self.max_interval_seconds:
            frappe.throw("Minimum interval cannot be greater than maximum interval")
        
        if self.daily_email_limit <= 0:
            frappe.throw("Daily email limit must be greater than zero")
        
        if self.hourly_email_limit <= 0:
            frappe.throw("Hourly email limit must be greater than zero")
        
        if self.hourly_email_limit > self.daily_email_limit:
            frappe.throw("Hourly email limit cannot be greater than daily email limit")
    
    def get_available_accounts(self):
        """Get all available and active email accounts in this provider"""
        if not self.email_accounts:
            return []
        
        # Get all email accounts linked to this provider
        email_accounts = frappe.get_all(
            "Email Account",
            filters={
                "parent": self.name,
                "parenttype": "Email Provider",
                "is_active": 1
            },
            fields=["name", "email", "daily_limit", "hourly_limit", "daily_count", "hourly_count", "last_used"]
        )
        
        return email_accounts
    
    def get_next_available_account(self, contact=None):
        """
        Get the next available email account for sending
        If contact is provided, try to use the same account previously assigned to this contact
        """
        # First check if contact has a previous sender assignment
        if contact:
            sender_assignment = frappe.get_all(
                "Sender Assignment",
                filters={
                    "contact": contact,
                    "is_active": 1
                },
                fields=["email_account"],
                limit=1
            )
            
            if sender_assignment:
                # Check if the assigned account is still available
                account = frappe.get_doc("Email Account", sender_assignment[0].email_account)
                if (account.is_active and 
                    account.daily_count < account.daily_limit and 
                    account.hourly_count < account.hourly_limit):
                    return account
        
        # Get all available accounts
        available_accounts = self.get_available_accounts()
        
        if not available_accounts:
            frappe.log_error(
                message=f"No available email accounts found for provider {self.name}",
                title="Email Provider Error"
            )
            return None
        
        # Filter accounts that haven't reached their limits
        available_accounts = [
            account for account in available_accounts 
            if account.daily_count < account.daily_limit and account.hourly_count < account.hourly_limit
        ]
        
        if not available_accounts:
            frappe.log_error(
                message=f"All email accounts for provider {self.name} have reached their sending limits",
                title="Email Provider Error"
            )
            return None
        
        # Sort by last used time (oldest first) to distribute load
        available_accounts.sort(key=lambda x: get_datetime(x.last_used) if x.last_used else get_datetime("1900-01-01"))
        
        # If auto rotation is enabled, use the account that was used least recently
        if self.enable_auto_rotation:
            return frappe.get_doc("Email Account", available_accounts[0].name)
        
        # Otherwise, randomly select an account from the available ones
        selected_account = random.choice(available_accounts)
        return frappe.get_doc("Email Account", selected_account.name)
    
    def get_next_send_time(self, last_send_time=None):
        """
        Calculate the next time an email can be sent based on interval settings
        If last_send_time is not provided, use current time
        """
        if not last_send_time:
            last_send_time = now_datetime()
        
        if self.enable_random_intervals:
            # Use a random interval between min and max
            interval_seconds = random.randint(self.min_interval_seconds, self.max_interval_seconds)
        else:
            # Use the minimum interval
            interval_seconds = self.min_interval_seconds
        
        next_send_time = get_datetime(last_send_time).add(seconds=interval_seconds)
        return next_send_time
    
    def assign_account_to_contact(self, contact, email_account):
        """
        Assign an email account to a contact for consistent sending
        """
        # Check if an assignment already exists
        existing_assignment = frappe.get_all(
            "Sender Assignment",
            filters={
                "contact": contact,
                "is_active": 1
            },
            fields=["name"],
            limit=1
        )
        
        if existing_assignment:
            # Update existing assignment
            assignment = frappe.get_doc("Sender Assignment", existing_assignment[0].name)
            assignment.email_account = email_account.name
            assignment.email_provider = self.name
            assignment.save()
            return assignment
        else:
            # Create new assignment
            assignment = frappe.get_doc({
                "doctype": "Sender Assignment",
                "contact": contact,
                "email_account": email_account.name,
                "email_provider": self.name,
                "assigned_date": now_datetime(),
                "is_active": 1
            })
            assignment.insert()
            return assignment
    
    def update_account_usage(self, email_account):
        """
        Update usage counters for an email account after sending
        """
        account = frappe.get_doc("Email Account", email_account)
        account.daily_count += 1
        account.hourly_count += 1
        account.last_used = now_datetime()
        account.save()
        
        # Check if account has reached its limits
        if account.daily_count >= account.daily_limit:
            frappe.log_error(
                message=f"Email account {account.email} has reached its daily sending limit",
                title="Email Account Limit Reached"
            )
        
        if account.hourly_count >= account.hourly_limit:
            frappe.log_error(
                message=f"Email account {account.email} has reached its hourly sending limit",
                title="Email Account Limit Reached"
            )
    
    def reset_hourly_counters(self):
        """
        Reset hourly counters for all email accounts in this provider
        """
        for account_data in self.email_accounts:
            account = frappe.get_doc("Email Account", account_data.name)
            account.hourly_count = 0
            account.save()
    
    def reset_daily_counters(self):
        """
        Reset daily counters for all email accounts in this provider
        """
        for account_data in self.email_accounts:
            account = frappe.get_doc("Email Account", account_data.name)
            account.daily_count = 0
            account.hourly_count = 0
            account.save()
