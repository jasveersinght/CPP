# MATH AUCTION — Live Mathematical Quiz & Real-Time Auction Platform

A production-grade, server-authoritative web application designed for collegiate mathematics competitions and hackathons. Teams compete in real time to bid on mathematical questions using virtual currency, solve questions on paper, submit verified answers, and earn reward bounties to climb the live leaderboard.

---

## 1. Project Overview

- **Audience**: College mathematics events with 50–100 simultaneous teams (1–4 students per team).
- **Starting Purse**: Each team begins with a virtual purse of **₹10,000.00**.
- **Rules & Auction Lifecycle**:
  - Host presents mathematical problems one by one via live real-time auction.
  - **Question Reading Time (10 Seconds)**: When a question is launched, all teams enter a 10-second reading phase to review the question text and diagrams. Bidding is locked during this reading phase.
  - **Bid Time (30 Seconds)**: After the 10-second reading time elapses, bidding opens with a 30-second countdown timer.
  - Starting bid is the opening price (e.g. ₹500).
  - First valid bid is the starting price; subsequent bids increment by ₹10.
  - Every valid bid resets the countdown to **30 seconds**.
  - When 30 seconds elapse without a new bid, the auction hammer drops.
  - The winning team's purse is atomically debited by the winning bid, and the question becomes active in their repository.
  - The team solves the question on paper and submits the answer through their dashboard.
  - If correct, the reward bounty (e.g. ₹2,000) is credited to their wallet immediately and celebrated with sound effects.
  - **Instant Balance Refresh**: Purse balances update immediately on answer submission and auction wins without requiring page refreshes or re-login.
  - Each team can complete at most 5 questions during the tournament.
  - Real-time ranking: Current Balance (DESC) $\to$ Correct Solutions (DESC) $\to$ Questions Won (DESC).

---

## 2. Key Features

- **Server-Authoritative Auction Engine**:
  - Dual-phase timing: 10-second Reading Phase + 30-second Bidding Phase.
  - Browser timers are purely visual. Expiry and bid ordering are strictly determined by the server and MySQL InnoDB row locks (`SELECT ... FOR UPDATE`).
  - Strict serializability prevents race conditions, duplicate winners, self-outbidding, or corrupted balances under concurrent loads of 100+ teams.
- **Multi-Layer Watchdog & Reconciliation**:
  - Background daemon worker scans every 500ms for expired LIVE auctions.
  - On-demand / lazy reconciliation runs on dashboard loads, bid attempts, and server startup.
  - Immune to browser refreshes, disconnects, or sudden server restarts.
- **ACID Double-Entry Financial Ledger**:
  - Wallets are backed by a strict `transactions` table with audit trail.
  - Balances cannot drop below zero (`CHECK (current_balance >= 0)` constraint).
  - Payment is deducted exactly once upon auction conclusion.
- **Normalized Server-Side Answer Evaluator**:
  - Correct answers are **never** exposed to the frontend.
  - Numerical: handles integers, decimals, scientific tolerances ($10^{-5}$), fractions (`5/12`), and percentages (`12%`).
  - MCQ: option letters (`A`, `B`, `C`, `D`).
  - Multiple Answer: order-independent mathematical set comparisons.
  - Text: whitespace and punctuation normalized.
- **Auditorium Projector View (`/host/live-auction`)**:
  - Designed for big-screen presentation on stage.
  - Extra-large typography, high-contrast indicators, dynamic circular timer showing Reading Time (10s) and Bidding Time (30s), and winner celebration overlay.
- **Synthesized Web Audio Sound Effects**:
  - In-browser Web Audio API synthesis: brassy cash-register "cha-ching" on reward, trumpet chime when bidding opens, hammer gavel sound on auction close, warning ticks on $\le 3$s, and pop on bids. Zero external audio file network dependencies.
- **Browser Anti-Cheating Surveillance**:
  - Fullscreen enforcement with 3-strike penalty:
    - Strike 1: Warning modal.
    - Strike 2: Final warning modal.
    - Strike 3: Automatic tournament disqualification (`is_disqualified = TRUE`).
  - Detects fullscreen exits, tab switches, and window blurs.
  - Host monitor logs every infraction in real time.

---

## 3. Technology Stack

- **Backend**: Python 3.10+, Flask 3.1, Flask-SocketIO (WebSocket + HTTP long-polling fallback).
- **Database**: MySQL 8.0 (InnoDB Engine with ACID transactions, Row-level Locking, Foreign Keys).
- **Driver**: PyMySQL with thread-safe connection pooling and automatic rollback context managers.
- **Frontend**: Vanilla JavaScript (ES6+), Socket.IO Client v4.7.5, Custom Responsive Tournament CSS.
- **Security**: Werkzeug PBKDF2 password hashing, isolated session contexts, strict role-based decorators.

---

## 4. Architecture & Database Schema

