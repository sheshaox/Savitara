"""
Test registration endpoint to identify and fix errors
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.security import SecurityManager
from app.models.database import User, UserRole, UserStatus

async def test_registration():
    """Test user registration with database"""
    print("=" * 60)
    print("TESTING USER REGISTRATION")
    print("=" * 60)
    
    # MongoDB connection
    MONGODB_URL = "mongodb+srv://sheshagirijoshi18_db_savitara:savitara123@cluster0.0q2ghgt.mongodb.net/?appName=Cluster0"
    DB_NAME = "savitara"
    
    try:
        # Connect to MongoDB
        print("\n1. Connecting to MongoDB...")
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DB_NAME]
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Test credentials
        test_email = "testuser@savitara.com"
        test_password = "TestPass123"
        test_name = "Test User"
        test_role = UserRole.GRIHASTA
        
        print(f"\n2. Testing with credentials:")
        print(f"   Email: {test_email}")
        print(f"   Name: {test_name}")
        print(f"   Role: {test_role}")
        
        # Check if user already exists
        print("\n3. Checking if user exists...")
        existing = await db.users.find_one({"email": test_email})
        if existing:
            print(f"⚠️  User exists with ID: {existing['_id']}")
            print("   Deleting existing test user...")
            await db.users.delete_one({"email": test_email})
            print("✅ Deleted existing test user")
        else:
            print("✅ User doesn't exist - good to proceed")
        
        # Create user object
        print("\n4. Creating user object...")
        security_manager = SecurityManager()
        
        try:
            user = User(
                email=test_email,
                name=test_name,
                password_hash=security_manager.get_password_hash(test_password),
                role=test_role,
                status=UserStatus.PENDING,
                credits=100,
                onboarded=False,
                device_tokens=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            print("✅ User object created successfully")
            print(f"   User: {user.email}, Role: {user.role}")
        except Exception as e:
            print(f"❌ ERROR creating user object: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return
        
        # Serialize user for database
        print("\n5. Serializing user for database...")
        try:
            user_dict = user.model_dump(by_alias=True, exclude_none=True, mode='json')
            print("✅ User serialized successfully")
            print(f"   Fields: {list(user_dict.keys())}")
        except Exception as e:
            print(f"❌ ERROR serializing user: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return
        
        # Insert into database
        print("\n6. Inserting user into database...")
        try:
            result = await db.users.insert_one(user_dict)
            user_id = str(result.inserted_id)
            print(f"✅ User inserted successfully!")
            print(f"   User ID: {user_id}")
        except Exception as e:
            print(f"❌ ERROR inserting user: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return
        
        # Generate tokens
        print("\n7. Generating auth tokens...")
        try:
            access_token = security_manager.create_access_token(
                user_id=user_id,
                role=user.role.value
            )
            refresh_token = security_manager.create_refresh_token(
                user_id=user_id
            )
            print("✅ Tokens generated successfully")
            print(f"   Access token length: {len(access_token)}")
            print(f"   Refresh token length: {len(refresh_token)}")
        except Exception as e:
            print(f"❌ ERROR generating tokens: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return
        
        print("\n" + "=" * 60)
        print("✅ REGISTRATION TEST PASSED!")
        print("=" * 60)
        print("\nUser successfully created in database.")
        print("The registration endpoint should work now.")
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.close()
            print("\n🔒 Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_registration())
