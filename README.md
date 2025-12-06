# KUBERA - AI-Powered Stock Analysis Chatbot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-316192.svg)](https://www.postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**KUBERA** is an intelligent stock analysis chatbot specialized in Indian markets (NSE/BSE). Built with FastAPI, PostgreSQL, and Claude 3.5 Sonnet, it provides comprehensive stock analysis through AI-powered conversations.

---

## Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Database Setup](#-database-setup)
- [Running the Application](#-running-the-application)
- [API Documentation](#-api-documentation)
- [MCP Servers](#-mcp-servers)
- [WebSocket Protocol](#-websocket-protocol)
- [Background Jobs](#-background-jobs)
- [Rate Limiting](#-rate-limiting)
- [Email Notifications](#-email-notifications)
- [Docker Deployment](#-docker-deployment)
- [Development](#-development)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

---

## Features

### Core Features
- **AI-Powered Chat**: Real-time conversations with Claude 3.5 Sonnet
- **Stock Analysis**: Comprehensive analysis of NSE/BSE stocks
- **Portfolio Tracking**: Track your investments with live price updates
- **Technical Analysis**: 44 MCP tools for in-depth analysis
- **Visualizations**: Beautiful charts and graphs
- **News & Sentiment**: Real-time market news and sentiment analysis

### Authentication & Security
- **3-Step OTP Registration**: Email-based verification
- **JWT Authentication**: Secure access and refresh tokens
- **Password Security**: Bcrypt hashing with strict requirements
- **Session Management**: Automatic token refresh

### Rate Limiting
- **4-Level Fail-Fast System**:
  - Burst: 10 prompts/minute
  - Per-Chat: 50 prompts/chat
  - Hourly: 150 prompts/hour
  - Daily: 1000 prompts/24 hours

### Email Notifications
- **15+ Email Triggers**:
  - Registration OTP
  - Password reset
  - Welcome email
  - Rate limit notifications
  - Portfolio reports
  - Security alerts

### Admin Panel
- **Complete System Management**:
  - User management
  - Rate limit configuration
  - System control (start/stop)
  - Analytics dashboard
  - Activity logs

### Background Jobs
- **Automated Tasks**:
  - Portfolio price updates (every 30 mins)
  - Daily/weekly/monthly reports
  - Cleanup jobs (OTPs, tokens)

---

## Architecture

┌─────────────────────────────────────────────────────────────┐
│ CLIENT (Browser/App) │
└────────────┬────────────────────────────────┬───────────────┘
│ │
│ REST API │ WebSocket
│ │
┌────────────▼─────────────────────────────────▼───────────────┐
│ FASTAPI APPLICATION │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ API Endpoints (42) │ │
│ │ - Auth (8) - User (6) - Portfolio (5) │ │
│ │ - Chat (5) - Admin (17) - WebSocket (1) │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Business Logic Layer │ │
│ │ - Services - Validators - Formatters │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ MCP Integration │ │
│ │ - LLM Orchestrator - Tool Handler - Client │ │
│ └─────────────────────────────────────────────────────────┘ │
└────────────┬─────────────────┬─────────────────┬────────────┘
│ │ │
┌────────────▼────┐ ┌───────▼────────┐ ┌───▼─────────────┐
│ PostgreSQL │ │ MCP Servers │ │ Background │
│ (15 tables) │ │ (5 servers) │ │ Scheduler │
│ │ │ (44 tools) │ │ (APScheduler) │
└─────────────────┘ └────────────────┘ └─────────────────┘
---

## Tech Stack

### Backend
- **Framework**: FastAPI 0.109.0
- **Language**: Python 3.11+
- **ASGI Server**: Uvicorn
- **Database**: PostgreSQL 14+
- **ORM**: AsyncPG (native async)

### AI & LLM
- **LLM**: Claude 3.5 Sonnet (Anthropic)
- **Framework**: LangChain
- **Protocol**: MCP (Model Context Protocol)

### Data & Finance
- **Stock Data**: yfinance
- **Data Processing**: Pandas, NumPy
- **Visualization**: Matplotlib, Plotly

### Authentication
- **Tokens**: JWT (python-jose)
- **Hashing**: Bcrypt (passlib)
- **Validation**: Pydantic

### Background Jobs
- **Scheduler**: APScheduler
- **Email**: aiosmtplib

### DevOps
- **Containerization**: Docker, Docker Compose
- **Process Manager**: Uvicorn workers

---

## Project Structure

kubera-backend/
├── app/
│ ├── main.py # FastAPI app entry point
│ ├── core/ # Core configurations
│ │ ├── config.py
│ │ ├── security.py
│ │ └── dependencies.py
│ ├── models/ # Pydantic models
│ ├── schemas/ # Request/Response schemas
│ ├── api/ # API routes
│ │ └── routes/
│ │ ├── auth_routes.py
│ │ ├── user_routes.py
│ │ ├── portfolio_routes.py
│ │ ├── chat_routes.py
│ │ ├── admin_routes.py
│ │ └── websocket_routes.py
│ ├── services/ # Business logic
│ │ ├── auth_service.py
│ │ ├── user_service.py
│ │ ├── portfolio_service.py
│ │ ├── chat_service.py
│ │ ├── rate_limit_service.py
│ │ ├── email_service.py
│ │ └── admin_service.py
│ ├── mcp/ # MCP Integration
│ │ ├── client.py
│ │ ├── config.py
│ │ ├── tool_handler.py
│ │ └── llm_integration.py
│ ├── websocket/ # WebSocket handling
│ │ ├── connection_manager.py
│ │ ├── message_handler.py
│ │ ├── response_streamer.py
│ │ └── protocols.py
│ ├── background/ # Background jobs
│ │ ├── scheduler.py
│ │ ├── jobs/
│ │ └── tasks/
│ ├── db/ # Database
│ │ ├── database.py
│ │ ├── migrations/
│ │ └── repositories/
│ ├── utils/ # Utilities
│ │ ├── validators.py
│ │ ├── formatters.py
│ │ ├── otp_generator.py
│ │ ├── email_templates.py
│ │ └── logger.py
│ └── exceptions/ # Exception handling
│ ├── custom_exceptions.py
│ └── handlers.py
├── mcp_servers/ # 5 MCP Servers
│ ├── server1_financial_data.py
│ ├── server2_market_technical.py
│ ├── server3_governance_compliance.py
│ ├── server4_news_sentiment.py
│ └── server5_visualization.py
├── scripts/ # Setup scripts
│ ├── init_db.py
│ ├── seed_admin.py
│ ├── seed_rate_limits.py
│ └── run_migrations.py
├── logs/ # Application logs
├── .env # Environment variables
├── .env.example # Environment template
├── requirements.txt # Python dependencies
├── Dockerfile # Docker image
├── docker-compose.yml # Docker Compose
└── README.md # This file


---

## Installation

### Prerequisites
- Python 3.11 or higher
- PostgreSQL 14 or higher
- pip or poetry
- (Optional) Docker & Docker Compose

### 1. Clone Repository



git clone https://github.com/yourusername/kubera-backend.git
cd kubera-backend


### 2. Create Virtual Environment

python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate


### 3. Install Dependencies


pip install --upgrade pip
pip install -r requirements.txt


---

## Configuration

### 1. Environment Variables

Copy `.env.example` to `.env`:


cp .env.example .env

Edit `.env` and configure:

Critical settings
SECRET_KEY=your_secret_key_here
ANTHROPIC_API_KEY=sk-ant-your-api-key

Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=kubera_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=kubera_db

SMTP (for emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password


### 2. Generate Secret Key

openssl rand -hex 32


---

## Database Setup

### Method 1: Automated Script


Initialize database, run migrations, seed data
python scripts/init_db.py


### Method 2: Manual Setup

Create database
createdb kubera_db

Run migrations
python scripts/run_migrations.py migrate

Create admin user
python scripts/seed_admin.py

Configure rate limits
python scripts/seed_rate_limits.py


### Verify Setup


Check migration status
python scripts/run_migrations.py status

List admins
python scripts/seed_admin.py list
---

## Running the Application

### Development Mode

With auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
### Production Mode

Multi-worker
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

### With run.py

python run.py
### Access Application

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/health

---

## API Documentation

### Authentication Endpoints (8)

POST /auth/register/step1 # Send OTP
POST /auth/register/step2 # Verify OTP
POST /auth/register/step3 # Complete registration
POST /auth/login # Login
POST /auth/refresh # Refresh token
POST /auth/logout # Logout
POST /auth/password-reset/request # Request reset
POST /auth/password-reset/confirm # Confirm reset
### User Endpoints (6)


GET /users/me # Get profile
PUT /users/me # Update profile
PUT /users/me/username # Change username
PUT /users/me/password # Change password
GET /users/me/preferences # Get preferences
PUT /users/me/preferences # Update preferences


### Portfolio Endpoints (5)

GET /portfolio # Get portfolio
POST /portfolio # Add stock
PUT /portfolio/{portfolio_id} # Update stock
DELETE /portfolio/{portfolio_id} # Remove stock
POST /portfolio/update-prices # Update prices


### Chat Endpoints (5)

GET /chats # List chats
POST /chats # Create chat
GET /chats/{chat_id} # Get chat with messages
PUT /chats/{chat_id} # Rename chat
DELETE /chats/{chat_id} # Delete chat


### Admin Endpoints (17)

POST /admin/login/send-otp # Send OTP
POST /admin/login/verify-otp # Verify OTP
GET /admin/dashboard # Dashboard stats
GET /admin/users # List users
GET /admin/users/{user_id} # Get user
PUT /admin/users/{user_id}/status # Update status
GET /admin/rate-limits # Get config
PUT /admin/rate-limits # Update config
GET /admin/rate-limits/violations # List violations
GET /admin/system/status # System status
POST /admin/system/start # Start system
POST /admin/system/stop # Stop system
GET /admin/portfolio-reports/config # Report config
PUT /admin/portfolio-reports/config # Update config
POST /admin/portfolio-reports/send # Send reports
GET /admin/activity-logs # Activity logs
GET /admin/analytics # Analytics


### WebSocket (1)


WS /ws/chat?token={jwt_token} # Real-time chat
---

## MCP Servers

KUBERA uses 5 specialized MCP servers with 44 tools:

### Server 1: Financial Data (7 tools)
- get_stock_info
- get_company_profile
- get_fundamentals
- get_financial_ratios
- get_valuation_metrics
- get_dividend_info
- search_stocks

### Server 2: Technical Analysis (9 tools)
- get_technical_indicators
- get_chart_patterns
- get_support_resistance
- get_moving_averages
- get_rsi
- get_macd
- get_bollinger_bands
- get_volume_analysis
- get_price_action

### Server 3: Governance (8 tools)
- get_corporate_actions
- get_shareholding_pattern
- get_promoter_holdings
- get_institutional_holdings
- get_board_of_directors
- get_corporate_announcements
- get_annual_reports
- get_quarterly_results

### Server 4: News & Sentiment (9 tools)
- get_stock_news
- get_market_news
- get_sector_news
- get_sentiment_analysis
- get_social_sentiment
- get_analyst_ratings
- get_insider_trading
- get_trending_stocks
- get_market_movers

### Server 5: Visualization (11 tools)
- create_price_chart
- create_candlestick_chart
- create_technical_chart
- create_volume_chart
- create_comparison_chart
- create_sector_performance_chart
- create_portfolio_pie_chart
- create_correlation_heatmap
- create_returns_histogram
- create_drawdown_chart
- export_chart

---

## WebSocket Protocol

### Connect

const ws = new WebSocket('ws://localhost:8000/ws/chat?token=YOUR_JWT_TOKEN');

### Client -> Server Messages

// Send message
{
"type": "message",
"chat_id": "uuid",
"message": "Analyze INFY stock"
}

// Ping
{
"type": "ping"
}

### Server -> Client Messages


// Text chunk (streaming)
{
"type": "text_chunk",
"content": "Infosys is...",
"chunk_id": 0
}

// Tool execution
{
"type": "tool_call_start",
"tool_name": "get_stock_info",
"tool_id": "call_123"
}

// Completion
{
"type": "message_complete",
"message_id": "uuid",
"metadata": {
"tokens_used": 1500,
"tools_used": ["get_stock_info"],
"processing_time_ms": 2500
}
}
---

## Background Jobs

### Configured Jobs

1. **Portfolio Price Update**
   - Frequency: Every 30 minutes
   - Updates stock prices via yfinance

2. **Portfolio Reports**
   - Frequency: Configurable (daily/weekly/monthly)
   - Sends email reports to users

3. **Cleanup OTPs**
   - Frequency: Every hour
   - Removes expired OTPs

4. **Cleanup Tokens**
   - Frequency: Every 6 hours
   - Removes revoked tokens

---

## Rate Limiting

### 4-Level Fail-Fast System

| Level | Limit | Window | Action |
|-------|-------|--------|--------|
| Burst | 10 prompts | 1 minute | Block immediately |
| Per-Chat | 50 prompts | Per chat | Block chat |
| Hourly | 150 prompts | 1 hour | Block for hour |
| Daily | 1000 prompts | 24 hours | Block for day |

### Admin Controls
- Update limits globally
- Set per-user overrides
- Whitelist users (no limits)
- View violation logs

---

## Email Notifications

### 15+ Email Types

1. **OTP Emails**
   - Registration OTP
   - Password reset OTP
   - Admin login OTP

2. **Account Emails**
   - Welcome email
   - Password changed
   - Account deactivated

3. **Rate Limit Emails**
   - Burst limit exceeded
   - Hourly limit exceeded
   - Daily limit exceeded

4. **Portfolio Emails**
   - Daily/weekly/monthly reports

5. **System Emails**
   - Maintenance notifications
   - Security alerts

---

## Docker Deployment

### Quick Start

Build and run
docker-compose up -d

View logs
docker-compose logs -f backend

Stop
docker-compose down
### Services

- **backend**: FastAPI application (port 8000)
- **postgres**: PostgreSQL database (port 5432)
- **redis**: Redis cache (port 6379)
- **pgadmin**: Database management (port 5050)

### Production Deployment

Build production image
docker build -t kubera-backend:latest .

Run with environment file
docker run -d
--name kubera-backend
--env-file .env
-p 8000:8000
kubera-backend:latest
---

## Development

### Code Style

Format code
black app/

Sort imports
isort app/

Lint
flake8 app/

Type checking
mypy app/
### Database Migrations

Create migration
python scripts/run_migrations.py create "description"

Apply migrations
python scripts/run_migrations.py migrate

Check status
python scripts/run_migrations.py status


---

## Testing

Run all tests
pytest

Run with coverage
pytest --cov=app --cov-report=html

Run specific test
pytest tests/test_auth.py

Run with logs
pytest -s -v


---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- **Email**: support@kubera.ai
- **Documentation**: https://docs.kubera.ai
- **Issues**: https://github.com/yourusername/kubera-backend/issues

---

## Acknowledgments

- **Anthropic** for Claude 3.5 Sonnet
- **FastAPI** team for the amazing framework
- **LangChain** for MCP adapters
- **yfinance** for stock data

---

## Statistics

- **Total Lines of Code**: 15,000+
- **API Endpoints**: 42 REST + 1 WebSocket
- **Database Tables**: 15
- **MCP Tools**: 44
- **Background Jobs**: 4
- **Email Templates**: 15+

---

**Made with love in India**

**Version**: 1.0.0  
**Last Updated**: December 2025


Total Files:           150+
Lines of Code:         15,000+
API Endpoints:         42 REST + 1 WebSocket
Database Tables:       15
Indexes:               60+
Foreign Keys:          10
Constraints:           25+
Triggers:              9
MCP Servers:           5
MCP Tools:             44
Background Jobs:       4
Email Templates:       15+
Python Packages:      50+
Docker Services:      4


# 1. Setup
cp .env.example .env
# Edit .env with your values

# 2. Install
pip install -r requirements.txt

# 3. Initialize Database
python scripts/init_db.py

# 4. Create Admin
python scripts/seed_admin.py

# 5. Run Application
uvicorn app.main:app --reload

# OR with Docker
docker-compose up -d
