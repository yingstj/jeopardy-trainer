# Jaypardy! AI Trainer - Project Documentation

## Overview
Jaypardy! is a Jeopardy training application with AI opponents, deployed on Streamlit Cloud at jaypardy.streamlit.app. The app features 577k+ real Jeopardy questions, multiple game modes, AI opponents with different personalities, and Firebase authentication.

## Quick Commands
```bash
# Run locally
streamlit run app.py

# Deploy to Firebase (for Google Auth helper)
./deploy_to_firebase.sh

# Run tests
python3 jeopardy_answer_checker.py
python3 test_ai_engine.py
```

## Architecture

### Core Files
- **app.py** - Main Streamlit application with AI features
- **ai_opponent.py** - AI opponent logic with 5 personalities
- **jeopardy_answer_checker.py** - Smart answer validation (CRITICAL: prevents false positives)
- **firebase_auth_streamlit.py** - Singleton Firebase auth helper
- **google_auth_helper.html** - OAuth workaround for Streamlit

### Data Files
- **data/all_jeopardy_clues.csv** - 577k questions (main dataset)
- **data/questions_sample.json** - 1000 question backup
- **data/jeopardy_questions_fixed.json** - 220 question fallback

### Game Modes
1. **Solo Practice** - Train at your own pace
2. **vs AI Opponent** - Battle against 5 AI personalities
3. **Category Focus** - Master specific categories

### AI Personalities
- **Ken Jennings** - History/Literature expert (85% base accuracy)
- **Watson** - Science/Tech master (90% base accuracy)
- **Brad Rutter** - Pop Culture specialist (82% base accuracy)
- **James Holzhauer** - Sports/Geography expert (88% base accuracy)
- **Balanced** - Average player (75% base accuracy)

## Critical Bug Fixes Applied

### 1. Answer Checker Bug (FIXED)
**Problem**: Substring matching caused false positives ("car" matched "carburetor")
**Solution**: Implemented word boundary checking in `jeopardy_answer_checker.py`
```python
# Now properly validates answers with:
- Word boundary detection
- Last name matching (Washington → George Washington)
- Abbreviation support (JFK → John F. Kennedy)
- Alternative answers (Zimbabwe (or Rhodesia))
```

### 2. Firebase Multiple Init (FIXED)
**Problem**: Multiple Firebase initialization attempts caused crashes
**Solution**: Singleton pattern in `firebase_auth_streamlit.py`
```python
# Thread-safe singleton ensures single initialization
FirebaseAuthHelper._instance = None
FirebaseAuthHelper._lock = threading.Lock()
```

### 3. Data Loading (FIXED)
**Problem**: Only loading 220 questions instead of 577k
**Solution**: Prioritized CSV loading with proper column mapping
```python
paths_to_try = [
    "data/all_jeopardy_clues.csv",  # 577k questions - prioritized
    # ... fallback options
]
```

## Deployment

### Streamlit Cloud
- **URL**: https://jaypardy.streamlit.app
- **Auto-deploy**: Pushes to main branch trigger automatic deployment
- **Secrets**: Configure in Streamlit Cloud dashboard
  ```toml
  [firebase]
  project_id = "jaypardy-53a55"
  private_key = "-----BEGIN PRIVATE KEY-----\n..."
  client_email = "..."
  ```

### Firebase Hosting (for Google Auth)
```bash
# Deploy authentication helper
firebase login
firebase deploy --only hosting
# Available at: https://jaypardy-53a55.web.app/google_auth_helper.html
```

## Security Considerations

### Current Issues
1. **Firebase private key was exposed in commits** - Needs regeneration
2. **Use environment variables for all secrets**
3. **Implement rate limiting for answer checking**

### Best Practices
- Never commit credentials
- Use Streamlit secrets for sensitive data
- Validate all user inputs
- Implement session timeouts

## Performance Optimizations

### Implemented
- Question caching with `@st.cache_data`
- Singleton Firebase authentication
- Efficient answer checking algorithm

### TODO
- Implement question pagination (load in chunks)
- Add database connection pooling
- Optimize embedding computations (batch processing)
- Add Redis caching for frequently accessed questions

## Testing

### Answer Checker Tests
```bash
python3 jeopardy_answer_checker.py
# Should show all tests passing
```

### Manual Testing Checklist
- [ ] Answer validation (no false positives)
- [ ] Firebase auth flow
- [ ] AI opponent buzzer timing
- [ ] Daily Double wagering
- [ ] Score persistence
- [ ] Category filtering

## Known Issues & TODOs

### High Priority
1. **Regenerate Firebase credentials** (security)
2. **Add multiplayer support** (WebSocket/Firebase Realtime)
3. **Implement spaced repetition** (SuperMemo SM-2 algorithm)

### Medium Priority
1. **Add tournament mode** (bracket system)
2. **Implement voice input** (Web Speech API)
3. **Add question reporting** (flag incorrect answers)
4. **Create admin dashboard** (question management)

### Low Priority
1. **Add achievements system**
2. **Implement leaderboards**
3. **Add sound effects**
4. **Create mobile app**

## Development Guidelines

### Code Style
- Use type hints for function parameters
- Add docstrings to all functions
- Follow PEP 8 conventions
- Keep functions under 50 lines

### Git Workflow
```bash
# Always test before committing
python3 jeopardy_answer_checker.py

# Use descriptive commit messages
git commit -m "Fix: [component] - description"

# Don't commit:
- Credentials or API keys
- Large data files (>100MB)
- Debug/test files
- Personal configuration
```

### Adding New Features
1. Create feature branch
2. Implement with tests
3. Update this documentation
4. Test locally with `streamlit run app.py`
5. Merge to main for auto-deployment

## API Keys & Services

### Firebase
- **Project**: jaypardy-53a55
- **Services**: Authentication, Hosting
- **Dashboard**: https://console.firebase.google.com/project/jaypardy-53a55

### Streamlit Cloud
- **App**: jaypardy.streamlit.app
- **Dashboard**: https://share.streamlit.io/
- **Secrets**: Configure in dashboard settings

## Troubleshooting

### Common Issues

**"No questions loaded"**
- Check data/ directory exists
- Verify CSV file integrity
- Check file permissions

**"Firebase auth failed"**
- Verify secrets in Streamlit Cloud
- Check Firebase project settings
- Ensure private key is properly formatted

**"Answer always wrong"**
- Check JeopardyAnswerChecker is imported
- Verify answer normalization
- Test with exact matches first

**"AI never buzzes in"**
- Check difficulty settings
- Verify buzzer timing logic
- Test with Easy difficulty

## Support & Resources

### Documentation
- [Streamlit Docs](https://docs.streamlit.io)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Original Jeopardy Archive](https://j-archive.com)

### Contact
- GitHub Issues: https://github.com/yingstj/jeopardy-trainer/issues
- Streamlit Community: https://discuss.streamlit.io

## Version History

### v2.0 (Current)
- Added AI opponents with 5 personalities
- Implemented smart answer checking
- Fixed critical bugs (substring matching, Firebase init)
- Added 577k question dataset

### v1.0
- Basic Jeopardy game
- Firebase authentication
- Simple scoring system

---

Last Updated: August 2025
Maintained by: @yingstj