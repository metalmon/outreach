# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from frappe.model.document import Document

class EmailAccount(Document):
    def validate(self):
        """Validate email account settings"""
        if self.daily_limit <= 0:
            frappe.throw("Daily limit must be greater than zero")
        
        if self.hourly_limit <= 0:
            frappe.throw("Hourly limit must be greater than zero")
        
        if self.hourly_limit > self.daily_limit:
            frappe.throw("Hourly limit cannot be greater than daily limit")
    
    def test_connection(self):
        """Test SMTP connection to verify credentials"""
        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            server.login(self.username, self.get_password())
            server.quit()
            
            self.status = "Active"
            return True
        except Exception as e:
            self.status = "Error"
            frappe.log_error(
                message=f"SMTP connection test failed for {self.email}: {str(e)}",
                title="Email Account Connection Test Failed"
            )
            return False
    
    def get_password(self):
        """Get decrypted password"""
        return frappe.utils.password.get_decrypted_password(
            "Email Account", self.name, "password"
        )
    
    def send_email(self, to_email, subject, message, html_message=None, attachments=None):
        """
        Send an email using this account
        Returns: success (bool), error_message (str)
        """
        if not self.is_active:
            return False, "Email account is not active"
        
        if self.status != "Active":
            return False, f"Email account status is {self.status}"
        
        if self.daily_count >= self.daily_limit:
            return False, "Daily sending limit reached"
        
        if self.hourly_count >= self.hourly_limit:
            return False, "Hourly sending limit reached"
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach text part
            msg.attach(MIMEText(message, 'plain'))
            
            # Attach HTML part if provided
            if html_message:
                msg.attach(MIMEText(html_message, 'html'))
            
            # Connect to SMTP server
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Login and send
            server.login(self.username, self.get_password())
            server.sendmail(self.email, to_email, msg.as_string())
            server.quit()
            
            # Update usage counters
            parent_provider = frappe.get_doc("Email Provider", self.parent)
            parent_provider.update_account_usage(self.name)
            
            return True, "Email sent successfully"
        
        except Exception as e:
            error_message = str(e)
            frappe.log_error(
                message=f"Failed to send email from {self.email}: {error_message}",
                title="Email Sending Failed"
            )
            
            # Update status if there's a connection issue
            if "Authentication" in error_message or "login" in error_message.lower():
                self.status = "Error"
                self.save()
            
            return False, error_message
