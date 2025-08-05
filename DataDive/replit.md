# Venezuelan Dollar Bot

## Overview

The Venezuelan Dollar Bot is a Telegram bot application that automatically fetches and reports Venezuelan dollar exchange rates. The bot runs on Python and provides both automated scheduled updates and manual rate queries. It includes a web dashboard for monitoring bot status and viewing rate history.

## System Architecture

### Core Components
- **Telegram Bot**: Built using pyTelegramBotAPI, handles user interactions and sends automated rate updates
- **Rate Fetcher**: Retrieves exchange rates from PyDolarVe API
- **Data Storage**: Local JSON-based storage system for rate history and persistence
- **Web Interface**: Flask-based dashboard for monitoring and administration
- **Scheduler**: Background threading system for automated rate updates

### Technology Stack
- **Backend**: Python 3.11
- **Bot Framework**: pyTelegramBotAPI
- **Web Framework**: Flask
- **HTTP Client**: requests library
- **Data Storage**: JSON files (file-based persistence)
- **Frontend**: HTML/CSS with Bootstrap 5 and Font Awesome icons

## Key Components

### 1. Main Bot Logic (`main.py`)
- **Purpose**: Core bot functionality and rate fetching
- **Key Features**:
  - Fetches rates from PyDolarVe API (BCV official + P2P markets)
  - Calculates average rates and detects significant changes (>2%)
  - Handles bot commands and automated messaging
  - Implements error handling and logging

### 2. Rate Storage (`rate_storage.py`)
- **Purpose**: Persistent data management
- **Features**:
  - JSON-based storage for rate history
  - Previous rate comparison functionality
  - Data integrity and error recovery
  - Statistics tracking for the web interface

### 3. Web Interface (`web_interface.py`)
- **Purpose**: Administrative dashboard
- **Features**:
  - Real-time bot status monitoring
  - Rate history visualization
  - RESTful API endpoints for status data
  - Bootstrap-based responsive UI

### 4. Application Runner (`run.py`)
- **Purpose**: Application orchestration
- **Features**:
  - Environment variable validation
  - Multi-threaded execution (bot + web server)
  - Centralized logging configuration
  - Graceful error handling and startup validation

## Data Flow

1. **Rate Fetching Process**:
   - Bot queries PyDolarVe API for BCV official rate
   - Fetches P2P market rates from multiple sources
   - Calculates weighted average including all sources
   - Stores current rate and compares with previous day

2. **Notification Logic**:
   - Scheduled daily updates at 9:00 AM (weekdays only)
   - Immediate alerts for rate changes >2%
   - Manual rate queries via `/tasas` command

3. **Data Persistence**:
   - Current and historical rates stored in `rates_data.json`
   - Previous rate comparison for change detection
   - Rate history maintained for trend analysis

## External Dependencies

### APIs
- **PyDolarVe API**: Primary data source for Venezuelan exchange rates
  - BCV official rate endpoint (USD and EUR)
  - P2P market rates endpoint
  - Provides rounded prices in Venezuelan Bolívars
- **CLP Today**: Secondary data source for enhanced Zelle/PayPal accuracy
  - Web scraping integration using Trafilatura
  - Fallback to calculated rates when unavailable

### Services
- **Telegram Bot API**: Message delivery and bot interactions
- **Environment Variables**: Configuration management (TOKEN, CHAT_ID)

### Python Packages
- `pyTelegramBotAPI`: Telegram bot framework
- `requests`: HTTP client for API calls
- `flask`: Web framework for dashboard
- `trafilatura`: Web content extraction for CLP Today scraping
- Standard library: `json`, `datetime`, `threading`, `logging`, `os`

## Deployment Strategy

### Environment Configuration
- **TOKEN**: Telegram bot token from BotFather
- **CHAT_ID**: Target Telegram chat/channel ID
- **PORT**: Web interface port (default 5000)

### Replit Deployment
- **Runtime**: Python 3.11 with Nix package management
- **Startup Command**: `pip install pyTelegramBotAPI requests flask && python run.py`
- **Architecture**: Single-process application with threading
- **Storage**: Local file system for persistence

### Execution Model
- **Multi-threaded**: Bot polling and web server run concurrently
- **Always-on**: Designed for continuous operation
- **Auto-restart**: Replit workflow handles process management

## Changelog
- June 19, 2025: Initial setup with PyDolarVe API integration
- June 19, 2025: Added CLP Today web scraping for enhanced Zelle/PayPal rates
- June 19, 2025: Integrated Euro (EUR) exchange rates from PyDolarVe
- June 19, 2025: Enhanced interactive keyboard buttons for improved user experience

## User Preferences

Preferred communication style: Simple, everyday language.