# 🚀 KUBERA - AI-Powered Stock Analysis Chatbot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-316192.svg)](https://www.postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**KUBERA** is an intelligent stock analysis chatbot specialized in Indian markets (NSE/BSE). Built with FastAPI, PostgreSQL, and OpenRouter (supporting multiple LLMs including Llama 3.3, Claude, GPT-4), it provides comprehensive stock analysis through AI-powered conversations.

---

## 📋 Table of Contents

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
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Core Features
- 🤖 **AI-Powered Chat**: Real-time conversations powered by OpenRouter (Llama 3.3, Claude, GPT-4, etc.)
- 📊 **Stock Analysis**: Comprehensive analysis of NSE/BSE stocks
- 💼 **Portfolio Tracking**: Track your investments with live price updates
- 📈 **Technical Analysis**: 45 MCP tools for in-depth analysis
- 🎨 **Visualizations**: Beautiful charts and graphs via Plotly
- 📰 **News & Sentiment**: Real-time market news and sentiment analysis

### Authentication & Security
- 🔐 **3-Step OTP Registration**: Email-based verification
- 🎫 **JWT Authentication**: Secure access and refresh tokens
- 🔒 **Password Security**: Bcrypt hashing with strict requirements
- 🔄 **Session Management**: Automatic token refresh

### Rate Limiting
- ⚡ **4-Level Fail-Fast System**:
  - Burst: 10 prompts/minute
  - Per-Chat: 50 prompts/chat
  - Hourly: 150 prompts/hour
  - Daily: 1000 prompts/24 hours

### Email Notifications
- 📧 **15+ Email Triggers**:
  - Registration OTP
  - Password reset
  - Welcome email
  - Rate limit notifications
  - Portfolio reports
  - Security alerts

### Admin Panel
- 🎛️ **Complete System Management**:
  - User management
  - Rate limit configuration
  - System control (start/stop)
  - Analytics dashboard
  - Activity logs

### Background Jobs
- ⏰ **Automated Tasks**:
  - Portfolio price updates (every 30 mins)
  - Daily/weekly/monthly reports
  - Cleanup jobs (OTPs, tokens)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT (Browser/App)                        │
└────────────────┬────────────────────────────┬───────────────────┘
                 │                            │
                 │ REST API                   │ WebSocket
                 │                            │
┌────────────────▼────────────────────────────▼───────────────────┐
│                    FASTAPI APPLICATION                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    API Endpoints (50)                      │ │
│  │  Auth (11) | User (7) | Portfolio (5) | Chat (5)           │ │
│  │        Admin (19) | Root (4) | WebSocket (1)               │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Business Logic Layer                      │ │
│  │         Services | Validators | Formatters                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    MCP Integration                         │ │
│  │      LLM Orchestrator | Tool Handler | Client              │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────┬──────────────────┬──────────────────┬──────────────┘
             │                  │                  │
┌────────────▼────────┐ ┌───────▼──────┐ ┌─────────▼───────────────┐
│    PostgreSQL       │ │ MCP Servers  │ │  Background Scheduler   │
│    (15 tables)      │ │ (5 servers)  │ │     (APScheduler)       │
│                     │ │ (45 tools)   │ │                         │
└─────────────────────┘ └──────────────┘ └─────────────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.109.0 | Web Framework |
| Python | 3.11+ | Language |
| Uvicorn | Latest | ASGI Server |
| PostgreSQL | 14+ | Database |
| AsyncPG | Latest | Async PostgreSQL Driver |

### AI & LLM
| Technology | Purpose |
|------------|---------|
| OpenRouter | LLM Gateway (multi-model) |
| Llama 3.3-70B | Default LLM Model |
| LangChain | LLM Orchestration |
| FastMCP | MCP Protocol |

### Data & Finance
| Technology | Purpose |
|------------|---------|
| yfinance | Stock Data |
| Pandas | Data Processing |
| NumPy | Numerical Computing |
| Plotly | Interactive Charts |
| Matplotlib | Static Charts |

