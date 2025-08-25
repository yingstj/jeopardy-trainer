"""
Firebase Authentication Helper for Streamlit with proper initialization checks
Implements singleton pattern to prevent multiple initialization attempts
"""

import firebase_admin
from firebase_admin import credentials, auth
import streamlit as st
import os
import json
import logging
from typing import Optional, Dict, Any
import threading

logger = logging.getLogger(__name__)


class FirebaseAuthHelper:
    """Singleton Firebase Auth Helper for Streamlit"""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Firebase Admin SDK only once"""
        if not FirebaseAuthHelper._initialized:
            with FirebaseAuthHelper._lock:
                if not FirebaseAuthHelper._initialized:
                    self._initialize_firebase()
                    FirebaseAuthHelper._initialized = True
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK with proper error handling"""
        try:
            # Check if already initialized
            if firebase_admin._apps:
                logger.info("Firebase Admin SDK already initialized")
                return
            
            # Try to get credentials from Streamlit secrets
            if hasattr(st, 'secrets') and 'firebase' in st.secrets:
                logger.info("Initializing Firebase from Streamlit secrets")
                
                # Build credential dict from secrets
                cred_dict = {
                    "type": st.secrets["firebase"].get("type", "service_account"),
                    "project_id": st.secrets["firebase"]["project_id"],
                    "private_key_id": st.secrets["firebase"].get("private_key_id", ""),
                    "private_key": st.secrets["firebase"]["private_key"].replace('\\n', '\n'),
                    "client_email": st.secrets["firebase"]["client_email"],
                    "client_id": st.secrets["firebase"].get("client_id", ""),
                    "auth_uri": st.secrets["firebase"].get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                    "token_uri": st.secrets["firebase"].get("token_uri", "https://oauth2.googleapis.com/token"),
                    "auth_provider_x509_cert_url": st.secrets["firebase"].get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
                    "client_x509_cert_url": st.secrets["firebase"].get("client_x509_cert_url", "")
                }
                
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully from Streamlit secrets")
                
            # Try environment variables
            elif os.environ.get("FIREBASE_SERVICE_ACCOUNT"):
                logger.info("Initializing Firebase from environment variable")
                
                service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
                cred_dict = json.loads(service_account_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully from environment")
                
            # Try local file
            elif os.path.exists("firebase_service_account.json"):
                logger.info("Initializing Firebase from local file")
                
                cred = credentials.Certificate("firebase_service_account.json")
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully from local file")
                
            else:
                # Initialize without credentials (limited functionality)
                logger.warning("No Firebase credentials found, initializing with default (limited functionality)")
                firebase_admin.initialize_app()
                
        except ValueError as e:
            if "already exists" in str(e):
                logger.info("Firebase app already exists")
            else:
                logger.error(f"Firebase initialization error: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            # Don't raise - allow app to continue with limited functionality
    
    def verify_firebase_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Firebase ID token
        Returns user data if valid, None otherwise
        """
        try:
            if not id_token:
                logger.warning("No token provided for verification")
                return None
            
            # Verify the token
            decoded_token = auth.verify_id_token(id_token)
            
            user_data = {
                'uid': decoded_token.get('uid'),
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name') or decoded_token.get('email', '').split('@')[0],
                'email_verified': decoded_token.get('email_verified', False),
                'picture': decoded_token.get('picture'),
                'provider': decoded_token.get('firebase', {}).get('sign_in_provider')
            }
            
            logger.info(f"Successfully verified token for user: {user_data['email']}")
            return user_data
            
        except auth.InvalidIdTokenError as e:
            logger.error(f"Invalid ID token: {e}")
            return None
        except auth.ExpiredIdTokenError as e:
            logger.error(f"Expired ID token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None
    
    def create_or_get_user(self, email: str, display_name: Optional[str] = None) -> Optional[auth.UserRecord]:
        """
        Create a new Firebase user or get existing one
        """
        try:
            # Try to get existing user
            try:
                user = auth.get_user_by_email(email)
                logger.info(f"Found existing user: {email}")
                return user
            except auth.UserNotFoundError:
                pass
            
            # Create new user
            user = auth.create_user(
                email=email,
                display_name=display_name or email.split('@')[0],
                email_verified=False
            )
            logger.info(f"Created new Firebase user: {email}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating/getting user: {e}")
            return None
    
    def update_user(self, uid: str, **kwargs) -> bool:
        """
        Update Firebase user properties
        """
        try:
            auth.update_user(uid, **kwargs)
            logger.info(f"Updated user {uid}")
            return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def delete_user(self, uid: str) -> bool:
        """
        Delete a Firebase user
        """
        try:
            auth.delete_user(uid)
            logger.info(f"Deleted user {uid}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def list_users(self, max_results: int = 100) -> list:
        """
        List Firebase users
        """
        try:
            users = []
            page = auth.list_users()
            
            while page:
                for user in page.users:
                    users.append({
                        'uid': user.uid,
                        'email': user.email,
                        'display_name': user.display_name,
                        'created': user.user_metadata.creation_timestamp if user.user_metadata else None
                    })
                    if len(users) >= max_results:
                        break
                
                if len(users) >= max_results or not page.has_next_page:
                    break
                    
                page = page.get_next_page()
            
            return users
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific user by UID
        """
        try:
            user = auth.get_user(uid)
            return {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'email_verified': user.email_verified,
                'disabled': user.disabled,
                'created': user.user_metadata.creation_timestamp if user.user_metadata else None
            }
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None


# Global singleton instance
firebase_auth_helper = FirebaseAuthHelper()