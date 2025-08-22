"""
User Migration Utility - Migrate existing local users to Firebase
"""

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
import json
import os
from datetime import datetime

def initialize_firebase_admin():
    """Initialize Firebase Admin SDK for migration"""
    try:
        # Use environment variables or Streamlit secrets
        if 'firebase_initialized' not in globals():
            firebase_config = {
                "type": "service_account",
                "project_id": os.environ.get("FIREBASE_PROJECT_ID", st.secrets.get("firebase_project_id")),
                "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", st.secrets.get("firebase_private_key_id")),
                "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", st.secrets.get("firebase_private_key", "")).replace('\\n', '\n'),
                "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL", st.secrets.get("firebase_client_email")),
                "client_id": os.environ.get("FIREBASE_CLIENT_ID", st.secrets.get("firebase_client_id")),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL", st.secrets.get("firebase_client_cert_url"))
            }
            
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            globals()['firebase_initialized'] = True
        
        return firestore.client()
    
    except Exception as e:
        print(f"Firebase initialization failed: {e}")
        return None

def migrate_local_users():
    """Migrate users from local storage to Firebase"""
    
    # Initialize Firebase
    db = initialize_firebase_admin()
    if not db:
        print("❌ Could not initialize Firebase. Migration aborted.")
        return
    
    print("✅ Firebase initialized successfully")
    
    # Load existing users (you may need to adjust this based on your local storage format)
    # Example: Loading from a JSON file
    local_users_file = "local_users.json"
    
    if os.path.exists(local_users_file):
        with open(local_users_file, 'r') as f:
            local_users = json.load(f)
    else:
        # Default demo users for testing
        local_users = {
            "demo": {
                "password": hashlib.sha256("demo123".encode()).hexdigest(),
                "stats": {
                    "total_questions": 50,
                    "correct_answers": 35,
                    "categories": {
                        "SCIENCE": {"total": 10, "correct": 8},
                        "HISTORY": {"total": 15, "correct": 10},
                        "LITERATURE": {"total": 25, "correct": 17}
                    },
                    "streak": 5,
                    "best_streak": 12,
                    "total_score": 15000,
                    "accuracy": 70.0
                }
            },
            "test_user": {
                "password": hashlib.sha256("test123".encode()).hexdigest(),
                "stats": {
                    "total_questions": 20,
                    "correct_answers": 15,
                    "categories": {
                        "GEOGRAPHY": {"total": 10, "correct": 8},
                        "SPORTS": {"total": 10, "correct": 7}
                    },
                    "streak": 3,
                    "best_streak": 8,
                    "total_score": 8000,
                    "accuracy": 75.0
                }
            }
        }
    
    # Migrate each user to Firestore
    migrated_count = 0
    failed_count = 0
    
    for username, user_data in local_users.items():
        try:
            print(f"Migrating user: {username}...")
            
            # Prepare user document
            user_doc = {
                "username": username,
                "created_at": firestore.SERVER_TIMESTAMP,
                "migrated_at": firestore.SERVER_TIMESTAMP,
                "stats": user_data.get("stats", {}),
                "is_migrated": True,
                "auth_type": "local_migrated"
            }
            
            # Don't store passwords in Firestore - they should use Firebase Auth
            # Instead, mark these users as needing password reset
            user_doc["needs_password_reset"] = True
            
            # Save to Firestore
            user_ref = db.collection('users').document(username)
            user_ref.set(user_doc, merge=True)
            
            # Also create a migration log
            migration_ref = db.collection('migrations').add({
                "username": username,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "source": "local_storage",
                "stats_migrated": bool(user_data.get("stats")),
                "success": True
            })
            
            print(f"✅ Successfully migrated: {username}")
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Failed to migrate {username}: {e}")
            failed_count += 1
            
            # Log failed migration
            try:
                db.collection('migrations').add({
                    "username": username,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "source": "local_storage",
                    "success": False,
                    "error": str(e)
                })
            except:
                pass
    
    # Create migration summary
    try:
        summary_ref = db.collection('migration_summaries').add({
            "timestamp": firestore.SERVER_TIMESTAMP,
            "total_users": len(local_users),
            "migrated_count": migrated_count,
            "failed_count": failed_count,
            "migration_type": "local_to_firebase"
        })
        print(f"\n📊 Migration Summary:")
        print(f"   Total users: {len(local_users)}")
        print(f"   Successfully migrated: {migrated_count}")
        print(f"   Failed: {failed_count}")
    except Exception as e:
        print(f"Could not save migration summary: {e}")
    
    return migrated_count, failed_count

def verify_migration():
    """Verify that users were successfully migrated"""
    db = initialize_firebase_admin()
    if not db:
        print("❌ Could not initialize Firebase for verification.")
        return
    
    print("\n🔍 Verifying migration...")
    
    try:
        # Get all migrated users
        users = db.collection('users').where('is_migrated', '==', True).stream()
        
        migrated_users = []
        for user in users:
            user_data = user.to_dict()
            migrated_users.append({
                'username': user.id,
                'stats': user_data.get('stats', {}),
                'needs_password_reset': user_data.get('needs_password_reset', False)
            })
        
        print(f"\n✅ Found {len(migrated_users)} migrated users in Firestore:")
        for user in migrated_users:
            print(f"   - {user['username']}: {user['stats'].get('total_questions', 0)} questions answered")
            if user['needs_password_reset']:
                print(f"     ⚠️  Needs password reset")
        
        return migrated_users
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return []

if __name__ == "__main__":
    print("=" * 50)
    print("User Migration Tool - Local to Firebase")
    print("=" * 50)
    
    # Run migration
    migrated, failed = migrate_local_users()
    
    # Verify migration
    if migrated > 0:
        verify_migration()
    
    print("\n✅ Migration complete!")
    print("\nNOTE: Migrated users will need to reset their passwords")
    print("      when they first log in with Firebase Authentication.")