### Authentication
| Technology | Purpose |
|------------|---------|
| python-jose | JWT Tokens |
| passlib (bcrypt) | Password Hashing |
| Pydantic | Validation |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| APScheduler | Background Jobs |
| aiosmtplib | Async Email |
| Docker | Containerization |
| Supabase | Chart Storage |

---

## 📁 Project Structure

```
kubera-backend/
├── main.py                           # FastAPI app entry point
├── app/
│   ├── __init__.py
│   ├── core/                         # Core configurations
│   │   ├── config.py                 # Settings & environment
│   │   ├── security.py               # Auth utilities
│   │   ├── database.py               # Database connection
│   │   ├── dependencies.py           # FastAPI dependencies
│   │   └── utils.py                  # Helper utilities
│   ├── models/                       # Pydantic models
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── portfolio.py
│   │   ├── admin.py
│   │   ├── rate_limit.py
│   │   ├── email.py
│   │   └── system.py
│   ├── schemas/                      # Request/Response schemas
│   │   ├── requests/
│   │   │   ├── auth_requests.py
│   │   │   ├── user_requests.py
│   │   │   ├── portfolio_requests.py
│   │   │   ├── chat_requests.py
│   │   │   └── admin_requests.py
│   │   └── responses/
│   │       ├── auth_responses.py
│   │       ├── user_responses.py
│   │       ├── portfolio_responses.py
│   │       ├── chat_responses.py
│   │       └── admin_responses.py
│   ├── api/                          # API routes
│   │   └── routes/
│   │       ├── auth_routes.py        # Authentication (8 endpoints)
│   │       ├── user_routes.py        # User management (6 endpoints)
│   │       ├── portfolio_routes.py   # Portfolio (5 endpoints)
│   │       ├── chat_routes.py        # Chat (5 endpoints)
│   │       ├── admin_routes.py       # Admin (17 endpoints)
│   │       └── websocket_routes.py   # WebSocket (1 endpoint)
│   ├── services/                     # Business logic
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── portfolio_service.py
│   │   ├── chat_service.py
│   │   ├── rate_limit_service.py
│   │   ├── email_service.py
│   │   └── admin_service.py
│   ├── mcp/                          # MCP Integration
│   │   ├── client.py                 # MCP client manager
│   │   ├── config.py                 # MCP configuration
│   │   ├── tool_handler.py           # Tool execution
│   │   └── llm_integration.py        # Claude integration
│   ├── websocket/                    # WebSocket handling
│   │   ├── connection_manager.py     # Connection pool
│   │   ├── message_handler.py        # Message processing
│   │   ├── response_streamer.py      # Streaming responses
│   │   └── protocols.py              # WebSocket protocols
│   ├── background/                   # Background jobs
│   │   ├── scheduler.py              # APScheduler config
│   │   ├── jobs/                     # Job definitions
│   │   └── tasks/                    # Task implementations
│   ├── db/                           # Database
│   │   ├── migrations/               # SQL migrations
│   │   │   ├── v1_initial_schema.sql
│   │   │   ├── v2_indexes.sql
│   │   │   ├── v2_add_chart_url.sql
│   │   │   └── v3_constraints.sql
│   │   └── repositories/             # Data access layer
│   │       ├── user_repository.py
│   │       ├── chat_repository.py
│   │       ├── portfolio_repository.py
│   │       ├── otp_repository.py
│   │       ├── token_repository.py
│   │       ├── rate_limit_repository.py
│   │       ├── email_repository.py
│   │       ├── admin_repository.py
│   │       └── system_repository.py
│   ├── utils/                        # Utilities
│   │   ├── validators.py
│   │   ├── formatters.py
│   │   ├── otp_generator.py
│   │   ├── email_templates.py
│   │   ├── helpers.py
│   │   └── logger.py
│   └── exceptions/                   # Exception handling
│       ├── custom_exceptions.py
│       └── handlers.py
├── mcp_servers/                      # 5 MCP Servers
│   ├── fin_data.py                   # Financial Data Server (7 tools)
│   ├── market_tech.py                # Market & Technical Server (9 tools)
│   ├── gov_compliance.py             # Governance & Compliance (8 tools)
│   ├── news_sent.py                  # News & Sentiment Server (10 tools)
│   └── visualization.py              # Visualization Server (11 tools)
├── scripts/                          # Setup scripts
│   ├── init_db.py                    # Database initialization
│   ├── seed_admin.py                 # Admin user creation
│   ├── seed_rate_limits.py           # Rate limit setup
│   └── run_migrations.py             # Migration runner
├── .env                              # Environment variables
├── .env.example                      # Environment template
├── requirements.txt                  # Python dependencies
├── pyproject.toml                    # Project configuration
├── Dockerfile                        # Docker image
├── docker-compose.yml                # Docker Compose
└── README.md                         # This file
```

