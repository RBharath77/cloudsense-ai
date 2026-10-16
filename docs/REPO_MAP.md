# CloudSense AI — Repository Map

This map reflects the actual repository structure in `/Users/BharathR/Downloads/cloudsense-ai`.

```
cloudsense-ai/
├── .agents/                          # Antigravity agent configuration
│   ├── rules/
│   │   └── cloudsense.md            # Invariant project rules
│   └── skills/
│       ├── cloudsense-start-phase/  # Phase planning skill
│       │   └── SKILL.md
│       └── cloudsense-finish-phase/ # Phase verification skill
│           └── SKILL.md
├── .env.example                     # Environment template with PostgreSQL/Redis/JWT placeholders
├── .gitignore                       # Git ignore (.env, .db, node_modules, .next, etc.)
├── .venv/                           # Local virtual environment (currently Python 3.14 without packages)
├── README.md                        # Project overview and setup instructions
├── docker-compose.yml               # Multi-container orchestration (PostgreSQL, Redis, backend, frontend)
├── backend/                         # FastAPI backend service
│   ├── Dockerfile                   # Python 3.11/Debian container definition
│   ├── alembic/                     # Database migration framework
│   ├── alembic.ini                  # Alembic configuration
│   ├── requirements.txt             # Core backend dependencies (FastAPI, SQLAlchemy, scikit-learn, etc.)
│   ├── requirements-dev.txt         # Dev dependencies
│   ├── tests/                       # Automated test suite
│   │   ├── test_auth.py             # Password hashing tests
│   │   └── test_ml.py               # ML forecasting and anomaly tests
│   └── app/                         # Application package
│       ├── __init__.py
│       ├── config.py                # Pydantic Settings (DB URL, JWT Secret, cloud mode)
│       ├── database/                # Database engine and SessionLocal setup
│       ├── models/                  # SQLAlchemy ORM models (15 tables)
│       ├── auth/                    # JWT issuance, verification, password hashing, role dependencies
│       ├── main.py                  # FastAPI app with route definitions
│       ├── ml.py                    # Trend forecasting and IsolationForest anomaly detection
│       ├── providers.py             # CloudProvider base class & MockCloudProvider (AWS, Azure, GCP)
│       ├── seed.py                  # Demo dataset generator (NovaTech Solutions, 120 resources, 90-day costs)
│       ├── ai/                      # AI assistant module directory (currently placeholder)
│       ├── alerts/                  # Alerting module directory (placeholder)
│       ├── api/                     # Sub-routes directory (placeholder)
│       ├── providers/               # Provider connectors directory (placeholder)
│       ├── reports/                 # Reporting module directory (placeholder)
│       ├── schemas/                 # Pydantic schema directory (placeholder)
│       ├── security/                # Security scanner directory (placeholder)
│       ├── services/                # Business services directory (placeholder)
│       └── utils/                   # Shared utilities directory (placeholder)
├── frontend/                        # Next.js frontend application
│   ├── Dockerfile                   # Node 20 / Next.js container definition
│   ├── package.json                 # Next 15.4, React 19, Tailwind CSS 4, Recharts, Framer Motion
│   ├── tsconfig.json                # TypeScript compiler config
│   ├── postcss.config.mjs           # PostCSS configuration with Tailwind
│   ├── lib/
│   │   └── api.ts                   # Fetch wrapper with Bearer token header injection
│   ├── components/
│   │   ├── Shell.tsx                # SaaS navigation sidebar and top header
│   │   ├── Analytics.tsx            # Dashboard, Cost, Forecast, Assistant components
│   │   └── Page.tsx                 # Page wrapper and generic DataList table
│   └── app/                         # App Router pages
│       ├── page.tsx                 # Root redirect / landing
│       ├── layout.tsx               # Root layout
│       ├── globals.css              # Global styles
│       ├── login/page.tsx           # Authentication page
│       ├── register/page.tsx        # Organization registration page
│       ├── dashboard/page.tsx       # Executive overview dashboard
│       ├── costs/page.tsx           # Cost intelligence page
│       ├── forecast/page.tsx        # Cost forecast page
│       ├── anomalies/page.tsx       # Anomaly center
│       ├── rca/page.tsx             # Root-cause analysis page
│       ├── optimization/page.tsx    # Recommendations & simulation
│       ├── carbon/page.tsx          # CarbonSense dashboard
│       ├── cloud-accounts/page.tsx  # Cloud accounts & simulated sync
│       ├── resources/page.tsx       # Cloud resource inventory
│       ├── budgets/page.tsx         # Budgets overview
│       ├── alerts/page.tsx          # Alerts center
│       ├── security/page.tsx        # Security findings
│       ├── sla/page.tsx             # SLA tracking
│       ├── scaling/page.tsx         # Predictive scaling
│       ├── assistant/page.tsx       # Grounded AI assistant chat
│       ├── reports/page.tsx         # PDF report generation & download
│       └── settings/page.tsx        # Settings
├── docs/                            # Architecture and design documentation
├── prompts/                         # Antigravity master and phase prompts
└── scripts/
    └── seed.sh                      # Shell script to seed the database
```
