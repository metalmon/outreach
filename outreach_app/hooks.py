
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "outreach_app"
app_title = "Outreach App"
app_publisher = "Your Company"
app_description = "Email outreach application with email pool management"
app_icon = "octicon octicon-mail"
app_color = "blue"
app_email = "your.email@example.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/outreach_app/css/outreach_app.css"
# app_include_js = "/assets/outreach_app/js/outreach_app.js"

# include js, css files in header of web template
# web_include_css = "/assets/outreach_app/css/outreach_app.css"
# web_include_js = "/assets/outreach_app/js/outreach_app.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#   "Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "outreach_app.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "outreach_app.install.before_install"
# after_install = "outreach_app.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "outreach_app.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#   "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#   "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Email Queue": {
        "before_insert": "outreach_app.utils.email_distribution.assign_sender",
    }
}

# Scheduled Tasks
# ---------------


scheduler_events = {
    "all": [
        "outreach_app.outreach_app.doctype.email_queue.email_queue.process_queue"
    ],
    "hourly": [
        "outreach_app.utils.email_distribution.reset_hourly_counters"
    ],

    "daily": [
        "outreach_app.utils.email_distribution.reset_daily_counters",
        "outreach_app.outreach_app.doctype.email_queue.email_queue.clear_old_emails"
    ],
    "cron": {
        # Run campaign email distribution every 15 minutes
        "*/15 * * * *": [
            "outreach_app.utils.email_distribution.distribute_emails_for_campaign"
        ]
    }
}
    
    

# Testing
# -------

# before_tests = "outreach_app.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#   "frappe.desk.doctype.event.event.get_events": "outreach_app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#   "Task": "outreach_app.task.get_dashboard_data"
# }


