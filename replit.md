# WordPress Code Review Bot

## Overview

This application is a Flask-based webhook service that automatically reviews WordPress code changes in Bitbucket pull requests using Google Gemini AI. The bot receives webhook events from Bitbucket, fetches the code diff, and provides automated code review feedback focusing on WordPress coding standards, security vulnerabilities, performance, and best practices.

**Status**: Fully operational and actively processing real pull requests from the translatepress repository.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Flask with Jinja2 templating
- **UI Framework**: Bootstrap 5 with dark theme
- **Icons**: Font Awesome 6.0
- **Styling**: Custom CSS with responsive design
- **Layout**: Single-page dashboard with real-time webhook event display

### Backend Architecture
- **Web Framework**: Flask (Python)
- **Application Structure**: Modular design with separate webhook handler
- **Logging**: Python's built-in logging module with DEBUG level
- **Session Management**: Flask sessions with secret key configuration
- **Error Handling**: Try-catch blocks with appropriate HTTP status codes

### API Integration
- **Bitbucket API**: REST API integration for fetching pull request diffs
- **Google Gemini AI**: Generative AI for code analysis and review
- **Authentication**: HTTP Basic Auth for Bitbucket API access

## Key Components

### Core Application (`app.py`)
- **Main Flask Application**: Handles routing and request processing
- **Dashboard Route**: Displays recent webhook events in a web interface
- **Webhook Endpoint**: Receives and processes Bitbucket webhook payloads
- **Event Storage**: In-memory storage for recent webhook events (last 10 events)

### Webhook Handler (`webhook_handler.py`)
- **Diff Fetching**: Retrieves pull request diffs from Bitbucket API
- **AI Analysis**: Sends code diffs to Gemini AI for WordPress-specific review
- **Code Review Focus**: WordPress coding standards, security, performance, and best practices
- **Error Handling**: Robust error handling for API failures and timeouts

### User Interface
- **Base Template**: Responsive navigation with dark theme
- **Dashboard**: Real-time display of webhook events and system status
- **Status Cards**: Visual indicators for webhook, AI, and Bitbucket integration status

## Data Flow

1. **Webhook Reception**: Bitbucket sends POST request to `/webhook` endpoint
2. **Event Processing**: Extract PR information and store in recent events
3. **Diff Retrieval**: Fetch code diff from Bitbucket API using authenticated request
4. **AI Analysis**: Send diff to Gemini AI with WordPress-specific prompts
5. **Review Generation**: Receive structured feedback on code quality and security
6. **Dashboard Update**: Display processed events in real-time web interface

## External Dependencies

### Required Environment Variables
- `BITBUCKET_EMAIL`: Atlassian account email for API authentication
- `BITBUCKET_API_TOKEN`: Bitbucket API token for repository access
- `GEMINI_API_KEY`: Google Gemini AI API key for code analysis
- `SESSION_SECRET`: Flask session secret key (optional, defaults to dev key)

### Third-Party Services
- **Bitbucket**: Source code repository and webhook provider
- **Google Gemini AI**: Large language model for code analysis
- **Bootstrap CDN**: UI framework and styling
- **Font Awesome CDN**: Icon library

### Python Dependencies
- `flask`: Web framework
- `requests`: HTTP client for API calls
- `google-genai`: Google Gemini AI client library
- `logging`: Built-in Python logging
- `datetime`: Built-in Python datetime handling

## Deployment Strategy

### Development Setup
- **Entry Point**: `main.py` runs Flask development server
- **Host Configuration**: Binds to `0.0.0.0:5000` for external access
- **Debug Mode**: Enabled for development with auto-reload

### Production Considerations
- **Environment Variables**: All sensitive credentials stored as environment variables
- **Error Handling**: Comprehensive error handling with appropriate HTTP status codes
- **Logging**: Structured logging for debugging and monitoring
- **Security**: Secret key management and API token protection

### Webhook Configuration
- **Endpoint**: `/webhook` accepts POST requests with JSON payloads
- **Event Filtering**: Processes pull request events from Bitbucket
- **Response Handling**: Returns appropriate HTTP status codes and JSON responses

The application is designed to be lightweight, focused on WordPress code review automation, and easily deployable in cloud environments like Replit.

## Recent Changes

### 2025-07-22 - Webhook Timeout and Deduplication Fix
- **Duplicate Prevention**: Implemented intelligent webhook deduplication using PR ID + timestamp
- **Timeout Resolution**: Added asynchronous processing to respond quickly and prevent Bitbucket timeouts
- **Update Handling**: System correctly distinguishes between webhook retries (skipped) and PR updates (processed)
- **Improved Logging**: Enhanced logging to clearly show when webhooks are duplicates vs legitimate updates

### 2025-07-10 - Full System Deployment and Testing
- **Webhook Integration**: Successfully resolved 301 redirect issues and established working webhook endpoint
- **Event Persistence**: Implemented file-based storage for webhook events to persist across application restarts
- **Live Testing**: Confirmed bot is processing real pull requests from translatepress repository
- **Gemini AI Integration**: Verified 4,000-5,000 character analysis responses with WordPress-specific feedback
- **Comment Posting**: Confirmed automated posting of AI analysis back to Bitbucket pull requests
- **Dashboard Enhancement**: Added persistent event display and sample data for better user experience