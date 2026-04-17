# Neura Platform v2

AI agent platform with Telegram and Web interfaces. Each agent ("capsule") runs independently with its own personality, memory, skills, and integrations.

## Architecture

```
Client (Browser / Telegram)
    │
    ├── Web: React+Vite SPA → FastAPI backend (port 8080)
    └── Telegram: python-telegram-bot polling
            │
    ┌───────▼───────────────────────────────┐
    │  Neura Platform (Python 3.12)         │
    │  ├── Core: engine, memory, context    │
    │  ├── Transport: telegram, web, auth   │
    │  ├── Storage: PostgreSQL + Redis      │
    │  └── Monitoring: metrics, alerts      │
    └───────┬───────────────────────────────┘
            │
    ┌───────▼───────────────────────────────┐
    │  AI Engine (Claude CLI)               │
    │  Fallbacks: OpenCode, YandexGPT       │
    └───────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Ubuntu 22.04+ / Debian 12+
- Python 3.12+
- Node.js 20+ (for web frontend)
- Docker + Docker Compose
- Claude CLI (`claude`) installed and authenticated

### 1. Clone and configure

```bash
git clone <repo-url> /opt/neura-v2
cd /opt/neura-v2

# Copy and edit environment variables
cp .env.example .env
nano .env  # Fill in all [REQUIRED] values
```

### 2. Start services

```bash
# Start PostgreSQL (pgvector) and Redis
docker compose up -d postgres redis

# Wait for healthy status
docker compose ps
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Build web frontend

```bash
cd web
npm install
npm run build   # Produces web/dist/
cd ..
```

### 5. Initialize database

Migrations run automatically on first start. Or manually:

```bash
python3 -c "
import asyncio
from neura.storage.db import Database
async def migrate():
    db = Database()
    await db.connect()
    await db.run_migrations()
    await db.close()
asyncio.run(migrate())
"
```

### 6. Create a capsule

Create a YAML config in `config/capsules/`:

```yaml
id: my_capsule
name: My AI Assistant
owner:
  name: John Doe
  telegram_id: 123456789
telegram:
  bot_token: ${MY_BOT_TOKEN}
  features:
    streaming: true
    voice_input: true
    file_tools: true
claude:
  model: sonnet
  effort: high
  system_prompt: my_capsule/SYSTEM.md
skills: []
```

Create the home directory:

```bash
mkdir -p homes/my_capsule
```

Add the bot token to `.env`:

```
MY_BOT_TOKEN=your_token_from_botfather
```

### 7. Start the platform

```bash
# Run as systemd service (recommended)
python3 -m neura.transport.app

# Or for development
python3 -m neura.transport.app --debug
```

### 8. Set up systemd (production)

```bash
cat > /etc/systemd/system/neura-v2.service << 'EOF'
[Unit]
Description=Neura Platform v2
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/neura-v2
EnvironmentFile=/opt/neura-v2/.env
ExecStart=/usr/bin/python3 -m neura.transport.app
Restart=always
RestartSec=5
MemoryMax=4G

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable neura-v2
systemctl start neura-v2
```

## Directory Structure

```
/opt/neura-v2/
├── neura/                  # Platform source code
│   ├── core/               # Engine, memory, context, capsule
│   ├── transport/           # Telegram, web, auth, websocket
│   ├── storage/             # Database, cache, migrations
│   ├── monitoring/          # Health checks, metrics, alerts
│   └── provisioning/        # Onboarding flow
├── web/                    # React+Vite frontend
│   ├── src/                # Source (TypeScript + React)
│   └── dist/               # Built SPA (git-ignored, run npm build)
├── config/
│   ├── capsules/           # Per-capsule YAML configs
│   ├── themes/             # UI theme configs
│   └── remote_capsules.yaml # Remote server mapping
├── homes/                  # Per-capsule runtime data (git-ignored)
│   └── <capsule_id>/
│       ├── CLAUDE.md       # System prompt for this capsule
│       ├── memory/         # Long-term memory files
│       ├── data/           # Capsule-specific data
│       └── heartbeat.yaml  # Scheduled tasks config
├── skills/                 # Shared skill pool (git-ignored)
├── data/
│   ├── uploads/            # User-uploaded files (git-ignored)
│   └── vectordb/           # Vector embeddings (git-ignored)
├── tests/                  # Pytest test suite
├── scripts/                # Utility scripts
├── docker-compose.yml      # PostgreSQL + Redis + nginx
├── .env.example            # Environment variable template
└── requirements.txt        # Python dependencies
```

## Multi-Server Setup

For capsules on remote servers, add them to `config/remote_capsules.yaml`:

```yaml
remote_capsule_id:
  host: http://remote-server-ip:8080
  name: "Client Name"
  server: server-label
```

The platform transparently proxies REST and WebSocket requests to remote servers. Each remote server runs its own Neura v2 instance with independent PostgreSQL and Redis.

## Development

```bash
# Run tests
pytest tests/

# Type checking
mypy neura/

# Frontend dev server (with API proxy)
cd web && npm run dev
```

## License

Proprietary. All rights reserved.
