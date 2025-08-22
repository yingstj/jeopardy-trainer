# URGENT: Security Fix Instructions

## ⚠️ IMPORTANT: Your Firebase private key was exposed in the git history

Follow these steps immediately to secure your repository:

## Step 1: Create Local .env File (DO NOT COMMIT THIS)

Create a file named `.env` in your project root with your actual credentials:

```bash
# Firebase Configuration
FIREBASE_PROJECT_ID=jaypardy-53a55
FIREBASE_API_KEY=AIzaSyD7OcmmwWY6zV4ngPHjsdwxvoXJ41r55UM
FIREBASE_AUTH_DOMAIN=jaypardy-53a55.firebaseapp.com
FIREBASE_STORAGE_BUCKET=jaypardy-53a55.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=367259134434
FIREBASE_APP_ID=1:367259134434:web:5728976d5fba3ef022b1bb
FIREBASE_DATABASE_URL=https://jaypardy-53a55-default-rtdb.firebaseio.com

# Firebase Service Account (KEEP THESE SECRET!)
FIREBASE_TYPE=service_account
FIREBASE_PRIVATE_KEY_ID=a75a781f4d379470e4f8bd6f079ffe84aeaeeb99
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCuDuSr5rUu3Jc/\nPj8OBdcmlscgWargbDyVZUmKNnp6KU10vZ/3yY5wP7bRkkN+25UEHiew8d0TLFVr\n3etpiYPlmntWoxi67XHEqdkd4OcltIJ42LFoIQNCF0HQudhh8Mz06gf9BVfxZTEt\n1yfm6goZN8jHJ4O08DxXr5og9XnaX3vt77mJAqi1fxQFEcH0RqzXf/FB19KOcCAE\nn9gP82KmRDhWiYaOTeROZShWRQevr5vQN9Rjc/Da0tiGIobBs7d0gtqpMh1lP9cM\nw7Xn7zIZHxQwZIHE0AM38wNREjpEPjdqdeW/QnBbkcCF8bV1JaBpFNPDv9rK7QjT\n5/zc0rEJAgMBAAECggEABWXK1kCE9TC8CVG0gjUmKI6GcEy3jYFtw4hCO+StRE/h\nlLGIs2tvB7DCH5pJ44uLAcyu7cAiW0TbBUmlfOlZy2tQpdglnS5d19EYkuJK6L1s\nn7NrP6UTxR8+2D/bI6EPCg1JNXcj9LAZp/1DFy3CJb64HYzuev70MBfu+f9YHwXH\n1p3l8YeSkVY7f8459iWzRHOz6TrvO95Qro+HDeTE3j8jHjZErxKIk7S3g3J+opBv\nhiCi/loL208KRrkkCfzip93j9orFt0E1zDLd0ai1z5LHfGKnRzroOBwdnQl4BGfv\nVLnFWAenhQozJ1vbcAs0Djd6eyUfqjuoirtQvb338QKBgQDrIo1UYWn7P3xJfc+Y\n4RMPtwJmUZmyvGNjSi+ZK55yDLXgnk7x9fcKME7xULcb26AJMbzCP25XvgVpmKzH\nMu1icMA2tgsC/O2hI8IvlrmEhbi51NEWPrsR4bXyjHSekF3BiLnTJjU/vPc0WSle\nJq0pjQ9OJEjpv/Sg3+K0IfqQ5QKBgQC9gOOa7eHO5Q1PCYoSsL2eHY4VC4MiyNPG\nO7FVWCgVtxKkeLHMD2Oz1h/i8PqzjqVf06i9CGOKaf05zP4noSIJV3/RM0JyXmEc\nFAB5BlzV4/EzCU3YtPV6rVI4YqXJ/TGSee2GjStPWeenpgrKnh/w/cEpbEoJ2s+/\niGG5SsXxVQKBgDlvDyZ1RPXh4/HvkS2+jHFiOmvTsr891OkDzeyUAvfIswRSpuXj\nNpx+gEnhdViQpN6aD4lDBSjZeWj5qfpeLi3FbK3weXAZZ9Hccio9nsMIBr8dhJTy\nba9IerDsLfAtQzlqtDknNAqFlbxrqvcca1+i3QIxSr4N7Sr+hNmLEzEhAoGAHkcE\nlpFhXbQdDz6/78KLWULxm40uU5VwuKB68d7W8LlCYkLibW8cB/SzPYgxFhU5ePkR\nYbqAZPIQQnbtOJm3HXT8eAlPmYRY0aqkdLG+jXIQ7I2VAYXQHtyoYVfpkz8/915B\nxBi0DcaYi6Gs4bin89InVZ32qmJqhPieXIOE4s0CgYAJDifKLT2FIG1Xt5Z4QBAt\nlWjgiMsBVJbXpIb6m3cfiGz65xCw7M6Yrk6dM12a/v2wXNjK8j32MyMbRNu7pFi1\nUxtkAg+DLaTn6KcsvoIMXdcY3ZAhNjvipP4wQ1hIapOVmKPs4xCS3jkHkG8AHBgM\nyEGvow9J0piD9eXAUcgszg==\n-----END PRIVATE KEY-----"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-fbsvc@jaypardy-53a55.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=103074607908039161794
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_CERT=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40jaypardy-53a55.iam.gserviceaccount.com

# Flask Configuration
FLASK_SECRET_KEY=your-very-secure-random-key-here
```

