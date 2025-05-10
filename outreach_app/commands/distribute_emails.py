
# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import click
from frappe.commands.utils import pass_context
from frappe.utils import now_datetime

@click.command('distribute-emails')
@click.option('--campaign', help='Campaign name to distribute emails for')
@click.option('--limit', default=100, help='Maximum number of emails to distribute')
@click.option('--force', is_flag=True, help='Force distribution even if daily limits are reached')
@pass_context
def distribute_emails(context, campaign=None, limit=100, force=False):
    """Distribute emails for a campaign or all active campaigns"""
    from outreach_app.outreach_app.utils.email_distribution import distribute_emails_for_campaign, check_daily_limits_reached
    
    with frappe.init_site(context.sites[0]):
        frappe.connect()
        
        if not force and check_daily_limits_reached():
            click.echo("Daily email limits reached for all providers. Use --force to override.")
            return
        
        if campaign:
            # Distribute emails for specific campaign
            if not frappe.db.exists("Campaign", campaign):
                click.echo(f"Campaign {campaign} does not exist")
                return
            
            count = distribute_emails_for_campaign(campaign, limit)
            click.echo(f"Distributed {count} emails for campaign {campaign}")
        else:
            # Distribute emails for all active campaigns
            campaigns = frappe.get_all(
                "Campaign",
                filters={"status": "Active"},
                fields=["name"]
            )
            
            if not campaigns:
                click.echo("No active campaigns found")
                return
            
            total_count = 0
            for campaign_data in campaigns:
                count = distribute_emails_for_campaign(campaign_data.name, limit)
                total_count += count
                click.echo(f"Distributed {count} emails for campaign {campaign_data.name}")
            
            click.echo(f"Total emails distributed: {total_count}")
        
        frappe.db.commit()

commands = [
    distribute_emails
]
