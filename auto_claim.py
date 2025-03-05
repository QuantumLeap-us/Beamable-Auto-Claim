#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import logging
import requests
import schedule
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Create custom log formatter to display UTC time
class UTCFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, timezone.utc)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("auto_claim.log"),
        logging.StreamHandler()
    ]
)
# Set custom formatter
formatter = UTCFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
for handler in logging.root.handlers:
    handler.setFormatter(formatter)

logger = logging.getLogger("AutoClaim")

# Load environment variables
load_dotenv()

# Get Cookie from environment variables, use default if not found
COOKIE = os.getenv('BEAMABLE_COOKIE', 'wagmi.store={"state":{"connections":{"__type":"Map","value":[]},"chainId":1,"current":null},"version":2}; harbor-session=s%3A8ab0da30-cd82-421b-892b-0c7be8f50387.j5UHeKRd1jsBBlJFYPfPlSgmgXWLJNbPyEanT1%2BqsNA; _ga=GA1.1.1722330049.1741135732; _ga_198F67P74H=GS1.1.1741135732.1.1.1741138724.0.0.0; _ga_GNVVWBL3J9=GS1.1.1741135734.1.1.1741138724.0.0.0')

# Website URLs
BEAMABLE_URL = "https://hub.beamable.network/modules/preregclaim"
BEAMABLE_API_URL = "https://hub.beamable.network/api/claim"

def get_cookies_dict():
    """Convert cookie string to dictionary"""
    cookies = {}
    for item in COOKIE.split(';'):
        if '=' in item:
            key, value = item.strip().split('=', 1)
            cookies[key] = value
    return cookies

def get_headers():
    """Get request headers"""
    return {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "referer": BEAMABLE_URL
    }

