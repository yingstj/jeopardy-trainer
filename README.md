# Jeopardy AI Trainer

An interactive web application for practicing Jeopardy questions with AI-powered assistance. This trainer helps users improve their trivia knowledge through spaced repetition, performance tracking, and intelligent question selection.

## Features

- **Adaptive Learning AI**: Intelligent question selection based on your performance patterns
- **Personalized Difficulty**: AI adjusts question difficulty to maintain optimal challenge level
- **Spaced Repetition**: Scientific algorithm for long-term retention
- **Performance Analytics**: Detailed statistics by category, difficulty, and time
- **Learning Insights**: AI-generated recommendations and study plans
- **Multiple Learning Modes**: Adaptive, Review, Challenge, Practice, and Weakness-focused
- **Progress Visualization**: Track improvement over time with charts and metrics
- **Data Scraping**: Automatically fetch new questions from online sources
- **Multi-user Support**: Individual progress tracking for each user

## Project Structure

```
jay-jeopardy-ai-trainer/
├── app.py                 # Main Flask application
├── auth.py               # User authentication system
├── database.py           # Database management and queries
├── ai_engine.py          # Adaptive learning AI algorithm
├── data_processor.py     # Question processing and difficulty rating
├── requirements.txt      # Python dependencies
├── static/              # Static assets
│   ├── css/            # Stylesheets
│   ├── js/             # JavaScript files
│   └── images/         # Images and icons
├── templates/           # HTML templates
│   ├── base.html       # Base template
│   ├── landing.html    # Landing page
│   ├── login.html      # Login page
│   ├── register.html   # Registration page
│   ├── profile.html    # User profile
│   └── jeopardy_trainer.html # Main game interface
├── scripts/             # Utility scripts
│   └── scraper_final.py # Web scraper for questions
└── data/               # Database and data files
    └── jeopardy.db     # SQLite database
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Internet connection for downloading questions

### Installation

1. **Clone the repository** (or create the directory):
   ```bash
   cd ~/jay-jeopardy-ai-trainer
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**:
   ```bash
   python -c "from database import JeopardyDatabase; JeopardyDatabase()"
   ```

5. **Load initial questions** (choose one method):
   
   a. Fetch recent games:
   ```bash
   python data_processor.py --fetch
   ```
   
   b. Fetch specific seasons:
   ```bash
   python data_processor.py --fetch --seasons 38 39 40
   ```
   
   c. Load from existing JSON file:
   ```bash
   python data_processor.py --load-file data/questions.json
   ```

## Running the Application

1. **Start the Flask server**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

3. The application will automatically create a session for tracking your progress.

## Usage Guide

### Main Interface

- **Category Selection**: Choose specific categories or play with all categories
- **Difficulty Level**: Select Easy (≤$400), Medium ($400-$800), or Hard (>$800)
- **Question Count**: Choose how many questions per session
- **Answer Input**: Type your answer and submit
- **AI Assistance**: Request hints or explanations when stuck

### Keyboard Shortcuts

- `Enter`: Submit answer
- `Space`: Show/hide answer
- `N`: Next question
- `H`: Get hint
- `S`: Skip question

### API Endpoints

- `GET /`: Main application page
- `GET /api/questions`: Fetch questions with filters
- `GET /api/categories`: List all available categories
- `POST /api/progress`: Save answer and track performance
- `GET /api/stats`: Get session statistics
- `POST /api/load_questions`: Upload new questions

### Data Management

1. **Update question database**:
   ```bash
   # Fetch new questions
   python data_processor.py --fetch
   
   # Load questions from JSON file
   python data_processor.py --load-file data/questions_sample.json
   
   # Update difficulty ratings based on user performance
   python data_processor.py --update-difficulty
   
   # Initialize database (for Railway deployment)
   python init_db.py
   ```

2. **View database statistics**:
   ```bash
   python data_processor.py --stats
   ```

3. **Backup database**:
   ```bash
   cp data/jeopardy.db data/jeopardy_backup_$(date +%Y%m%d).db
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///data/jeopardy.db  # For local development
# DATABASE_URL=postgresql://user:password@host:port/dbname  # For Railway deployment
```

### Database Configuration

The application supports both SQLite (for local development) and PostgreSQL (for production deployment on Railway):

- **SQLite (Local)**: Default configuration, no additional setup required
- **PostgreSQL (Railway)**: Automatically detected when `DATABASE_URL` environment variable is set

### Application Settings

Modify `app.py` to change:
- Port number (default: 5000)
- Debug mode (default: True in development)
- Session timeout
- Question selection algorithm parameters

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
flake8 .
```

### Adding New Features

1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Submit pull request

## Troubleshooting

### Common Issues

1. **Database errors**:
   ```bash
   # Reset database
   rm data/jeopardy.db
   python -c "from database import JeopardyDatabase; JeopardyDatabase()"
   ```

2. **Missing questions**:
   ```bash
   # Re-fetch questions
   python data_processor.py --fetch
   ```

3. **Port already in use**:
   ```bash
   # Use different port
   python app.py --port 5001
   ```

### Performance Optimization

- **Large database**: Create indexes on frequently queried columns
- **Slow loading**: Enable caching in Flask configuration
- **Memory issues**: Implement pagination for large result sets

## AI Adaptive Learning System

The Jeopardy AI Trainer uses an advanced adaptive learning algorithm that personalizes your experience:

### How It Works

1. **Performance Analysis**: Tracks your accuracy, response time, and patterns across categories
2. **Difficulty Calibration**: Adjusts question difficulty to maintain ~75% success rate for optimal learning
3. **Spaced Repetition**: Uses forgetting curve algorithms to schedule question reviews
4. **Weakness Detection**: Identifies struggling categories and increases their frequency
5. **Learning Modes**:
   - **Adaptive**: Full AI algorithm for personalized learning
   - **Review**: Focus on previously seen questions using spaced repetition
   - **Challenge**: Slightly harder questions to push your limits
   - **Practice**: Random questions at your current level
   - **Weakness**: Intensive practice on your weakest categories

### API Endpoints

- `GET /api/ai/questions` - Get AI-recommended questions
- `GET /api/ai/insights` - Get personalized learning insights
- `POST /api/ai/update` - Update AI parameters after answering

### Testing the AI Engine

```bash
python test_ai_engine.py
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Future Enhancements

- [ ] Multiplayer mode
- [ ] Voice input support
- [ ] Mobile app version
- [ ] Advanced AI explanations
- [ ] Custom question sets
- [ ] Tournament mode
- [ ] Social features (leaderboards, sharing)
- [ ] Offline mode with cached questions

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Jeopardy question data sourced from publicly available archives
- Built with Flask web framework
- UI inspired by the classic Jeopardy game show
- AI integration powered by Claude API

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Contact: [your-email@example.com]
- Documentation: [link-to-docs]

---

**Note**: This is an educational project. Jeopardy! is a registered trademark of Jeopardy Productions, Inc.