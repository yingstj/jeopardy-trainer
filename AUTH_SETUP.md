# Authentication Setup Guide

## Overview
Jay's Jeopardy Trainer includes an authentication system that allows users to:
- Save their progress across sessions
- Track performance over time
- Use personalized adaptive training

## Quick Start (Simple Email Login)

The app works out of the box with simple email/password login. No configuration required!

1. Run the app: `streamlit run app.py`
2. Enter any email and password to create an account
3. Your progress will be saved automatically

## Google OAuth Setup (Optional)

For production use with Google sign-in:

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API

### 2. Create OAuth Credentials
1. Go to APIs & Services > Credentials
2. Click "Create Credentials" > "OAuth 2.0 Client ID"
3. Configure consent screen if prompted
4. Application type: "Web application"
5. Add authorized redirect URIs:
   - For local development: `http://localhost:8501`
   - For Streamlit Cloud: `https://your-app.streamlit.app`

### 3. Configure Secrets

#### For Local Development:
Create `.streamlit/secrets.toml`:
```toml
GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "your-client-secret"
REDIRECT_URI = "http://localhost:8501"
```

#### For Streamlit Cloud:
1. Go to your app settings
2. Click "Secrets" in the sidebar
3. Add the same configuration

## User Data Storage

User sessions are stored in the `user_data/` directory:
- Each user gets a unique ID based on their email
- Session data includes:
  - Game history
  - Scores and statistics
  - Performance by category
  - Personal settings (timer, adaptive mode)

## Testing Authentication

Run the test script to verify authentication is working:
```bash
streamlit run test_auth.py
```

This will allow you to:
- Test login/logout
- Verify session saving/loading
- Check data persistence

## Deployment Considerations

### For Public Deployment:
1. **Always use HTTPS** in production
2. Consider implementing proper password hashing (current demo accepts any password)
3. Add rate limiting for login attempts
4. Consider adding password reset functionality

### For Private/Team Use:
- The simple email login is sufficient for trusted users
- Consider using Google OAuth for better security
- Restrict access via Streamlit Cloud settings if needed

## Troubleshooting

### "OAuth not installed" Error
```bash
pip install streamlit-oauth
```

### Google OAuth Not Working
- Verify credentials in secrets.toml
- Check redirect URI matches exactly
- Ensure Google+ API is enabled

### Session Not Persisting
- Check `user_data/` directory has write permissions
- Verify email is being saved correctly
- Check browser cookies are enabled

## Security Notes

⚠️ **Current Implementation is for Demo/Development**

For production, consider:
1. Implementing proper password hashing (bcrypt, argon2)
2. Adding email verification
3. Implementing session timeouts
4. Using a proper database instead of JSON files
5. Adding CSRF protection
6. Implementing rate limiting

## Disabling Authentication

To run without authentication (original behavior):

1. Edit `app.py`
2. Comment out lines 147-152:
```python
# Check authentication
# if not st.session_state.get('authenticated', False):
#     auth.show_login_page()
#     st.stop()
# 
# Show user menu in sidebar
# auth.show_user_menu()
```

## Support

For issues or questions:
- Check the test script: `streamlit run test_auth.py`
- Review error messages in the terminal
- Ensure all dependencies are installed: `pip install -r requirements.txt`