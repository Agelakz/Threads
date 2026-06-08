import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration for Threads Affiliate Intelligence System."""
    
    # Gemini AI Configuration
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    
    # Threads Configuration
    THREADS_USERNAME = os.environ.get("THREADS_USERNAME", "")
    THREADS_PASSWORD = os.environ.get("THREADS_PASSWORD", "")
    
    # Shopee Affiliate Configuration
    SHOPEE_AFFILIATE_USERNAME = os.environ.get("SHOPEE_AFFILIATE_USERNAME", "")
    SHOPEE_AFFILIATE_PASSWORD = os.environ.get("SHOPEE_AFFILIATE_PASSWORD", "")
    
    # Database Configuration
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///database.db")
    
    # Flask Configuration
    FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

# Select config based on environment
ENV = os.environ.get("FLASK_ENV", "development")
config = DevelopmentConfig if ENV == "development" else ProductionConfig
