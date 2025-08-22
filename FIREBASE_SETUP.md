# Firebase Authentication Setup for Jaypardy

This application has been configured to use Firebase Authentication for user management.

## Firebase Project Details

- **Project Name**: Jaypardy
- **Project ID**: jaypardy-53a55
- **Web API Key**: AIzaSyD7OcmmwWY6zV4ngPHjsdwxvoXJ41r55UM

## Features Implemented

### Authentication Methods
1. **Email/Password Authentication**
   - User registration with email and password
   - Email verification
   - Password reset functionality

2. **Google Sign-In**
   - One-click Google authentication
   - Automatic account creation for new users

3. **Phone Number Authentication**
   - SMS verification code
   - reCAPTCHA protection

### User Management
- Profile management
- Display name updates
- Account deletion
- Session management

## File Structure

### New Files Added
- `firebase_config.py` - Firebase configuration and credentials
- `firebase_auth.py` - Firebase authentication backend logic
- `templates/firebase_login.html` - Firebase login page
- `templates/firebase_register.html` - Firebase registration page
- `templates/firebase_profile.html` - User profile page with Firebase

### Modified Files
- `app.py` - Integrated Firebase authentication blueprint
- `requirements.txt` - Added Firebase dependencies

## Environment Variables

For production deployment, set these environment variables:

```bash
# Firebase Configuration
FIREBASE_API_KEY=AIzaSyD7OcmmwWY6zV4ngPHjsdwxvoXJ41r55UM
FIREBASE_AUTH_DOMAIN=jaypardy-53a55.firebaseapp.com
FIREBASE_PROJECT_ID=jaypardy-53a55
FIREBASE_STORAGE_BUCKET=jaypardy-53a55.appspot.com
FIREBASE_MESSAGING_SENDER_ID=367259134434

# Firebase Admin SDK (for server-side operations)
# Download service account key from Firebase Console
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=your_client_email
FIREBASE_CLIENT_ID=your_client_id
```

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Firebase Console Setup
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select the Jaypardy project
3. Enable Authentication methods:
   - Email/Password
   - Google
   - Phone

### 3. Service Account (Optional)
For enhanced server-side features:
1. Go to Project Settings > Service Accounts
2. Generate new private key
3. Set environment variables with the service account details

### 4. Run the Application
```bash
python app.py
```

## Usage

### Default Authentication Flow
The application now uses Firebase authentication by default. Users will be redirected to `/firebase_auth/login` when accessing protected routes.

### Switching Between Auth Systems
- Firebase Auth: Access via `/firebase_auth/login`
- Legacy Auth: Access via `/auth/login` (still available)

### API Integration
All API endpoints now support both authentication methods:
- Session-based (legacy)
- Firebase token-based

## Security Notes

1. **API Key Security**: While the Web API Key is visible in client-side code, it's restricted by:
   - HTTP referrer restrictions (configure in Firebase Console)
   - Domain whitelisting
   - Firebase Security Rules

2. **Service Account**: Keep the service account credentials secure and never commit them to version control

3. **Session Management**: Sessions are still maintained server-side for compatibility with existing features

## Troubleshooting

### Common Issues

1. **"Firebase Admin SDK initialization failed"**
   - This warning appears if no service account is configured
   - Basic authentication still works without it

2. **Phone authentication not working**
   - Ensure phone auth is enabled in Firebase Console
   - Check that reCAPTCHA is properly configured

3. **Google Sign-In issues**
   - Verify OAuth consent screen is configured
   - Check authorized domains in Firebase Console

## Testing

Test the authentication flow:
1. Visit the application homepage
2. You'll be redirected to Firebase login
3. Try registering a new account
4. Test login with email/password
5. Test Google Sign-In
6. Verify profile page loads correctly

## Migration from Legacy Auth

Existing users from the legacy authentication system will need to:
1. Create a new account through Firebase
2. Or link their existing account (future feature)

## Support

For issues or questions about Firebase integration, refer to:
- [Firebase Documentation](https://firebase.google.com/docs/auth)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)