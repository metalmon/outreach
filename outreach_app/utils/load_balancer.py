
# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import random
from frappe.utils import now_datetime, get_datetime, time_diff_in_seconds

def get_provider_load_stats():
    """
    Get load statistics for all active email providers
    Returns a list of providers with their usage statistics
    """
    providers = frappe.get_all(
        "Email Provider",
        filters={"is_active": 1},
        fields=["name"]
    )
    
    if not providers:
        return []
    
    provider_stats = []
    
    for provider_data in providers:
        provider = frappe.get_doc("Email Provider", provider_data.name)
        
        # Get all accounts for this provider
        accounts = provider.get_available_accounts()
        
        if not accounts:
            continue
        
        # Calculate total daily and hourly usage and limits
        total_daily_count = sum(account.daily_count for account in accounts)
        total_daily_limit = sum(account.daily_limit for account in accounts)
        total_hourly_count = sum(account.hourly_count for account in accounts)
        total_hourly_limit = sum(account.hourly_limit for account in accounts)
        
        # Calculate usage ratios
        daily_ratio = float(total_daily_count) / float(total_daily_limit) if total_daily_limit > 0 else 1.0
        hourly_ratio = float(total_hourly_count) / float(total_hourly_limit) if total_hourly_limit > 0 else 1.0
        
        # Count available accounts (not at limit)
        available_accounts = sum(1 for account in accounts 
                               if account.daily_count < account.daily_limit and 
                                  account.hourly_count < account.hourly_limit)
        
        provider_stats.append({
            "provider": provider,
            "daily_count": total_daily_count,
            "daily_limit": total_daily_limit,
            "daily_ratio": daily_ratio,
            "hourly_count": total_hourly_count,
            "hourly_limit": total_hourly_limit,
            "hourly_ratio": hourly_ratio,
            "available_accounts": available_accounts,
            "total_accounts": len(accounts)
        })
    
    return provider_stats

def select_provider_weighted_random():
    """
    Select a provider using weighted random selection based on available capacity
    Providers with more available capacity have a higher chance of being selected
    Returns the provider document or None
    """
    provider_stats = get_provider_load_stats()
    
    if not provider_stats:
        return None
    
    # Filter providers that have available accounts
    available_providers = [p for p in provider_stats if p["available_accounts"] > 0]
    
    if not available_providers:
        return None
    
    # Calculate weights based on inverse of daily usage ratio
    # Lower usage ratio = higher weight
    weights = []
    for provider in available_providers:
        # Use inverse of daily ratio as weight (1 - ratio)
        # Add a small value to ensure even fully utilized providers have a small chance
        weight = max(0.05, 1.0 - provider["daily_ratio"])
        weights.append(weight)
    
    # Normalize weights
    total_weight = sum(weights)
    if total_weight > 0:
        weights = [w / total_weight for w in weights]
    
    # Select provider using weighted random
    selected_index = weighted_random_selection(weights)
    
    if selected_index is not None:
        return available_providers[selected_index]["provider"]
    
    # Fallback to least used provider
    available_providers.sort(key=lambda x: x["daily_ratio"])
    return available_providers[0]["provider"]

def weighted_random_selection(weights):
    """
    Select an index based on weights using weighted random selection
    Returns the selected index or None if weights is empty
    """
    if not weights:
        return None
    
    # Generate a random value between 0 and 1
    r = random.random()
    
    # Calculate cumulative weights
    cumulative_weights = []
    cumulative_sum = 0
    for weight in weights:
        cumulative_sum += weight
        cumulative_weights.append(cumulative_sum)
    
    # Find the index where the random value falls
    for i, cumulative_weight in enumerate(cumulative_weights):
        if r <= cumulative_weight:
            return i
    
    # Fallback to last index
    return len(weights) - 1

def get_account_load_stats(provider):
    """
    Get load statistics for all active email accounts in a provider
    Returns a list of accounts with their usage statistics
    """
    accounts = provider.get_available_accounts()
    
    if not accounts:
        return []
    
    account_stats = []
    
    for account in accounts:
        # Calculate usage ratios
        daily_ratio = float(account.daily_count) / float(account.daily_limit) if account.daily_limit > 0 else 1.0
        hourly_ratio = float(account.hourly_count) / float(account.hourly_limit) if account.hourly_limit > 0 else 1.0
        
        # Check if account is available
        is_available = (account.daily_count < account.daily_limit and 
                        account.hourly_count < account.hourly_limit)
        
        # Calculate time since last use
        last_used = get_datetime(account.last_used) if account.last_used else get_datetime("1900-01-01")
        seconds_since_last_use = time_diff_in_seconds(now_datetime(), last_used)
        
        account_stats.append({
            "account": account,
            "daily_count": account.daily_count,
            "daily_limit": account.daily_limit,
            "daily_ratio": daily_ratio,
            "hourly_count": account.hourly_count,
            "hourly_limit": account.hourly_limit,
            "hourly_ratio": hourly_ratio,
            "is_available": is_available,
            "last_used": last_used,
            "seconds_since_last_use": seconds_since_last_use
        })
    
    return account_stats

def select_account_from_provider(provider, contact=None):
    """
    Select an account from a provider based on load balancing strategy
    If contact is provided, try to use the same account previously assigned to this contact
    Returns the account document or None
    """
    # First check if contact has a previous sender assignment
    if contact:
        from outreach_app.outreach_app.doctype.sender_assignment.sender_assignment import SenderAssignment
        
        assignment = SenderAssignment.get_assignment_for_contact(contact)
        
        if assignment and assignment.email_provider == provider.name:
            # Check if the assigned account is still available
            account = frappe.get_doc("Email Account", assignment.email_account)
            if (account.is_active and 
                account.daily_count < account.daily_limit and 
                account.hourly_count < account.hourly_limit):
                return account
    
    # Get account statistics
    account_stats = get_account_load_stats(provider)
    
    if not account_stats:
        return None
    
    # Filter available accounts
    available_accounts = [a for a in account_stats if a["is_available"]]
    
    if not available_accounts:
        return None
    
    # If auto rotation is enabled, use the account that was used least recently
    if provider.enable_auto_rotation:
        available_accounts.sort(key=lambda x: x["seconds_since_last_use"], reverse=True)
        return available_accounts[0]["account"]
    
    # Calculate weights based on inverse of daily usage ratio and time since last use
    weights = []
    for account in available_accounts:
        # Use inverse of daily ratio as weight (1 - ratio)
        usage_weight = max(0.05, 1.0 - account["daily_ratio"])
        
        # Add weight for time since last use (normalized to max 1.0)
        time_weight = min(1.0, account["seconds_since_last_use"] / 3600.0)  # Max weight at 1 hour
        
        # Combine weights
        combined_weight = (usage_weight * 0.7) + (time_weight * 0.3)
        weights.append(combined_weight)
    
    # Select account using weighted random
    selected_index = weighted_random_selection(weights)
    
    if selected_index is not None:
        return available_accounts[selected_index]["account"]
    
    # Fallback to least used account
    available_accounts.sort(key=lambda x: x["daily_ratio"])
    return available_accounts[0]["account"]
