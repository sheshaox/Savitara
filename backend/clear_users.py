#!/usr/bin/env python3
"""
Clear all users from database
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.connection import DatabaseManager


async def clear_users():
    """Delete all users and profiles"""
    print("Connecting to database...")
    await DatabaseManager.connect_to_database()
    
    db = DatabaseManager.get_database()
    
    # Count before deletion
    user_count = await db.users.count_documents({})
    grihasta_count = await db.grihasta_profiles.count_documents({})
    acharya_count = await db.acharya_profiles.count_documents({})
    
    print(f"\n📊 Current counts:")
    print(f"   Users: {user_count}")
    print(f"   Grihasta Profiles: {grihasta_count}")
    print(f"   Acharya Profiles: {acharya_count}")
    
    if user_count == 0 and grihasta_count == 0 and acharya_count == 0:
        print("\n✅ Database is already empty!")
        await DatabaseManager.close_database_connection()
        return
    
    # Delete all users
    print("\n🗑️ Deleting all users...")
    result = await db.users.delete_many({})
    print(f"   Deleted {result.deleted_count} users")
    
    # Delete all grihasta profiles
    print("🗑️ Deleting all Grihasta profiles...")
    result = await db.grihasta_profiles.delete_many({})
    print(f"   Deleted {result.deleted_count} Grihasta profiles")
    
    # Delete all acharya profiles
    print("🗑️ Deleting all Acharya profiles...")
    result = await db.acharya_profiles.delete_many({})
    print(f"   Deleted {result.deleted_count} Acharya profiles")
    
    print("\n✅ All users and profiles cleared successfully!")
    
    await DatabaseManager.close_database_connection()


if __name__ == "__main__":
    asyncio.run(clear_users())
