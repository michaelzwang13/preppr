import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "a-default-secret-key-for-development")

    # Database configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 8889))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
    DB_NAME = os.getenv("DB_NAME", "hacknyu25")

    # Nutritionix API configuration
    NUTRITIONIX_API_ID = os.getenv("NUTRITIONIX_API_ID")
    NUTRITIONIX_API_KEY = os.getenv("NUTRITIONIX_API_KEY")

    # Gemini AI configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # JWT configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)  # Fallback to main secret key
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))  # 1 hour default
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 2592000))  # 30 days default
    
    # Security configuration
    BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", 12))  # Stronger default rounds
