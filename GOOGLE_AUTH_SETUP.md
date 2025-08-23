# 🔷 Setting Up Google Sign-In for Jaypardy

## Quick Setup (2 Options)

### Option 1: Deploy to Firebase Hosting (Recommended)

1. **Install Firebase CLI:**
```bash
npm install -g firebase-tools
```

2. **Initialize Firebase Hosting:**
```bash
firebase init hosting
```
- Choose your project: `jaypardy-53a55`
- Public directory: `.` (current directory)
- Single-page app: No
- Set up automatic builds: No

3. **Deploy the auth helper:**
```bash
firebase deploy --only hosting
```

4. **Your Google Sign-In page will be at:**
```
https://jaypardy-53a55.web.app/google_auth_helper.html
```

### Option 2: Use GitHub Pages

1. **Create a new repository** called `jaypardy-auth`

2. **Upload `google_auth_helper.html`** to the repository

3. **Enable GitHub Pages:**
- Go to Settings → Pages
- Source: Deploy from branch
- Branch: main
- Folder: / (root)

4. **Your Google Sign-In page will be at:**
```
https://[your-username].github.io/jaypardy-auth/google_auth_helper.html
```

## How It Works

1. **User clicks the link** in the Streamlit app
2. **Opens Google Sign-In page** in new tab
3. **User signs in with Google**
4. **Page displays authentication token**
5. **User copies token** and pastes in Streamlit app
6. **Streamlit verifies token** with Firebase Admin SDK

## Testing Locally

1. **Start a local server:**
```bash
python -m http.server 8000
```

2. **Open in browser:**
```
http://localhost:8000/google_auth_helper.html
```

## Security Notes

✅ **Secure:** The token is a Firebase ID token, not a password
✅ **Time-limited:** Tokens expire after 1 hour
✅ **Verified:** Streamlit app verifies token with Firebase Admin SDK
✅ **No secrets exposed:** Only public Firebase config is in HTML

## Troubleshooting

### "Permission Denied" Error
- Go to Firebase Console → Authentication → Settings
- Add your domain to Authorized domains:
  - `jaypardy-53a55.web.app`
  - `jaypardy-53a55.firebaseapp.com`
  - Your GitHub Pages domain (if using)

### Token Not Working
- Make sure Firebase Admin SDK is initialized in Streamlit
- Check that secrets are properly configured
- Token may have expired (they last 1 hour)

### Google Sign-In Not Working
- Enable Google provider in Firebase Console:
  - Authentication → Sign-in method → Google → Enable
  - Add your email as support email

## Alternative: Direct Integration

For a smoother experience, consider using:
- **Firebase UI**: Pre-built auth UI
- **Custom OAuth flow**: Direct Google OAuth implementation
- **Auth0 or Clerk**: Third-party auth services with better Streamlit integration