def perform_claim():
    """Perform claim operation"""
    try:
        logger.info("Starting claim operation...")
        
        # Get page content
        logger.info("Getting page content...")
        cookies = get_cookies_dict()
        headers = get_headers()
        
        try:
            # First get page content to check if already claimed and countdown info
            response = requests.get(
                BEAMABLE_URL,
                headers=headers,
                cookies=cookies,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get page! Status code: {response.status_code}")
                return False
            
            page_content = response.text
            
            # Check if already claimed
            if "ITEM CLAIMED" in page_content:
                logger.info("Item has already been claimed")
                
                # Try to parse countdown
                next_claim_time = parse_countdown(page_content)
                if next_claim_time:
                    # Cancel all previous scheduled tasks
                    schedule.clear()
                    # Set new scheduled task
                    schedule_next_claim(next_claim_time)
                    return True
            else:
                # If not claimed, try to perform claim operation
                logger.info("Attempting to perform claim operation...")
                
                # Send claim request
                claim_response = requests.post(
                    BEAMABLE_API_URL,
                    headers=headers,
                    cookies=cookies,
                    json={"type": "daily"},
                    timeout=10
                )
                
                if claim_response.status_code == 200:
                    logger.info("Claim successful!")
                    
                    # Get page again to parse next claim time
                    response = requests.get(
                        BEAMABLE_URL,
                        headers=headers,
                        cookies=cookies,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        next_claim_time = parse_countdown(response.text)
                        if next_claim_time:
                            # Cancel all previous scheduled tasks
                            schedule.clear()
                            # Set new scheduled task
                            schedule_next_claim(next_claim_time)
                            return True
                else:
                    logger.error(f"Claim request failed! Status code: {claim_response.status_code}")
                    logger.error(f"Response content: {claim_response.text}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {str(e)}")
        
        # If all above steps failed, use default scheduling strategy
        logger.info("Unable to get accurate next claim time, using default time")
        schedule_default_claim()
        return False
            
    except Exception as e:
        logger.error(f"Error during claim operation: {str(e)}")
        return False

def parse_countdown(html_content):
    """Parse countdown from HTML content"""
    try:
        # Try to find time after "Time to Claim:"
        # Format 1: Numbers displayed in hours and minutes divs
        hours_pattern = re.search(r'<div[^>]*>(\d+)</div>\s*<div[^>]*>HOURS</div>', html_content, re.IGNORECASE)
        minutes_pattern = re.search(r'<div[^>]*>(\d+)</div>\s*<div[^>]*>MINUTES</div>', html_content, re.IGNORECASE)
        
        if hours_pattern and minutes_pattern:
            hours = int(hours_pattern.group(1))
            minutes = int(minutes_pattern.group(1))
            
            # Calculate next claim time using UTC time
            now = datetime.now(timezone.utc)
            next_time = now + timedelta(hours=hours, minutes=minutes)
            
            logger.info(f"Parsed next claim time from page: {hours} hours {minutes} minutes later (UTC: {next_time.strftime('%Y-%m-%d %H:%M:%S')})")
            return next_time
        
        # Format 2: "Time to Claim: XX : YY"
        time_pattern = re.search(r'Time to Claim:.*?(\d+)\s*:\s*(\d+)', html_content, re.IGNORECASE | re.DOTALL)
        
        if time_pattern:
            hours = int(time_pattern.group(1))
            minutes = int(time_pattern.group(2))
            
            # Calculate next claim time using UTC time
            now = datetime.now(timezone.utc)
            next_time = now + timedelta(hours=hours, minutes=minutes)
            
            logger.info(f"Parsed next claim time from page: {hours} hours {minutes} minutes later (UTC: {next_time.strftime('%Y-%m-%d %H:%M:%S')})")
            return next_time
            
        # If already claimed but can't parse countdown, default to 12 hours later
        if "ITEM CLAIMED" in html_content:
            now = datetime.now(timezone.utc)
            next_time = now + timedelta(hours=12)
            logger.info(f"Item claimed but couldn't parse countdown, setting next claim time to 12 hours later (UTC: {next_time.strftime('%Y-%m-%d %H:%M:%S')})")
            return next_time
            
    except Exception as e:
        logger.error(f"Error parsing countdown: {str(e)}")
    
    return None

def schedule_next_claim(next_time):
    """Schedule next claim based on parsed next claim time"""
    # Calculate time until next claim (in seconds)
    now = datetime.now(timezone.utc)
    
    # Ensure claim is performed before UTC 23:30 of the current day (30 minutes buffer)
    today_deadline = now.replace(hour=23, minute=30, second=0, microsecond=0)
    
    # If parsed next claim time exceeds today's deadline, use today's deadline
    if next_time.date() == now.date() and next_time > today_deadline:
        next_time = today_deadline
        logger.info(f"Next claim time exceeds today's deadline, adjusted to today's UTC 23:30")
    # If parsed next claim time is tomorrow or later, use today's deadline
    elif next_time.date() > now.date():
        next_time = today_deadline
        logger.info(f"Next claim time is tomorrow or later, adjusted to today's UTC 23:30")
    
    seconds_until_next = (next_time - now).total_seconds()
    
    # Ensure time is positive
    if seconds_until_next <= 0:
        logger.warning("Calculated next claim time has already passed, using default time")
        schedule_default_claim()
        return
    
    # Set one-time task
    logger.info(f"Setting next claim time: UTC {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
    schedule.every(int(seconds_until_next)).seconds.do(claim_and_reschedule).tag('claim')

def claim_and_reschedule():
    """Perform claim and reschedule next task"""
    # Perform claim
    perform_claim()
    # Clear current task (as it's a one-time task)
    schedule.clear('claim')

def schedule_default_claim():
    """Set default claim time (every 12 hours)"""
    now = datetime.now(timezone.utc)
    today_deadline = now.replace(hour=23, minute=30, second=0, microsecond=0)
    
    # If current time is past today's deadline, set to same time tomorrow
    if now > today_deadline:
        next_time = (now + timedelta(days=1)).replace(hour=23, minute=30, second=0, microsecond=0)
    else:
        # If less than 12 hours until today's deadline, use today's deadline
        if (today_deadline - now).total_seconds() < 12 * 3600:
            next_time = today_deadline
        else:
            # Otherwise use 12 hours later, but not exceeding today's deadline
            next_time = min(now + timedelta(hours=12), today_deadline)
    
    seconds_until_next = (next_time - now).total_seconds()
    logger.info(f"Setting default claim time: UTC {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
    schedule.every(int(seconds_until_next)).seconds.do(claim_and_reschedule).tag('claim')

def run_pending_tasks():
    """Run pending tasks"""
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def calculate_time_until_next_run():
    """Calculate time until next run"""
    next_run = schedule.next_run()
    if next_run:
        # Convert next_run to timezone-aware object for comparison with current UTC time
        if next_run.tzinfo is None:
            next_run = next_run.replace(tzinfo=timezone.utc)
        
        time_diff = next_run - datetime.now(timezone.utc)
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} hours {minutes} minutes {seconds} seconds"
    return "unknown"

if __name__ == "__main__":
    logger.info("Auto Claim program started")
    
    # Perform claim operation immediately
    logger.info("Performing initial claim operation")
    perform_claim()
    
    # If no tasks are set (possibly because perform_claim failed to parse next time)
    if len(schedule.get_jobs()) == 0:
        logger.info("No tasks set, using default time")
        schedule_default_claim()
    
    # Display time until next run
    next_run_time = calculate_time_until_next_run()
    logger.info(f"Next claim will be performed in {next_run_time}")
    
    # Run scheduled tasks
    try:
        run_pending_tasks()
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Program terminated abnormally: {str(e)}") 