# Card Checker Telegram Bot

A high-performance, multi-gateway credit card validation bot for Telegram. Supports concurrent checking across multiple payment gateways with admin controls, site management, and production-grade reliability.

## Features

- **Multi-Gateway Support** — Braintree Auth (B3), PPCP, PayPal Pro, and Stripe
- **Telegram Bot Interface** — Full command-based interaction for users and admins
- **High Concurrency** — Async card checking with configurable thread pools (200+ workers)
- **Admin Panel** — User management, mod system, gateway controls, site freeze, and mass-check settings
- **Site Management** — Per-gateway site rotation, bad-site auto-detection and removal, site freeze/restore
- **Forwarder System** — Forward approved card results to multiple Telegram channels per gateway
- **Rate Limiting** — Per-user, per-gateway, and per-domain token-bucket rate limiters
- **BIN Lookup** — Multi-API BIN info with caching (antipublic, bincheck, handyapi)
- **Backup & Restore** — Full/partial system backups with ZIP export and one-click restore
- **Auto-Restart** — Graceful bot restart with state persistence and post-restart notifications
- **Production Runner** — Dedicated production entry point with health monitoring, memory management, and `uvloop` support
- **Gateway Statistics** — Real-time tracking of active threads, success rates, and response times

## Project Structure

```
├── auth.py                     # Main Telegram bot (entry point)
├── run_production.py           # Production runner with health monitoring
├── system_manager.py           # Backup, restore, and system update logic
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── bot_token.txt               # Telegram bot token (not committed)
│
├── core/                       # Shared core modules
│   ├── __init__.py
│   ├── config.py               # Centralized configuration and constants
│   ├── database.py             # Cached JSON database with file locking
│   ├── concurrency_manager.py  # Per-gateway request queues and load balancing
│   ├── gateway_stats.py        # Gateway usage statistics tracker
│   ├── http_client.py          # Connection-pooled HTTP client (sync + async)
│   ├── rate_limiter.py         # Token-bucket rate limiters (async, sync, per-domain, per-user)
│   └── utils.py                # Shared utilities (card format, BIN lookup, address data)
│
├── ppcp/                       # PPCP (PayPal Credit Card Payment) gateway
│   ├── __init__.py
│   ├── async_ppcpgatewaycvv.py # Async checker with streaming results
│   ├── ppcpgatewaycvv.py       # Sync checker
│   ├── site_manager.py         # Site rotation and bad-site handling
│   ├── rate_limiter.py         # PPCP-specific rate limiter
│   ├── metrics.py              # Health monitoring and metrics
│   └── sites.txt               # PPCP gateway sites list
│
├── paypalpro/                  # PayPal Pro gateway
│   ├── __init__.py
│   ├── paypalpro.py            # PayPal Pro checker with connection pooling
│   └── sites.txt               # PayPal Pro sites list
│
├── stripe/                     # Stripe gateway
│   ├── __init__.py
│   └── allstripecvv.py         # Stripe CVV checker
│
├── site_1/, site_2/, ...       # Braintree Auth site configurations
│   ├── site.txt                # Site URL
│   ├── cookies_1.txt           # Session cookies
│   ├── cookies_2.txt           # Alternate cookies
│   └── proxy.txt               # Proxy configuration
│
└── test_*.py                   # Test scripts
```

## Prerequisites

- **Python 3.10+**
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Linux recommended for `uvloop` support (optional on Windows/macOS)

## Installation

1. **Clone the repository:**

   ```bash
   git clone <repo-url>
   cd <repo-directory>
   ```

2. **Create a virtual environment (recommended):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the bot token:**

   Place your Telegram bot token in `bot_token.txt`:

   ```bash
   echo "YOUR_BOT_TOKEN" > bot_token.txt
   ```

   Or set the `TELEGRAM_BOT_TOKEN` environment variable.

5. **Configure environment variables (optional):**

   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

## Configuration

Configuration is loaded from environment variables (or `.env` file via `python-dotenv`). Key settings:

