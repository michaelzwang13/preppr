"""
Timezone utility functions for handling user-specific timezone conversions.
"""

from datetime import datetime, date
import pytz
from src.database import get_db
from src.logging_config import get_logger

logger = get_logger("preppr.timezone_utils")

def get_user_timezone(user_id: str) -> str:
    """
    Get the timezone for a specific user from the database.
    
    Args:
        user_id: The user's ID
        
    Returns:
        str: The user's timezone (defaults to UTC if not found)
    """
    try:
        connection = get_db()
        cursor = connection.cursor()
        
        cursor.execute(
            "SELECT timezone FROM user_account WHERE user_ID = %s",
            (user_id,)
        )
        
        result = cursor.fetchone()
        cursor.close()
        
        if result and result['timezone']:
            return result['timezone']
        else:
            logger.warning(f"No timezone found for user {user_id}, defaulting to UTC")
            return 'UTC'
            
    except Exception as e:
        logger.error(f"Error getting timezone for user {user_id}: {str(e)}")
        return 'UTC'

def get_user_current_date(user_id: str) -> date:
    """
    Get the current date in the user's timezone.
    
    Args:
        user_id: The user's ID
        
    Returns:
        date: Current date in user's timezone
    """
    try:
        user_timezone = get_user_timezone(user_id)
        tz = pytz.timezone(user_timezone)
        
        # Get current UTC time and convert to user's timezone
        utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        user_now = utc_now.astimezone(tz)
        
        return user_now.date()
        
    except Exception as e:
        logger.error(f"Error getting current date for user {user_id}: {str(e)}")
        # Fallback to UTC
        return datetime.utcnow().date()

def get_user_current_datetime(user_id: str) -> datetime:
    """
    Get the current datetime in the user's timezone.
    
    Args:
        user_id: The user's ID
        
    Returns:
        datetime: Current datetime in user's timezone
    """
    try:
        user_timezone = get_user_timezone(user_id)
        tz = pytz.timezone(user_timezone)
        
        # Get current UTC time and convert to user's timezone
        utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        user_now = utc_now.astimezone(tz)
        
        return user_now
        
    except Exception as e:
        logger.error(f"Error getting current datetime for user {user_id}: {str(e)}")
        # Fallback to UTC
        return datetime.utcnow().replace(tzinfo=pytz.UTC)


def get_timezone_display_name(timezone_str: str) -> str:
    """
    Get a human-readable display name for a timezone.
    
    Args:
        timezone_str: The timezone string (e.g., 'America/New_York')
        
    Returns:
        str: Human-readable timezone name
    """
    timezone_names = {
        'America/New_York': 'Eastern Time (New York)',
        'America/Chicago': 'Central Time (Chicago)',
        'America/Denver': 'Mountain Time (Denver)',
        'America/Los_Angeles': 'Pacific Time (Los Angeles)',
        'America/Anchorage': 'Alaska Time (Anchorage)',
        'Pacific/Honolulu': 'Hawaii Time (Honolulu)',
        'America/Toronto': 'Eastern Time (Toronto)',
        'America/Vancouver': 'Pacific Time (Vancouver)',
        'Europe/London': 'Greenwich Mean Time (London)',
        'Europe/Paris': 'Central European Time (Paris)',
        'Europe/Berlin': 'Central European Time (Berlin)',
        'Europe/Rome': 'Central European Time (Rome)',
        'Europe/Madrid': 'Central European Time (Madrid)',
        'Europe/Amsterdam': 'Central European Time (Amsterdam)',
        'Europe/Stockholm': 'Central European Time (Stockholm)',
        'Europe/Moscow': 'Moscow Time (Moscow)',
        'Asia/Tokyo': 'Japan Standard Time (Tokyo)',
        'Asia/Shanghai': 'China Standard Time (Shanghai)',
        'Asia/Seoul': 'Korea Standard Time (Seoul)',
        'Asia/Hong_Kong': 'Hong Kong Time (Hong Kong)',
        'Asia/Singapore': 'Singapore Standard Time (Singapore)',
        'Asia/Dubai': 'Gulf Standard Time (Dubai)',
        'Asia/Kolkata': 'India Standard Time (Mumbai)',
        'Asia/Bangkok': 'Indochina Time (Bangkok)',
        'Australia/Sydney': 'Australian Eastern Time (Sydney)',
        'Australia/Melbourne': 'Australian Eastern Time (Melbourne)',
        'Australia/Perth': 'Australian Western Time (Perth)',
        'Pacific/Auckland': 'New Zealand Standard Time (Auckland)',
        'UTC': 'Coordinated Universal Time (UTC)'
    }
    
    return timezone_names.get(timezone_str, timezone_str)