---

## 📥 Installation

### Prerequisites
- Python 3.11 or higher
- PostgreSQL 14 or higher
- pip or uv (package manager)
- (Optional) Docker & Docker Compose

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/kubera-backend.git
cd kubera-backend
```

### 2. Create Virtual Environment

```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# OR using uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Using pip
pip install --upgrade pip
pip install -r requirements.txt

# OR using uv
uv pip install -r requirements.txt
```

---

## ⚙️ Configuration

### 1. Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and configure the following:

```env
# ===========================================
# CRITICAL SETTINGS
# ===========================================
SECRET_KEY=your_secret_key_here

# ===========================================
# LLM (OPENROUTER)
# ===========================================
OPENROUTER_API_KEY=sk-or-your-api-key
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct  # or anthropic/claude-3.5-sonnet

# ===========================================
# DATABASE (SUPABASE)
# ===========================================
POSTGRES_HOST=your-project.pooler.supabase.com
POSTGRES_PORT=6543
POSTGRES_USER=postgres.your-project
POSTGRES_PASSWORD=your_password
POSTGRES_DB=postgres

# ===========================================
# SMTP (for emails)
# ===========================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com

# ===========================================
# SUPABASE (for chart storage)
# ===========================================
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# ===========================================
# OPTIONAL: EXTERNAL APIS
# ===========================================
FINNHUB_API_KEY=your-finnhub-key
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
NEWS_API_KEY=your-news-api-key
```

### 2. Generate Secret Key

```bash
# Using OpenSSL
openssl rand -hex 32

# OR using Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🗄️ Database Setup

### Method 1: Automated Script (Recommended)

```bash
# Initialize database, run migrations, seed data
python scripts/init_db.py
```

### Method 2: Manual Setup

```bash
# Step 1: Create database
createdb kubera_db

# Step 2: Run migrations
python scripts/run_migrations.py migrate

# Step 3: Create admin user
python scripts/seed_admin.py

# Step 4: Configure rate limits
python scripts/seed_rate_limits.py
```

### Verify Setup

```bash
# Check migration status
python scripts/run_migrations.py status

# List admin users
python scripts/seed_admin.py list
```

---

## 🚀 Running the Application

### Development Mode

```bash
# With auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# OR simply
python main.py
```

### Production Mode

