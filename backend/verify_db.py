#!/usr/bin/env python3
"""
MongoDB Connection Verification Script
Run this script to test database connectivity with detailed diagnostics
"""
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.connection import DatabaseManager
from app.core.config import settings


async def verify_database():
    """Verify MongoDB connection with detailed reporting"""
    print("=" * 60)
    print("🔍 Savitara MongoDB Connection Verification")
    print("=" * 60)
    
    print(f"📊 Configuration:")
    print(f"   Database Name: {settings.MONGODB_DB_NAME}")
    print(f"   MongoDB URL: {DatabaseManager._mask_connection_string(settings.MONGODB_URL)}")
    print(f"   Pool Size: {settings.MONGODB_MIN_POOL_SIZE}-{settings.MONGODB_MAX_POOL_SIZE}")
    print(f"   Environment: {settings.APP_ENV}")
    print()
    
    try:
        print("🔄 Attempting connection...")
        await DatabaseManager.connect_to_database()
        
        print("✅ Connection established!")
        print()
        
        # Perform health check
        print("🏥 Running health check...")
        health = await DatabaseManager.health_check(force_check=True)
        
        print(f"   Status: {health['status']}")
        print(f"   Ping Time: {health.get('ping_time_ms', 'N/A')} ms")
        
        if 'server_info' in health:
            server_info = health['server_info']
            print(f"   MongoDB Version: {server_info.get('version', 'unknown')}")
            print(f"   Git Version: {server_info.get('git_version', 'unknown')}")
        
        # Test basic operations
        print()
        print("🧪 Testing basic database operations...")
        
        # Test collection access
        users_count = await DatabaseManager.db.users.count_documents({})
        print(f"   Users collection: {users_count} documents")
        
        # Test index creation (should be fast if already exist)
        print("   Creating/verifying indexes...")
        await DatabaseManager.create_indexes()
        print("   ✅ Indexes verified")
        
        print()
        print("🎉 All tests passed! Database is ready for use.")
        
    except Exception as e:
        print(f"❌ Connection failed!")
        print(f"   Error: {e}")
        print(f"   Type: {type(e).__name__}")
        print()
        print("🔧 Troubleshooting suggestions:")
        print("   1. Check MONGODB_URL in .env file")
        print("   2. Verify MongoDB server is accessible")
        print("   3. Check network connectivity and firewall")
        print("   4. Verify authentication credentials")
        print("   5. For Atlas: check IP whitelist settings")
        return False
        
    finally:
        # Clean up
        await DatabaseManager.close_database_connection()
        print()
        print("🔒 Connection closed")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_database())
    sys.exit(0 if success else 1)