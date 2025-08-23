#!/bin/bash

echo "🚀 Deploying Google Auth Helper to Firebase Hosting"
echo ""
echo "This script will deploy your authentication page to Firebase."
echo ""

# Check if firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo "❌ Firebase CLI is not installed"
    echo "Installing Firebase CLI..."
    npm install -g firebase-tools
fi

echo "📝 Step 1: Login to Firebase"
echo "You'll be redirected to your browser to authenticate."
firebase login

echo ""
echo "🎯 Step 2: Deploying to Firebase Hosting"
firebase deploy --only hosting

echo ""
echo "✅ Deployment complete!"
echo "Your Google Sign-In page is now available at:"
echo "https://jaypardy-53a55.web.app/google_auth_helper.html"
echo ""
echo "Test it by visiting the link above!"