| Variable | Default | Description |
|---|---|---|
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `MAX_CONCURRENT_REQUESTS` | `100` | Maximum concurrent requests |
| `MAX_RETRIES` | `3` | Maximum retry attempts per request |
| `RATE_LIMIT_PER_SECOND` | `10` | Global rate limit |
| `BIN_CHECK_TIMEOUT` | `10` | BIN lookup API timeout |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FILE` | `ppcp_checker.log` | Log file path |

See `.env.example` for the full list.

## Usage

### Run the Telegram Bot

```bash
python auth.py
```

### Run in Production Mode

The production runner adds health monitoring, memory management, graceful shutdown, and optional `uvloop`:

```bash
python run_production.py
```

## Telegram Commands

### User Commands

| Command | Description |
|---|---|
| `/start` | Start the bot and show welcome message |
| `/b3 <card>` | Check card via Braintree Auth gateway |
| `/pp <card>` | Check card via PPCP gateway |
| `/pro <card>` | Check card via PayPal Pro gateway |
| `/st <card>` | Check card via Stripe gateway |
| `/b3s` | Mass check — send multiple cards for Braintree |
| `/pps` | Mass check — send multiple cards for PPCP |
| `/pros` | Mass check — send multiple cards for PayPal Pro |
| `/sts` | Mass check — send multiple cards for Stripe |

**Card format:** `number|mm|yyyy|cvv` or `number|mm|yy|cvv` or `number mmyy cvv`

### Admin Commands

| Command | Description |
|---|---|
| `/admin` | Open admin control panel |
| `/adduser <id>` | Approve a user |
| `/removeuser <id>` | Remove a user |
| `/addmod <id>` | Add a moderator |
| `/removemod <id>` | Remove a moderator |
| `/stats` | View gateway statistics |
| `/backup` | Create system backup |
| `/restore` | Restore from backup |
| `/update` | Update system from GitHub |
| `/restart` | Restart the bot |

## Modules

### `core/`

Shared infrastructure used by all gateways:

- **`config.py`** — Centralized configuration with environment variable support and gateway-specific settings.
- **`database.py`** — Thread-safe JSON database with in-memory caching (TTL-based), file locking, and atomic updates.
- **`concurrency_manager.py`** — Per-gateway priority queues with configurable concurrency, load balancing, and real-time statistics.
- **`gateway_stats.py`** — Tracks active threads, request counts, success/failure rates, and response times per gateway.
- **`http_client.py`** — Singleton HTTP client manager with connection pooling for both `requests` (sync) and `aiohttp` (async).
- **`rate_limiter.py`** — Token-bucket rate limiters: async, sync, per-domain, and per-user variants.
- **`utils.py`** — Card format normalization, BIN info lookup with caching, random address/name/email generation, country detection.

### `ppcp/`

PayPal Credit Card Payment gateway checker with async support:

- **`async_ppcpgatewaycvv.py`** — Production-grade async checker with streaming results, bad-site auto-removal, multiple BIN APIs, and connection pooling.
- **`ppcpgatewaycvv.py`** — Synchronous checker for single-card operations.
- **`site_manager.py`** — Thread-safe site loading, bad-site pattern matching, auto-removal (configurable), and site restoration.
- **`rate_limiter.py`** — PPCP-specific rate limiter instances.
- **`metrics.py`** — Request metrics collection (totals, success rates, response times, per-domain stats).

### `paypalpro/`

PayPal Pro (NVP API) gateway checker with connection pooling, retry logic, and BIN caching.

### `stripe/`

Stripe charge-based gateway checker.

## Testing

Run individual test scripts:

```bash
# Validate file structure and syntax
python validate_implementation.py

# Test concurrency and thread safety
python test_concurrency.py

# Test restart functionality
python test_restart_standalone.py

# Test PPCP checker
python test_ppcp_checker.py

# Test forwarder database
python test_forwarders_basic.py
```

## License

Private — All rights reserved.