```bash
# Multi-worker
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Access Points

| Endpoint | URL |
|----------|-----|
| 🌐 API Root | http://localhost:8000 |
| 📖 Swagger Docs | http://localhost:8000/docs |
| 📚 ReDoc | http://localhost:8000/redoc |
| ❤️ Health Check | http://localhost:8000/health |
| 🔌 WebSocket | ws://localhost:8000/ws/chat |

---

## 📡 API Documentation

### Authentication Endpoints (11)

```http
POST /auth/register/step1              # Step 1: Send OTP to email
POST /auth/register/step2              # Step 2: Verify OTP
POST /auth/register/step3              # Step 3: Complete registration
POST /auth/login                       # Login with username and password
POST /auth/refresh                     # Refresh access token
POST /auth/logout                      # Logout user
GET  /auth/check-username/{username}   # Check username availability
POST /auth/password-reset/send-otp     # Send OTP for password reset
POST /auth/password-reset/confirm      # Confirm password reset with OTP
POST /auth/forgot-password/send-otp    # Send forgot password OTP
POST /auth/forgot-password/confirm     # Reset password with OTP
```

### User Endpoints (7)

```http
GET    /user/profile               # Get user profile
PUT    /user/profile               # Update user profile
PUT    /user/username              # Update username
PUT    /user/password              # Update password
GET    /user/email-preferences     # Get email preferences
PUT    /user/email-preferences     # Update email preferences
GET    /user/stats                 # Get user statistics
```

### Portfolio Endpoints (5)

```http
GET    /portfolio/                 # Get user portfolio
POST   /portfolio/                 # Add portfolio entry
PUT    /portfolio/{portfolio_id}   # Update portfolio entry
DELETE /portfolio/{portfolio_id}   # Delete portfolio entry
POST   /portfolio/update-prices    # Update portfolio prices
```

### Chat Endpoints (5)

```http
GET    /chats/                     # Get all chats
POST   /chats/                     # Create new chat
GET    /chats/{chat_id}            # Get chat with messages
DELETE /chats/{chat_id}            # Delete chat
PUT    /chats/{chat_id}/rename     # Rename chat
```

### Admin Endpoints (19)

```http
POST   /admin/login/send-otp                   # Admin login - Send OTP
POST   /admin/login/verify-otp                 # Admin login - Verify OTP
GET    /admin/dashboard                        # Get dashboard statistics
GET    /admin/dashboard/prompt-activity        # Get prompt activity time-series
GET    /admin/users                            # Get all users
GET    /admin/users/{user_id}                  # Get user details
PUT    /admin/users/{user_id}/deactivate       # Deactivate user
PUT    /admin/users/{user_id}/reactivate       # Reactivate user
GET    /admin/rate-limits/config               # Get rate limit configuration
PUT    /admin/rate-limits/global               # Update global rate limits
PUT    /admin/rate-limits/user/{user_id}       # Set user-specific rate limits
POST   /admin/rate-limits/whitelist            # Add user to whitelist
DELETE /admin/rate-limits/whitelist/{user_id}  # Remove user from whitelist
POST   /admin/rate-limits/reset/{user_id}      # Reset user rate limit counters
GET    /admin/rate-limits/violations           # Get rate limit violations
GET    /admin/portfolio-reports/settings       # Get portfolio report settings
PUT    /admin/portfolio-reports/settings       # Update portfolio report settings
POST   /admin/system/control                   # System control (start/stop)
GET    /admin/activity-logs                    # Get admin activity logs
```

### Root Endpoints (4)

```http
GET    /                           # API Root
GET    /health                     # Health Check
GET    /mcp/tools                  # List MCP Tools
GET    /scheduler/status           # Scheduler Status
```

### WebSocket (1)

```http
WS /ws/chat?token={jwt_token}      # Real-time chat
```

---

## 🔧 MCP Servers

KUBERA uses 5 specialized MCP servers with **45 tools** total:

### Server 1: Financial Data (`fin_data.py`) - 7 Tools

| Tool | Description |
|------|-------------|
| `fetch_company_fundamentals` | Core fundamental metrics |
| `fetch_historical_financials` | Historical financial data |
| `fetch_balance_sheet_data` | Balance sheet components |
| `fetch_cash_flow_data` | Cash flow statement |
| `fetch_dividend_history` | Dividend data & sustainability |
| `fetch_eps_analysis` | EPS trends & analysis |
| `validate_stock_symbol` | Symbol validation |

### Server 2: Market & Technical (`market_tech.py`) - 9 Tools

| Tool | Description |
|------|-------------|
| `fetch_current_price_data` | Real-time price data |
| `fetch_historical_price_data` | OHLCV historical data |
| `fetch_technical_indicators` | SMA, RSI, MACD, BBands |
| `fetch_volume_analysis` | Volume trends |
| `fetch_volatility_metrics` | Beta, drawdown, Sharpe |
| `fetch_comparative_performance` | Performance comparison |
| `fetch_institutional_holding_data` | FII/DII holdings |
| `fetch_liquidity_metrics` | Trading liquidity |
| `validate_technical_data` | Data quality check |

### Server 3: Governance & Compliance (`gov_compliance.py`) - 8 Tools

| Tool | Description |
|------|-------------|
| `fetch_promoter_holding_data` | Promoter & pledging info |
| `fetch_board_composition` | Board structure |
| `fetch_audit_quality` | Auditor information |
| `fetch_regulatory_compliance` | Regulatory status |
| `fetch_shareholding_pattern` | Complete shareholding |
| `fetch_related_party_transactions` | Related party deals |
| `fetch_governance_score` | Governance quality score |
| `fetch_insider_transactions` | Insider trading patterns |

### Server 4: News & Sentiment (`news_sent.py`) - 10 Tools

| Tool | Description |
|------|-------------|
| `fetch_news_articles` | Recent news articles |
| `fetch_overall_news_sentiment` | Aggregate sentiment |
| `fetch_analyst_ratings` | Analyst recommendations |
| `fetch_social_sentiment` | Social media sentiment |
| `fetch_company_announcements` | Official announcements |
| `fetch_sector_sentiment` | Sector-wide sentiment |
| `fetch_competitor_sentiment` | Competitor comparison |
| `fetch_news_impact_analysis` | Price impact analysis |
| `fetch_management_commentary` | Management guidance |
| `calculate_sentiment_score` | Text sentiment scoring |

### Server 5: Visualization (`visualization.py`) - 11 Tools

| Tool | Description |
|------|-------------|
| `generate_price_volume_chart` | Price & volume chart |
| `generate_candlestick_chart` | Candlestick chart |
| `generate_technical_indicators_chart` | Technical chart |
| `generate_fundamental_comparison_chart` | Comparison chart |
| `generate_financial_trend_chart` | Trend chart |
| `generate_performance_vs_benchmark_chart` | Benchmark comparison |
| `generate_valuation_heatmap` | Valuation heatmap |
| `generate_portfolio_composition_chart` | Portfolio pie/treemap |
| `generate_dividend_timeline_chart` | Dividend timeline |
| `generate_risk_return_scatter` | Risk-return scatter |
| `validate_chart_data` | Chart data validation |

---

## 🔌 WebSocket Protocol

### Connect

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat?token=YOUR_JWT_TOKEN');
```

