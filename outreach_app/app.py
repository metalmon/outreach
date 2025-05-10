
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

__version__ = '0.0.1'

app_name = "outreach_app"
app_title = "Outreach App"
app_publisher = "Your Company"
app_description = "Email outreach application with email pool management"
app_icon = "octicon octicon-mail"
app_color = "blue"
app_email = "your.email@example.com"
app_license = "MIT"

# Document Events
doc_events = {
    "Email Queue": {
        "before_insert": "outreach_app.outreach_app.utils.email_distribution.assign_sender",
    }
}

# Scheduled Tasks
scheduler_events = {
    "hourly": [
        "outreach_app.outreach_app.utils.email_distribution.reset_hourly_counters"
    ],
    "daily": [
        "outreach_app.outreach_app.utils.email_distribution.reset_daily_counters"
    ],
    "cron": {
        # Run campaign email distribution every 15 minutes
        "*/15 * * * *": [
            "outreach_app.outreach_app.utils.email_distribution.distribute_emails_for_campaign"
        ]
    }
}

# Website
website_route_rules = [
    # {"from_route": "/outreach", "to_route": "Outreach Dashboard"}
]

# Commands
from outreach_app.outreach_app.commands.distribute_emails import commands as distribute_commands

commands = distribute_commands
