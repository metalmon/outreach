# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class SenderAssignment(Document):
    def validate(self):
        """Validate sender assignment"""
        # Check if contact exists
        if not frappe.db.exists("Contact", self.contact):
            frappe.throw(f"Contact {self.contact} does not exist")
        
        # Check if email account exists
        if not frappe.db.exists("Email Account", self.email_account):
            frappe.throw(f"Email Account {self.email_account} does not exist")
        
        # Check if email provider exists
        if not frappe.db.exists("Email Provider", self.email_provider):
            frappe.throw(f"Email Provider {self.email_provider} does not exist")
        
        # Check if there's already an active assignment for this contact
        if not self.is_new():
            existing = frappe.get_all(
                "Sender Assignment",
                filters={
                    "contact": self.contact,
                    "is_active": 1,
                    "name": ["!=", self.name]
                },
                fields=["name"]
            )
            
            if existing and self.is_active:
                # Deactivate other assignments
                for assignment in existing:
                    doc = frappe.get_doc("Sender Assignment", assignment.name)
                    doc.is_active = 0
                    doc.save()
    
    def update_email_sent(self, campaign=None):
        """
        Update the last email sent timestamp and counter
        Optionally update the campaign reference
        """
        self.last_email_sent = now_datetime()
        self.total_emails_sent += 1
        
        if campaign and not self.campaign:
            self.campaign = campaign
        
        self.save()
    
    @staticmethod
    def get_assignment_for_contact(contact):
        """
        Get the active sender assignment for a contact
        Returns the SenderAssignment document or None
        """
        assignments = frappe.get_all(
            "Sender Assignment",
            filters={
                "contact": contact,
                "is_active": 1
            },
            fields=["name"],
            limit=1
        )
        
        if assignments:
            return frappe.get_doc("Sender Assignment", assignments[0].name)
        
        return None
    
    @staticmethod
    def create_assignment(contact, email_account, email_provider, campaign=None):
        """
        Create a new sender assignment
        """
        # Deactivate any existing assignments
        existing = frappe.get_all(
            "Sender Assignment",
            filters={
                "contact": contact,
                "is_active": 1
            },
            fields=["name"]
        )
        
        for assignment in existing:
            doc = frappe.get_doc("Sender Assignment", assignment.name)
            doc.is_active = 0
            doc.save()
        
        # Create new assignment
        assignment = frappe.get_doc({
            "doctype": "Sender Assignment",
            "contact": contact,
            "email_account": email_account,
            "email_provider": email_provider,
            "assigned_date": now_datetime(),
            "is_active": 1,
            "campaign": campaign,
            "total_emails_sent": 0
        })
        
        assignment.insert()
        return assignment