### Client → Server Messages

```javascript
// Send message
{
    "type": "message",
    "chat_id": "uuid",
    "message": "Analyze INFY stock"
}

// Ping (keep-alive)
{
    "type": "ping"
}
```

### Server → Client Messages

```javascript
// Text chunk (streaming)
{
    "type": "text_chunk",
    "content": "Infosys is...",
    "chunk_id": 0
}

// Tool execution start
{
    "type": "tool_call_start",
    "tool_name": "fetch_company_fundamentals",
    "tool_id": "call_123"
}

// Tool execution complete
{
    "type": "tool_call_complete",
    "tool_id": "call_123",
    "result": { ... }
}

// Message complete
{
    "type": "message_complete",
    "message_id": "uuid",
    "metadata": {
        "tokens_used": 1500,
        "tools_used": ["fetch_company_fundamentals", "fetch_current_price_data"],
        "processing_time_ms": 2500,
        "chart_url": "https://...",    // Supabase storage URL (if chart generated)
        "chart_html": "<html>..."      // Direct HTML for rendering (if chart generated)
    }
}

// Error
{
    "type": "error",
    "message": "Rate limit exceeded",
    "code": "RATE_LIMITED"
}
```

---

## ⏰ Background Jobs

### Configured Jobs

| Job | Frequency | Description |
|-----|-----------|-------------|
| Portfolio Price Update | Every 30 minutes | Updates stock prices via yfinance |
| Portfolio Reports | Configurable | Sends email reports (daily/weekly/monthly) |
| Cleanup OTPs | Every hour | Removes expired OTPs |
| Cleanup Tokens | Every 6 hours | Removes revoked/expired tokens |

### Check Scheduler Status

```bash
curl http://localhost:8000/scheduler/status
```

---

## ⚡ Rate Limiting

### 4-Level Fail-Fast System

