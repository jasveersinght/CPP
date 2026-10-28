-- MATH AUCTION Database Schema (MySQL 8.0 InnoDB)
-- Server-authoritative transactional architecture with ACID integrity

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS violations;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS submissions;
DROP TABLE IF EXISTS bids;
DROP TABLE IF EXISTS auctions;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS hosts;

SET FOREIGN_KEY_CHECKS = 1;

-- Host Administrators
CREATE TABLE hosts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Participating Teams
CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_code VARCHAR(20) NOT NULL UNIQUE,
    team_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    starting_balance DECIMAL(12, 2) NOT NULL DEFAULT 10000.00,
    current_balance DECIMAL(12, 2) NOT NULL DEFAULT 10000.00,
    questions_won INT NOT NULL DEFAULT 0,
    questions_completed INT NOT NULL DEFAULT 0,
    correct_answers INT NOT NULL DEFAULT 0,
    status ENUM('WAITING', 'BIDDING', 'WON', 'SOLVING', 'SUBMITTED', 'RESULT', 'COMPLETED') NOT NULL DEFAULT 'WAITING',
    violation_count INT NOT NULL DEFAULT 0,
    is_disqualified BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_team_balance_non_negative CHECK (current_balance >= 0.00),
    INDEX idx_team_code (team_code),
    INDEX idx_team_status (status),
    INDEX idx_team_disqualified (is_disqualified),
    INDEX idx_team_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Mathematical Question Bank
CREATE TABLE questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(60) NOT NULL,
    question_text TEXT NOT NULL,
    question_image VARCHAR(255) DEFAULT NULL,
    question_type ENUM('MCQ', 'Numerical', 'Text', 'Multiple Answer') NOT NULL,
    options JSON DEFAULT NULL,
    starting_bid DECIMAL(10, 2) NOT NULL DEFAULT 500.00,
    reward DECIMAL(10, 2) NOT NULL DEFAULT 2000.00,
    correct_answer TEXT NOT NULL,
    status ENUM('AVAILABLE', 'LIVE', 'QUESTION_ACTIVE', 'CORRECT', 'WRONG', 'COMPLETED', 'ENDED') NOT NULL DEFAULT 'AVAILABLE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_question_status (status),
    INDEX idx_question_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Live and Historic Auctions
CREATE TABLE auctions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    starting_bid DECIMAL(10, 2) NOT NULL,
    current_bid DECIMAL(10, 2) NOT NULL,
    current_bidder_id INT DEFAULT NULL,
    winner_team_id INT DEFAULT NULL,
    status ENUM('PENDING', 'LIVE', 'ENDED', 'CANCELLED') NOT NULL DEFAULT 'PENDING',
    started_at DATETIME(6) DEFAULT NULL,
    ends_at DATETIME(6) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE RESTRICT,
    FOREIGN KEY (current_bidder_id) REFERENCES teams(id) ON DELETE SET NULL,
    FOREIGN KEY (winner_team_id) REFERENCES teams(id) ON DELETE SET NULL,
    INDEX idx_auction_status (status),
    INDEX idx_auction_ends_at (ends_at),
    INDEX idx_auction_question (question_id),
    INDEX idx_auction_winner (winner_team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bid Ledger
CREATE TABLE bids (
    id INT AUTO_INCREMENT PRIMARY KEY,
    auction_id INT NOT NULL,
    team_id INT NOT NULL,
    bid_amount DECIMAL(10, 2) NOT NULL,
    bid_time DATETIME(6) NOT NULL,
    FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE RESTRICT,
    INDEX idx_bids_auction (auction_id),
    INDEX idx_bids_team (team_id),
    INDEX idx_bids_time (bid_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Answer Submissions for Won Questions
CREATE TABLE submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    auction_id INT NOT NULL UNIQUE,
    team_id INT NOT NULL,
    question_id INT NOT NULL,
    submitted_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    reward_credited DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE RESTRICT,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE RESTRICT,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE RESTRICT,
    INDEX idx_sub_team (team_id),
    INDEX idx_sub_question (question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Wallet Financial Transactions Ledger
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    auction_id INT DEFAULT NULL,
    transaction_type ENUM('STARTING_BALANCE', 'BID_PAYMENT', 'REWARD', 'PENALTY', 'ADJUSTMENT') NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    description VARCHAR(255) NOT NULL,
    balance_after DECIMAL(12, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE RESTRICT,
    FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE SET NULL,
    INDEX idx_tx_team (team_id),
    INDEX idx_tx_type (transaction_type),
    INDEX idx_tx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Anti-Cheating & Integrity Violations
CREATE TABLE violations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    violation_type VARCHAR(50) NOT NULL,
    violation_count INT NOT NULL,
    details VARCHAR(255) DEFAULT NULL,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    INDEX idx_viol_team (team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
