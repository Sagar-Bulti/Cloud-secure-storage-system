"""
MongoDB Atlas Database Connection Module
==========================================
Provides cloud database connectivity with automatic fallback to JSON files.

Features:
- MongoDB Atlas cloud integration
- Automatic connection pooling
- Graceful fallback to JSON storage
- Connection health monitoring
- Thread-safe operations
"""

import os
import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
USE_MONGODB = os.getenv("USE_MONGODB", "false").lower() == "true"
DB_NAME = "securecloud_db"

# Global MongoDB client
_mongo_client = None
_mongodb_available = False


def init_mongodb():
    """
    Initialize MongoDB connection with error handling.
    
    Returns:
        bool: True if MongoDB is available, False otherwise
    """
    global _mongo_client, _mongodb_available
    
    if not USE_MONGODB or not MONGODB_URI:
        print("ℹ️ MongoDB disabled or not configured - using JSON storage")
        _mongodb_available = False
        return False
    
    try:
        print("🔄 Connecting to MongoDB Atlas...")
        
        # Create MongoDB client with timeout settings
        _mongo_client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        
        # Test connection
        _mongo_client.admin.command('ping')
        
        _mongodb_available = True
        print("✅ MongoDB Atlas connected successfully!")
        print(f"📊 Database: {DB_NAME}")
        
        return True
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"⚠️ MongoDB connection failed: {e}")
        print("📁 Falling back to JSON file storage")
        _mongodb_available = False
        _mongo_client = None
        return False
    except Exception as e:
        print(f"❌ Unexpected MongoDB error: {e}")
        print("📁 Falling back to JSON file storage")
        _mongodb_available = False
        _mongo_client = None
        return False


def get_database():
    """
    Get MongoDB database instance.
    
    Returns:
        Database: MongoDB database object or None
    """
    global _mongo_client, _mongodb_available
    
    if not _mongodb_available or _mongo_client is None:
        return None
    
    try:
        return _mongo_client[DB_NAME]
    except Exception as e:
        print(f"❌ Database access error: {e}")
        return None


def get_collection(collection_name):
    """
    Get MongoDB collection with error handling.
    
    Args:
        collection_name (str): Name of the collection
        
    Returns:
        Collection: MongoDB collection object or None
    """
    db = get_database()
    if db is None:
        return None
    
    try:
        return db[collection_name]
    except Exception as e:
        print(f"❌ Collection access error: {e}")
        return None


def is_mongodb_available():
    """
    Check if MongoDB is currently available.
    
    Returns:
        bool: True if MongoDB is connected and working
    """
    global _mongodb_available, _mongo_client
    
    if not _mongodb_available or _mongo_client is None:
        return False
    
    try:
        # Ping to verify connection is alive
        _mongo_client.admin.command('ping')
        return True
    except Exception:
        _mongodb_available = False
        return False


def close_mongodb():
    """Close MongoDB connection gracefully."""
    global _mongo_client, _mongodb_available
    
    if _mongo_client:
        try:
            _mongo_client.close()
            print("✅ MongoDB connection closed")
        except Exception as e:
            print(f"⚠️ Error closing MongoDB: {e}")
        finally:
            _mongo_client = None
            _mongodb_available = False


# Collection name constants
USERS_COLLECTION = "users"
FILES_COLLECTION = "files"
FOLDERS_COLLECTION = "folders"
ACTIVITY_LOG_COLLECTION = "activity_log"
ACCESS_LOG_COLLECTION = "access_log"
OTP_COLLECTION = "otp"
SHARES_COLLECTION = "shares"
ALERTS_COLLECTION = "sent_alerts"


# Initialize MongoDB on module import
init_mongodb()


if __name__ == "__main__":
    # Test connection
    print("\n🧪 Testing MongoDB connection...")
    
    if is_mongodb_available():
        print("✅ MongoDB is ready!")
        
        # Test collections
        db = get_database()
        collections = db.list_collection_names()
        print(f"📚 Available collections: {collections}")
        
    else:
        print("❌ MongoDB not available - using JSON fallback")
    
    close_mongodb()