## Step 2: Commit the Clean Version

```bash
git add firebase_config.py requirements.txt
git commit -m "Security: Remove hardcoded secrets from firebase_config.py"
```

## Step 3: Remove Secrets from Git History

### Option A: If this is a PRIVATE repository that you haven't shared:

```bash
# Use BFG Repo-Cleaner (recommended)
# First, install BFG if you haven't already
brew install bfg  # On macOS

# Clean the repository
bfg --replace-text <(echo "AIzaSyD7OcmmwWY6zV4ngPHjsdwxvoXJ41r55UM==>REMOVED") .
bfg --replace-text <(echo "a75a781f4d379470e4f8bd6f079ffe84aeaeeb99==>REMOVED") .
bfg --delete-files firebase_config.py

# Clean up
git reflog expire --expire=now --all && git gc --prune=now --aggressive

# Force push (WARNING: This rewrites history!)
git push --force
```

### Option B: If this is a PUBLIC repository or has been shared:

Since the credentials have been exposed, you MUST:

1. **Regenerate your Firebase service account key immediately:**
   - Go to https://console.firebase.google.com/project/jaypardy-53a55/settings/serviceaccounts/adminsdk
   - Click "Generate New Private Key"
   - Download the new JSON file
   - Update your `.env` file with the new credentials

2. **Consider the current credentials compromised**
   - The private key in this repository should be considered leaked
   - Anyone who has accessed this repository has had access to these credentials

3. **For the repository:**
   ```bash
   # Create a new branch from the clean state
   git checkout -b security-fix
   
   # Commit the clean files
   git add .
   git commit -m "Security: Remove all hardcoded secrets"
   
   # Push the new branch
   git push origin security-fix
   
   # Create a pull request and merge it
   # Then delete the old branches with exposed secrets
   ```

## Step 4: Set Up Environment Variables for Deployment

### For Local Development:
- Keep the `.env` file in your project root
- Never commit it to git

### For Railway Deployment:
1. Go to your Railway project dashboard
2. Click on your service
3. Go to Variables tab
4. Add each environment variable from your `.env` file

### For Vercel Deployment:
1. Go to your Vercel project settings
2. Navigate to Environment Variables
3. Add each variable from your `.env` file

### For Heroku:
```bash
heroku config:set FIREBASE_API_KEY="your-api-key"
heroku config:set FIREBASE_PRIVATE_KEY="your-private-key"
# ... add all other variables
```

## Step 5: Security Best Practices Going Forward

1. **Never commit `.env` files**
2. **Always use environment variables for secrets**
3. **Use `.env.example` files with dummy values for documentation**
4. **Regularly rotate your credentials**
5. **Use secret scanning tools in your CI/CD pipeline**
6. **Enable GitHub secret scanning alerts**

## Step 6: Enable GitHub Secret Scanning

1. Go to your repository settings
2. Navigate to "Code security and analysis"
3. Enable "Secret scanning"
4. Enable "Push protection" to prevent future accidents

## Remember:
- **The private key that was exposed should be considered compromised**
- **Generate a new service account key immediately**
- **Monitor your Firebase usage for any unauthorized access**
- **Check Firebase audit logs for suspicious activity**

## Additional Resources:
- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [Firebase: Service Account Best Practices](https://firebase.google.com/docs/admin/setup#initialize-sdk)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)