| Level | Limit | Window | Action |
|-------|-------|--------|--------|
| 🚀 Burst | 10 prompts | 1 minute | Block immediately |
| 💬 Per-Chat | 50 prompts | Per chat | Block chat |
| ⏰ Hourly | 150 prompts | 1 hour | Block for hour |
| 📅 Daily | 1000 prompts | 24 hours | Block for day |

### Admin Controls

- ✅ Update limits globally
- ✅ Set per-user overrides
- ✅ Whitelist users (no limits)
- ✅ View violation logs

---

## 📧 Email Notifications

### 15+ Email Types

| Category | Templates |
|----------|-----------|
| 🔑 OTP Emails | Registration, Password Reset, Admin Login |
| 👤 Account Emails | Welcome, Password Changed, Account Deactivated |
| ⚡ Rate Limit Emails | Burst/Hourly/Daily Limit Exceeded |
| 📊 Portfolio Emails | Daily/Weekly/Monthly Reports |
| 🔔 System Emails | Maintenance, Security Alerts |

---

## 🐳 Docker Deployment

### Quick Start

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| backend | 8000 | FastAPI application |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache (optional) |
| pgadmin | 5050 | Database management |

### Production Deployment

```bash
# Build production image
docker build -t kubera-backend:latest .

# Run with environment file
docker run -d \
  --name kubera-backend \
  --env-file .env \
  -p 8000:8000 \
  kubera-backend:latest
```

---

## 💻 Development

### Code Style

```bash
# Format code
black app/ mcp_servers/ scripts/

# Sort imports
isort app/ mcp_servers/ scripts/

# Lint
flake8 app/ mcp_servers/ scripts/

# Type checking
mypy app/
```

### Database Migrations

```bash
# Create migration
python scripts/run_migrations.py create "description"

# Apply migrations
python scripts/run_migrations.py migrate

# Check status
python scripts/run_migrations.py status
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with logs
pytest -s -v

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

---

## 🔍 Troubleshooting

### Common Issues

#### MCP Client Not Initializing

```bash
# Check if all required API keys are set
echo $OPENROUTER_API_KEY

# Verify MCP server files exist
ls mcp_servers/
```

#### Database Connection Failed

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify database exists
psql -l | grep kubera_db
```

#### WebSocket Connection Issues

```bash
# Check if server is running
curl http://localhost:8000/health

# Verify JWT token is valid
```

#### Email Not Sending

```bash
# Verify SMTP settings
# For Gmail, ensure "Less secure app access" or use App Passwords
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Commit Convention

```
feat: Add new feature
fix: Bug fix
docs: Documentation update
style: Code style changes
refactor: Code refactoring
test: Add/update tests
chore: Maintenance tasks
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

- 📧 **Email**: support@kubera.ai
- 📖 **Documentation**: https://docs.kubera.ai
- 🐛 **Issues**: https://github.com/yourusername/kubera-backend/issues

---

## 🙏 Acknowledgments

- **OpenRouter** for multi-model LLM access
- **FastAPI** team for the amazing framework
- **FastMCP** for MCP protocol implementation
- **yfinance** for stock data

---

## 📊 Project Statistics

| Metric | Count |
|--------|-------|
| 📁 Total Files | 150+ |
| 📝 Lines of Code | 15,000+ |
| 🌐 REST Endpoints | 50 |
| 🔌 WebSocket Endpoints | 1 |
| 🗄️ Database Tables | 15 |
| 📇 Database Indexes | 60+ |
| 🔗 Foreign Keys | 10 |
| ✅ Constraints | 25+ |
| ⚡ Triggers | 9 |
| 🤖 MCP Servers | 5 |
| 🔧 MCP Tools | 45 |
| ⏰ Background Jobs | 4 |
| 📧 Email Templates | 15+ |
| 📦 Python Packages | 50+ |
| 🐳 Docker Services | 4 |

---

## 🚀 Quick Start

```bash
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
python main.py

# OR with Docker
docker-compose up -d
```

---

<div align="center">


**Version**: 1.0.0 | **Last Updated**: December 2025

</div>
