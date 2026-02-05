"""
MongoDB Database Connection Manager
SonarQube: S2095 - Ensure resources are properly closed
SonarQube: S1192 - No duplicated strings
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging
import asyncio
import time
from datetime import datetime, timezone

from app.core.config import settings
from app.core.constants import FIELD_LOCATION_CITY

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Singleton database connection manager with retry logic and health monitoring
    SonarQube: Proper resource management
    """
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    _connection_attempts: int = 0
    _last_connection_time: Optional[float] = None
    _last_health_check: Optional[float] = None
    _health_status: str = "disconnected"
    
    # Connection configuration
    MAX_RETRIES = 5
    INITIAL_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 30.0     # seconds
    HEALTH_CHECK_INTERVAL = 60.0  # seconds
    
    @classmethod
    async def connect_to_database(cls, force_reconnect: bool = False):
        """
        Initialize database connection with retry logic and exponential backoff
        SonarQube: S2095 - Connection is managed properly
        """
        if cls.client is not None and not force_reconnect:
            logger.info("Database already connected, skipping connection attempt")
            return
        
        cls._connection_attempts = 0
        retry_delay = cls.INITIAL_RETRY_DELAY
        
        while cls._connection_attempts < cls.MAX_RETRIES:
            cls._connection_attempts += 1
            
            try:
                logger.info(f"Connecting to MongoDB (attempt {cls._connection_attempts}/{cls.MAX_RETRIES})...")
                logger.info(f"MongoDB URL: {cls._mask_connection_string(settings.MONGODB_URL)}")
                logger.info(f"Database name: {settings.MONGODB_DB_NAME}")
                
                start_time = time.time()
                
                # Create async MongoDB client
                cls.client = AsyncIOMotorClient(
                    settings.MONGODB_URL,
                    minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                    maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    retryWrites=True,
                    retryReads=True,
                    heartbeatFrequencyMS=10000,  # 10 seconds
                    maxIdleTimeMS=30000,  # 30 seconds
                )
                
                # Get database
                cls.db = cls.client[settings.MONGODB_DB_NAME]
                
                # Verify connection with detailed ping
                ping_result = await cls._detailed_ping()
                connection_time = time.time() - start_time
                
                cls._last_connection_time = time.time()
                cls._health_status = "healthy"
                
                logger.info(f"✅ Successfully connected to MongoDB in {connection_time:.2f}s")
                logger.info(f"MongoDB version: {ping_result.get('version', 'unknown')}")
                logger.info(f"Server info: {ping_result}")
                logger.info(f"Connection pool - Min: {settings.MONGODB_MIN_POOL_SIZE}, Max: {settings.MONGODB_MAX_POOL_SIZE}")
                
                # Create indexes
                await cls.create_indexes()
                
                # Reset connection attempts on success
                cls._connection_attempts = 0
                return
                
            except Exception as e:
                connection_time = time.time() - start_time
                error_type = type(e).__name__
                error_msg = str(e)
                
                logger.error(f"❌ MongoDB connection failed (attempt {cls._connection_attempts}/{cls.MAX_RETRIES})")
                logger.error(f"Connection time: {connection_time:.2f}s")
                logger.error(f"Error type: {error_type}")
                logger.error(f"Error message: {error_msg}")
                
                # Clean up failed connection
                if cls.client:
                    cls.client.close()
                cls.client = None
                cls.db = None
                cls._health_status = "unhealthy"
                
                # Log specific error types for better debugging
                if "authentication" in error_msg.lower():
                    logger.error("🔑 Authentication failed - check username/password in MONGODB_URL")
                elif "network" in error_msg.lower() or "timeout" in error_msg.lower():
                    logger.error("🌐 Network error - check connectivity and firewall settings")
                elif "dns" in error_msg.lower():
                    logger.error("🌍 DNS resolution failed - check MongoDB host address")
                elif "ssl" in error_msg.lower() or "tls" in error_msg.lower():
                    logger.error("🔒 SSL/TLS error - check certificate configuration")
                
                # If this was the last attempt, raise the exception
                if cls._connection_attempts >= cls.MAX_RETRIES:
                    logger.error(f"💀 Failed to connect to MongoDB after {cls.MAX_RETRIES} attempts")
                    logger.error("Possible solutions:")
                    logger.error("1. Check MONGODB_URL in .env file")
                    logger.error("2. Verify MongoDB server is running and accessible")
                    logger.error("3. Check network connectivity and firewall settings")
                    logger.error("4. Verify authentication credentials")
                    logger.error("5. Check MongoDB Atlas IP whitelist (if using Atlas)")
                    raise
                
                # Wait before retry with exponential backoff
                logger.info(f"⏳ Retrying in {retry_delay:.1f} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, cls.MAX_RETRY_DELAY)
    
    @classmethod
    async def _detailed_ping(cls):
        """Perform detailed ping to get server information"""
        if cls.client is None:
            raise Exception("No database client available")
        
        # Basic ping
        await cls.client.admin.command('ping')
        
        # Get server info
        try:
            server_info = await cls.client.admin.command('buildinfo')
            return {
                'status': 'ok',
                'version': server_info.get('version', 'unknown'),
                'git_version': server_info.get('gitVersion', 'unknown'),
                'server_status': 'available'
            }
        except Exception as e:
            logger.warning(f"Could not get detailed server info: {e}")
            return {'status': 'ok', 'version': 'unknown'}
    
    @classmethod
    def _mask_connection_string(cls, connection_string: str) -> str:
        """Mask sensitive information in connection string for logging"""
        if not connection_string:
            return "None"
        
        # Mask password in mongodb:// or mongodb+srv:// URLs
        import re
        masked = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', connection_string)
        return masked
    
    @classmethod
    async def health_check(cls, force_check: bool = False) -> dict:
        """
        Perform health check with caching to avoid excessive DB calls
        """
        current_time = time.time()
        
        # Use cached result if recent (unless forced)
        if (not force_check and 
            cls._last_health_check and 
            current_time - cls._last_health_check < cls.HEALTH_CHECK_INTERVAL):
            return {
                'status': cls._health_status,
                'last_check': cls._last_health_check,
                'cached': True
            }
        
        try:
            if cls.client is None or cls.db is None:
                cls._health_status = "disconnected"
                return {
                    'status': cls._health_status,
                    'error': 'No database connection',
                    'last_check': current_time
                }
            
            start_time = time.time()
            ping_result = await cls._detailed_ping()
            ping_time = time.time() - start_time
            
            cls._health_status = "healthy"
            cls._last_health_check = current_time
            
            return {
                'status': cls._health_status,
                'ping_time_ms': round(ping_time * 1000, 2),
                'server_info': ping_result,
                'connection_time': cls._last_connection_time,
                'last_check': current_time,
                'cached': False
            }
            
        except Exception as e:
            cls._health_status = "unhealthy" 
            cls._last_health_check = current_time
            
            logger.warning(f"Database health check failed: {e}")
            
            return {
                'status': cls._health_status,
                'error': str(e),
                'error_type': type(e).__name__,
                'last_check': current_time,
                'cached': False
            }
    
    @classmethod
    async def close_database_connection(cls):
        """
        Close database connection
        SonarQube: S2095 - Explicitly close resources
        """
        if cls.client is not None:
            logger.info("Closing MongoDB connection...")
            cls.client.close()
            cls.client = None
            cls.db = None
            cls._health_status = "disconnected"
            logger.info("MongoDB connection closed")
    
    @classmethod
    async def reconnect(cls):
        """
        Force reconnection to database
        """
        logger.info("Forcing database reconnection...")
        await cls.close_database_connection()
        await cls.connect_to_database(force_reconnect=True)
    
    @classmethod
    async def _create_index_safe(cls, collection, *args, **kwargs):
        """
        Safely create index, ignore if it already exists
        """
        try:
            await collection.create_index(*args, **kwargs)
            return True  # Index created
        except Exception as e:
            # Ignore index already exists errors
            if "existing index" in str(e).lower() or "IndexKeySpecsConflict" in str(e):
                logger.debug(f"Index already exists: {str(e)[:100]}")
                return False  # Index skipped
            else:
                # Re-raise other errors
                logger.error(f"Failed to create index: {e}")
                raise
    
    @classmethod
    async def create_indexes(cls):
        """
        Create database indexes for performance
        SonarQube: Optimize database queries
        """
        if cls.db is None:
            logger.warning("Cannot create indexes - no database connection")
            return
        
        logger.info("Creating database indexes...")
        index_start_time = time.time()
        indexes_created = 0
        indexes_skipped = 0
        
        # Users collection indexes
        if await cls._create_index_safe(cls.db.users, "email", unique=True):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.users, "google_id", unique=True, sparse=True):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.users, [("role", 1), ("status", 1)]):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.users, "created_at"):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.users, "phone"):
            indexes_created += 1
        else:
            indexes_skipped += 1
        
        # Grihasta profiles indexes
        if await cls._create_index_safe(cls.db.grihasta_profiles, "user_id", unique=True):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.grihasta_profiles, FIELD_LOCATION_CITY):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.grihasta_profiles, [("user_id", 1), (FIELD_LOCATION_CITY, 1)]):
            indexes_created += 1
        else:
            indexes_skipped += 1
        
        # Acharya profiles indexes
        await cls._create_index_safe(cls.db.acharya_profiles, "user_id", unique=True)
        await cls._create_index_safe(cls.db.acharya_profiles, "status")
        await cls._create_index_safe(cls.db.acharya_profiles, [("status", 1), ("ratings.average", -1)])
        await cls._create_index_safe(cls.db.acharya_profiles, [("status", 1), ("ratings.count", -1)])
        await cls._create_index_safe(cls.db.acharya_profiles, FIELD_LOCATION_CITY)
        await cls._create_index_safe(cls.db.acharya_profiles, "parampara")
        await cls._create_index_safe(cls.db.acharya_profiles, "specializations")
        await cls._create_index_safe(cls.db.acharya_profiles, "languages")
        
        # Compound index for advanced search
        await cls._create_index_safe(cls.db.acharya_profiles, [
            ("status", 1),
            (FIELD_LOCATION_CITY, 1),
            ("ratings.average", -1),
            ("hourly_rate", 1)
        ])
        
        # Text search index for acharyas
        await cls._create_index_safe(cls.db.acharya_profiles, [
            ("name", "text"),
            ("bio", "text"),
            ("specializations", "text")
        ])
        
        # Geospatial index for location-based search
        await cls._create_index_safe(cls.db.acharya_profiles, [("location.coordinates", "2dsphere")])
        
        # Bookings indexes
        await cls._create_index_safe(cls.db.bookings, [("grihasta_id", 1), ("status", 1)])
        await cls._create_index_safe(cls.db.bookings, [("acharya_id", 1), ("status", 1)])
        await cls._create_index_safe(cls.db.bookings, [("acharya_id", 1), ("date_time", 1)])
        await cls._create_index_safe(cls.db.bookings, [("grihasta_id", 1), ("created_at", -1)])
        await cls._create_index_safe(cls.db.bookings, [("date_time", 1), ("status", 1)])
        await cls._create_index_safe(cls.db.bookings, "status")
        await cls._create_index_safe(cls.db.bookings, "created_at")
        await cls._create_index_safe(cls.db.bookings, "payment_status")
        
        # Compound index for booking queries
        await cls._create_index_safe(cls.db.bookings, [
            ("acharya_id", 1),
            ("date_time", 1),
            ("status", 1)
        ])
        
        # Messages indexes
        await cls._create_index_safe(cls.db.messages, "conversation_id")
        await cls._create_index_safe(cls.db.messages, [("conversation_id", 1), ("created_at", -1)])
        await cls._create_index_safe(cls.db.messages, [("sender_id", 1), ("receiver_id", 1)])
        await cls._create_index_safe(cls.db.messages, "created_at")
        
        # Conversations indexes
        await cls._create_index_safe(cls.db.conversations, "participants")
        await cls._create_index_safe(cls.db.conversations, [("participants", 1), ("updated_at", -1)])
        
        # Panchanga indexes
        await cls._create_index_safe(cls.db.panchanga, "date", unique=True)
        await cls._create_index_safe(cls.db.panchanga, [("date", 1), ("location", 1)])
        
        # Reviews indexes
        await cls._create_index_safe(cls.db.reviews, "booking_id", unique=True)
        await cls._create_index_safe(cls.db.reviews, "acharya_id")
        await cls._create_index_safe(cls.db.reviews, [("acharya_id", 1), ("created_at", -1)])
        await cls._create_index_safe(cls.db.reviews, [("is_public", 1), ("rating", -1)])
        await cls._create_index_safe(cls.db.reviews, "grihasta_id")
        
        # Analytics events indexes
        await cls._create_index_safe(cls.db.analytics_events, [("user_id", 1), ("timestamp", -1)])
        await cls._create_index_safe(cls.db.analytics_events, [("event_name", 1), ("timestamp", -1)])
        await cls._create_index_safe(cls.db.analytics_events, "date")
        
        # Loyalty program indexes
        await cls._create_index_safe(cls.db.user_loyalty, "user_id", unique=True)
        await cls._create_index_safe(cls.db.user_loyalty, [("tier", 1), ("points", -1)])
        
        # Referrals indexes
        await cls._create_index_safe(cls.db.referrals, "referrer_id")
        await cls._create_index_safe(cls.db.referrals, "referred_user_id", unique=True)
        await cls._create_index_safe(cls.db.referrals, "referral_code")
        
        # Notifications indexes
        await cls._create_index_safe(cls.db.notifications, [("user_id", 1), ("created_at", -1)])
        await cls._create_index_safe(cls.db.notifications, [("user_id", 1), ("read", 1)])
        
        # Services indexes
        if await cls._create_index_safe(cls.db.services, "category_id"):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.services, [("is_active", 1), ("popularity_score", -1)]):
            indexes_created += 1
        else:
            indexes_skipped += 1
        
        # Service Bookings indexes
        if await cls._create_index_safe(cls.db.service_bookings, "service_id"):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.service_bookings, [("user_id", 1), ("created_at", -1)]):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.service_bookings, "booking_type"):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.service_bookings, "status"):
            indexes_created += 1
        else:
            indexes_skipped += 1
        
        # Gamification & Wallet indexes
        if await cls._create_index_safe(cls.db.coupons, "code", unique=True):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.coupons, [("is_active", 1), ("valid_until", 1)]):
            indexes_created += 1
        else:
            indexes_skipped += 1
        if await cls._create_index_safe(cls.db.wallet_transactions, [("user_id", 1), ("created_at", -1)]):
            indexes_created += 1
        else:
            indexes_skipped += 1
        
        index_time = time.time() - index_start_time
        logger.info(f"✅ Database indexes completed in {index_time:.2f}s")
        logger.info(f"📊 Index summary: {indexes_created} created, {indexes_skipped} already existed")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance - returns None if not connected"""
        return cls.db
    
    @classmethod
    def is_connected(cls) -> bool:
        """Check if database is connected"""
        return cls.db is not None


# Dependency for FastAPI
def get_db() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency to get database
    SonarQube: Proper dependency injection
    Raises ServiceUnavailableError if database is not connected
    """
    db = DatabaseManager.get_database()
    
    # Test environment fallback
    if db is None:
        import sys
        if "pytest" in sys.modules and hasattr(DatabaseManager, "_test_db"):
            return DatabaseManager._test_db

    if db is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {
                    "code": "DB_001",
                    "message": "Database service unavailable. Please try again later.",
                    "details": {}
                }
            }
        )
    return db