```
math-auction/
├── app.py                      # Application entry point, factory & startup watchdog
├── config.py                   # Environment configuration & rules
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .env                        # Local environment credentials (gitignored)
├── database/
│   ├── schema.sql              # MySQL DDL (InnoDB, Foreign Keys, Constraints)
│   ├── db.py                   # Database connection manager & transaction blocks
│   ├── init_db.py              # DDL runner & tournament seed data
│   └── seed_data.py            # 90 competition questions & test teams
├── routes/
│   ├── auth.py                 # Team & Host login, logout, role decorators
│   ├── team.py                 # Team dashboard, bidding, solving, violations
│   └── host.py                 # Host control panel, projector view, admin actions
├── services/
│   ├── auction_service.py      # Server-authoritative auction engine & row locking
│   ├── wallet_service.py       # ACID purse deduction & bounty disbursement
│   ├── answer_service.py       # Server-side answer evaluation & normalization
│   ├── leaderboard_service.py  # Live tournament standings calculation
│   ├── reconciliation_service.py # Watchdog background worker & lazy reconciliation
│   └── anticheat_service.py    # 3-strike integrity violation tracker
├── sockets/
│   └── auction_events.py       # Real-time WebSocket event dispatcher
├── templates/
│   ├── base.html               # Master layout with audio toggle & cheat modals
│   ├── login_team.html         # Team authentication page
│   ├── login_host.html         # Host administration login
│   ├── team_dashboard.html     # Team arena, live auction card & problem solver
│   ├── host_dashboard.html     # Host control room, question bank & live feeds
│   ├── live_auction.html       # Cinema projector screen view
│   └── error.html              # Custom 404 / 500 error display
├── static/
│   ├── css/style.css           # Modern dark tournament styling
│   └── js/
│       ├── socket.io.min.js    # Local offline-ready Socket.IO client
│       ├── sound.js            # Web Audio API sound synthesizer
│       ├── team_dashboard.js   # Team real-time client controller
│       ├── host_dashboard.js   # Host real-time client controller
│       └── live_auction.js     # Projector display controller
└── tests/
    ├── test_reading_time_and_balance_refresh.py # 10s reading time, 30s bid time & balance refresh
    ├── test_auth.py            # Authentication, sessions & authorization tests
    ├── test_wallet.py          # Ledger, balance deductions & negative balance prevention
    ├── test_answer.py          # Normalization, answer checking & reward credit
    ├── test_auction_lifecycle.py # Lifecycle & serializability tests
    ├── test_restart_recovery.py # Crash/restart reconciliation test
    ├── test_concurrency.py     # 100 simultaneous simulated team bids
    └── test_live_e2e.py        # End-to-end integration test against live server
```

---

## 5. Installation & Setup

### Prerequisites
- Python 3.10+
- MySQL Server 8.0+

### Step 1: Clone or Navigate to Project
```powershell
cd c:\Users\jasve\CRYPTEX
```

### Step 2: Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure your `.env` contains your MySQL credentials:
```ini
FLASK_SECRET_KEY=math-auction-production-secret-key-change-me
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=math_auction
FLASK_ENV=development
QUESTION_READING_DURATION_SECONDS=10
AUCTION_DURATION_SECONDS=30
BID_INCREMENT=10
STARTING_WALLET_BALANCE=10000.0
MAX_QUESTIONS_PER_TEAM=5
```

### Step 4: Initialize & Seed Database
Run the schema creation and data seeding script:
```powershell
python database\init_db.py
```
This sets up all tables, the default host, 80 competition teams with ₹10,000 purses, and 90 mathematical questions.

---

## 6. Running the Application

Start the Flask-SocketIO server:
```powershell
python app.py
```
Output will confirm:
```
[INFO] math_auction: Running startup reconciliation for expired auctions...
[INFO] services.reconciliation_service: Auction Watchdog background worker started with 0.5s interval.
[INFO] math_auction: Starting MATH AUCTION Server on http://127.0.0.1:5000
```

Access the application in your browser:
- **Team Portal**: `http://127.0.0.1:5000/team/login`
- **Host Control Room**: `http://127.0.0.1:5000/host/login`
- **Auditorium Projector Display**: `http://127.0.0.1:5000/host/live-auction`

---

## 7. Default Credentials

### Host Administrator
- **Username**: `admin`
- **Password**: `host123`

### Default Student Teams
Teams `TEAM001` through `TEAM080` are pre-seeded:
| Team Code | Team Name | Initial Balance | Password |
| :--- | :--- | :--- | :--- |
| `TEAM001` | Team 01 | ₹10,000.00 | `TEST@123` |
| `TEAM002` | Team 02 | ₹10,000.00 | `TEST@123` |
| `TEAM003` | Team 03 | ₹10,000.00 | `TEST@123` |
| `TEAM004` | Team 04 | ₹10,000.00 | `TEST@123` |
| `TEAM005` | Team 05 | ₹10,000.00 | `TEST@123` |

---

## 8. Automated Test Suite

Run the full test suite with automated tests:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

### Dedicated Tests
- **Reading Time (10s), Bid Time (30s) & Balance Refresh Test**:
  ```powershell
  python -m unittest tests.test_reading_time_and_balance_refresh -v
  ```
- **Auction Lifecycle Test**:
  ```powershell
  python -m unittest tests.test_auction_lifecycle -v
  ```
- **Crash/Restart Recovery Test**:
  ```powershell
  python -m unittest tests.test_restart_recovery -v
  ```
- **100 Concurrent Teams Bidding Test**:
  ```powershell
  python -m unittest tests.test_concurrency -v
  ```

---

## 9. Production Deployment

For production deployments:
1. Set `FLASK_ENV=production` in `.env`.
2. Generate a cryptographically random `FLASK_SECRET_KEY`.
3. Use a production WSGI server with WebSocket support:
   ```bash
   gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
   ```
4. Put a reverse proxy (e.g. Nginx) in front with SSL termination and WebSocket upgrade headers.
5. Enable HTTPS so `SESSION_COOKIE_SECURE = True` protects cookies in transit.
