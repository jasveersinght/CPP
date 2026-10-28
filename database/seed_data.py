import os
import sys
import json
import logging
from werkzeug.security import generate_password_hash
from config import get_config
from database.db import get_db_connection

logger = logging.getLogger(__name__)

QUESTIONS_BANK_90 = [
    # CRYARITHMETIC (16 questions)
    {
        "id": 1,
        "category": "CRYARITHMETIC",
        "text": "In the cryptarithmetic addition SEND + MORE = MONEY, where each letter represents a distinct digit (0-9) and leading digits S and M are non-zero, what is the single integer value of the 5-digit sum MONEY?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2500.0,
        "correct_answer": "10652"
    },
    {
        "id": 2,
        "category": "CRYARITHMETIC",
        "text": "In the cryptarithmetic puzzle BASE + BALL = GAMES, where each distinct letter represents a unique digit from 0 to 9, what integer digit does the letter M represent?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "1"
    },
    {
        "id": 3,
        "category": "CRYARITHMETIC",
        "text": "In the cryptarithm TWO + TWO = FOUR, where each distinct letter represents a distinct digit (0-9), O=4, and W=3, what integer digit does F represent?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "1"
    },
    {
        "id": 4,
        "category": "CRYARITHMETIC",
        "text": "In the cryptarithmetic puzzle AB + BA = 121, where A and B are distinct non-zero digits and A - B = 3, what is the integer value of the product A * B?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "28"
    },
    {
        "id": 5,
        "category": "CRYARITHMETIC",
        "text": "In the cryptarithmetic puzzle USA + USSR = PEACE, where each letter represents a unique digit (0-9), what integer digit does the letter P represent?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2200.0,
        "correct_answer": "1"
    },
    {
        "id": 6,
        "category": "CRYARITHMETIC",
        "text": "In the alphametic equation CROSS + ROADS = DANGER with D=1, what is the integer value of the digit represented by R?",
        "type": "Numerical",
        "starting_bid": 600.0,
        "reward": 2600.0,
        "correct_answer": "8"
    },
    {
        "id": 7,
        "category": "CRYARITHMETIC",
        "text": "In the classic cryptarithm DONALD + GERALD = ROBERT with D=5, what is the integer digit represented by T?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "0"
    },
    {
        "id": 8,
        "category": "CRYARITHMETIC",
        "text": "In the cryptarithm FORTY + TEN + TEN = SIXTY, what is the single integer digit represented by the letter E?",
        "type": "Numerical",
        "starting_bid": 550.0,
        "reward": 2300.0,
        "correct_answer": "5"
    },
    {
        "id": 9,
        "category": "CRYARITHMETIC",
        "text": "In the sum TO + GO = OUT, where each letter represents a distinct digit (0-9) and T, G, O are non-zero, what integer digit does O represent?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "1"
    },
    {
        "id": 10,
        "category": "CRYARITHMETIC",
        "text": "In the alphametic puzzle NO + NO = TOO, where N, O, T are distinct digits and N and T are non-zero, what is the integer value of the 3-digit sum TOO?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "100"
    },
    {
        "id": 11,
        "category": "CRYARITHMETIC",
        "text": "In the alphametic HOCUS + POCUS = PRESTO with distinct letters and non-zero leading digits, what integer digit does P represent?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2200.0,
        "correct_answer": "1"
    },
    {
        "id": 12,
        "category": "CRYARITHMETIC",
        "text": "In the cryptarithm FLY + FLY = AWAY, where F and A are non-zero, what integer digit does the leading letter A represent?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "1"
    },
    {
        "id": 13,
        "category": "CRYARITHMETIC",
        "text": "In the addition ABC + ABC + ABC = CCC, where A, B, C are distinct non-zero digits, what is the integer value of the digit B?",
        "type": "Numerical",
        "starting_bid": 550.0,
        "reward": 2400.0,
        "correct_answer": "8"
    },
    {
        "id": 14,
        "category": "CRYARITHMETIC",
        "text": "In the alphametic DID + DID = DONE, where D is a non-zero digit producing a carry into D in the sum, what is the integer value of digit D?",
        "type": "Numerical",
        "starting_bid": 550.0,
        "reward": 2400.0,
        "correct_answer": "9"
    },
    {
        "id": 15,
        "category": "CRYARITHMETIC",
        "text": "In the cryptarithm EAT + THAT = APPLE, with distinct letters and leading digits E, T, A non-zero, what is the integer digit represented by A?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2100.0,
        "correct_answer": "1"
    },
    {
        "id": 16,
        "category": "CRYARITHMETIC",
        "text": "In the alphametic puzzle COCA + COLA = OASIS, where each letter represents a distinct digit from 0 to 9, what integer digit does O represent?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "1"
    },

    # FINTECH (17 questions)
    {
        "id": 17,
        "category": "FINTECH",
        "text": "A digital lending platform lends ₹10,000 at a compound interest rate of 20% per annum compounded annually. What is the total interest in Rupees accrued after exactly 2 years?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "4400"
    },
    {
        "id": 18,
        "category": "FINTECH",
        "text": "A cryptocurrency payment gateway charges a 2% fee on all merchant transactions. If a merchant receives a net amount of ₹49,000 after the fee is deducted, what was the gross transaction amount in Rupees?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "50000"
    },
    {
        "id": 19,
        "category": "FINTECH",
        "text": "An automated algorithmic savings wallet compounds ₹8,000 at an effective annual rate of 25%. What is the total maturity value in Rupees after 2 years?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2100.0,
        "correct_answer": "12500"
    },
    {
        "id": 20,
        "category": "FINTECH",
        "text": "A micro-investing app rounds up purchases to the nearest ₹10. Over one month, a user makes 60 purchases, each ending in exactly ₹3 (e.g. ₹43 rounded to ₹50, saving ₹7). What is the total amount in Rupees saved that month?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "420"
    },
    {
        "id": 21,
        "category": "FINTECH",
        "text": "A Buy-Now-Pay-Later (BNPL) provider charges a late fee of 5% on an overdue balance of ₹6,000, plus a flat processing fee of ₹150. What is the total penalty amount in Rupees?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "450"
    },
    {
        "id": 22,
        "category": "FINTECH",
        "text": "A peer-to-peer lending fund yields 15% simple interest per year. How many years will it take for an initial principal of ₹20,000 to earn an exact total interest of ₹9,000?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "3"
    },
    {
        "id": 23,
        "category": "FINTECH",
        "text": "An automated forex remittance platform offers an exchange rate of 1 USD = ₹83. If a flat wire transfer fee of ₹250 is deducted first from a ₹83,250 deposit, how many USD will the recipient receive?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "1000"
    },
    {
        "id": 24,
        "category": "FINTECH",
        "text": "A neo-bank offers a cashback incentive of ₹50 on every ₹2,500 spent on debit cards. If a customer spends a total of ₹75,000, what is the total cashback in Rupees earned?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 1900.0,
        "correct_answer": "1500"
    },
    {
        "id": 25,
        "category": "FINTECH",
        "text": "A robo-advisor portfolio starts with ₹100,000. In Year 1 it gains 20%, and in Year 2 it declines by 10%. What is the portfolio value in Rupees at the end of Year 2?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2100.0,
        "correct_answer": "108000"
    },
    {
        "id": 26,
        "category": "FINTECH",
        "text": "Under the financial Rule of 72, an investment account compounding annually at 8% will double in approximately how many years?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1600.0,
        "correct_answer": "9"
    },
    {
        "id": 27,
        "category": "FINTECH",
        "text": "A smart contract blockchain processes 40 transactions per block, with a new block produced every 12 seconds. How many total transactions are processed in exactly 3 minutes?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "600"
    },
    {
        "id": 28,
        "category": "FINTECH",
        "text": "An investor deposits ₹16,000 at 10% annual interest compounded semi-annually. What is the total maturity balance in Rupees after 1 year?",
        "type": "Numerical",
        "starting_bid": 550.0,
        "reward": 2200.0,
        "correct_answer": "17640"
    },
    {
        "id": 29,
        "category": "FINTECH",
        "text": "A fintech firm processes ₹1,200,000 in monthly transactions. If fraud detection algorithms reduce chargeback loss from 1.5% to 0.5%, how many Rupees are saved each month?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "12000"
    },
    {
        "id": 30,
        "category": "FINTECH",
        "text": "An equity crowdfunding startup raises ₹600,000 by issuing 12,000 equity shares. What is the offering price per share in Rupees?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "50"
    },
    {
        "id": 31,
        "category": "FINTECH",
        "text": "A high-yield digital deposit returns ₹1,331 at maturity on a principal of ₹1,000 compounded annually at 10%. What is the term of the deposit in years?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "3"
    },
    {
        "id": 32,
        "category": "FINTECH",
        "text": "A POS terminal distributor offers a cash discount of 4% for upfront invoice settlement. If the invoice amount is ₹25,000, what is the discounted payment amount in Rupees?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 1900.0,
        "correct_answer": "24000"
    },
    {
        "id": 33,
        "category": "FINTECH",
        "text": "An e-wallet loyalty rewards pool of ₹45,000 is distributed equally among 150 active winners. How many Rupees does each winner receive?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1600.0,
        "correct_answer": "300"
    },

    # TRADING MATHEMATICS (9 questions)
    {
        "id": 34,
        "category": "TRADING MATHEMATICS",
        "text": "A day trader buys 200 shares at ₹450 each and sells them at ₹485 each. If broker commissions total ₹600 for the round trip, what is the net profit in Rupees?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "6400"
    },
    {
        "id": 35,
        "category": "TRADING MATHEMATICS",
        "text": "A swing trader buys 50 shares of an asset at ₹300 and later buys 150 additional shares of the same asset at ₹340. What is the Volume-Weighted Average Price (VWAP) per share in Rupees?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "330"
    },
    {
        "id": 36,
        "category": "TRADING MATHEMATICS",
        "text": "An arbitrageur buys 40 units of Gold ETF on Exchange A at ₹5,200 and simultaneously sells on Exchange B at ₹5,280. If total transaction fees are ₹800, what is the net arbitrage profit in Rupees?",
        "type": "Numerical",
        "starting_bid": 550.0,
        "reward": 2300.0,
        "correct_answer": "2400"
    },
    {
        "id": 37,
        "category": "TRADING MATHEMATICS",
        "text": "A trader uses 5x margin leverage to buy stock worth ₹50,000 with ₹10,000 personal equity. If the stock price increases by 6%, what is the percentage return on the trader's ₹10,000 equity?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2100.0,
        "correct_answer": "30"
    },
    {
        "id": 38,
        "category": "TRADING MATHEMATICS",
        "text": "A futures contract lot size is 50. If the index futures price moves from 19,400 to 19,520 in favor of a long position holding 2 lots, what is the total profit in Rupees?",
        "type": "Numerical",
        "starting_bid": 600.0,
        "reward": 2500.0,
        "correct_answer": "12000"
    },
    {
        "id": 39,
        "category": "TRADING MATHEMATICS",
        "text": "A trader sets a stop-loss at 2% below an entry price of ₹850 and a profit target at 6% above entry. What is the integer reward multiple per unit of risk (Reward / Risk)?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1600.0,
        "correct_answer": "3"
    },
    {
        "id": 40,
        "category": "TRADING MATHEMATICS",
        "text": "A scalper executes 80 trades in a day: 50 winning trades gaining ₹400 each, and 30 losing trades losing ₹300 each. What is the day's total gross P&L in Rupees?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2100.0,
        "correct_answer": "11000"
    },
    {
        "id": 41,
        "category": "TRADING MATHEMATICS",
        "text": "A short seller borrows and sells 120 shares at ₹650 each. Later, the seller covers the position by buying back all shares at ₹575 each. What is the gross profit in Rupees?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "9000"
    },
    {
        "id": 42,
        "category": "TRADING MATHEMATICS",
        "text": "An algorithmic market maker places bids at ₹995 and asks at ₹1,005 on an order book. If both orders execute for 100 shares each, what is the captured spread profit in Rupees?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "1000"
    },

    # COMPUTER TECHNOLOGY (17 questions)
    {
        "id": 43,
        "category": "COMPUTER TECHNOLOGY",
        "text": "How many total address bits are required to uniquely address 4 Kilobytes (4,096 bytes) of byte-addressable computer memory?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1600.0,
        "correct_answer": "12"
    },
    {
        "id": 44,
        "category": "COMPUTER TECHNOLOGY",
        "text": "Convert the 8-bit unsigned binary number 10110100 into its equivalent decimal integer value.",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "180"
    },
    {
        "id": 45,
        "category": "COMPUTER TECHNOLOGY",
        "text": "In an IPv4 subnet with a subnet mask of 255.255.255.224 (/27), what is the maximum number of usable host IP addresses available?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "30"
    },
    {
        "id": 46,
        "category": "COMPUTER TECHNOLOGY",
        "text": "What is the maximum number of nodes in a complete binary tree of height 5 (where the root node is at height 0)?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "63"
    },
    {
        "id": 47,
        "category": "COMPUTER TECHNOLOGY",
        "text": "An algorithm with O(N^2) time complexity takes 4 seconds to process an array of 1,000 elements. How many seconds will it take to process an array of 3,000 elements on identical hardware?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2100.0,
        "correct_answer": "36"
    },
    {
        "id": 48,
        "category": "COMPUTER TECHNOLOGY",
        "text": "What is the decimal integer value of the hexadecimal number 0x2FA?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1900.0,
        "correct_answer": "762"
    },
    {
        "id": 49,
        "category": "COMPUTER TECHNOLOGY",
        "text": "A network connection provides a bandwidth of 100 Megabits per second (Mbps). How many Megabytes (MB) of data can be transferred in 16 seconds? (1 Byte = 8 bits)",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "200"
    },
    {
        "id": 50,
        "category": "COMPUTER TECHNOLOGY",
        "text": "A hash table has a capacity of 128 buckets. If 96 key-value pairs are stored, what is the load factor expressed as an integer percentage?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1600.0,
        "correct_answer": "75"
    },
    {
        "id": 51,
        "category": "COMPUTER TECHNOLOGY",
        "text": "In relational database design, if a relation with composite primary key components contains zero partial functional dependencies on any candidate key, how many partial dependencies exist?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1500.0,
        "correct_answer": "0"
    },
    {
        "id": 52,
        "category": "COMPUTER TECHNOLOGY",
        "text": "A CPU executes a program requiring 10,000,000 clock cycles on a 2.0 GHz processor. How many milliseconds does the execution take?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "5"
    },
    {
        "id": 53,
        "category": "COMPUTER TECHNOLOGY",
        "text": "What is the maximum number of directed edges in a simple directed graph with 10 vertices containing no self-loops?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "90"
    },
    {
        "id": 54,
        "category": "COMPUTER TECHNOLOGY",
        "text": "What is the decimal output of the bitwise XOR operation (45 XOR 27)?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "54"
    },
    {
        "id": 55,
        "category": "COMPUTER TECHNOLOGY",
        "text": "A RAID 5 disk array consists of 6 physical hard drives of 2 Terabytes each. What is the usable data storage capacity in Terabytes?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "10"
    },
    {
        "id": 56,
        "category": "COMPUTER TECHNOLOGY",
        "text": "What is the maximum number of comparisons needed in the worst case to locate an element in a sorted array of 1,024 elements using Binary Search?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "11"
    },
    {
        "id": 57,
        "category": "COMPUTER TECHNOLOGY",
        "text": "How many unique 8-bit byte sequences contain exactly 3 ones and 5 zeros?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "56"
    },
    {
        "id": 58,
        "category": "COMPUTER TECHNOLOGY",
        "text": "In the standard IEEE 754 single-precision 32-bit floating-point format, how many total bits are allocated for the exponent field?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1600.0,
        "correct_answer": "8"
    },
    {
        "id": 59,
        "category": "COMPUTER TECHNOLOGY",
        "text": "A B+ tree index has 10 keys per node. In a 3-level tree where each internal node has 10 children and each leaf node holds 10 records, what is the maximum number of records indexed?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "1000"
    },

    # STOCK & TRADING CONCEPTS (4 questions)
    {
        "id": 60,
        "category": "STOCK & TRADING CONCEPTS",
        "text": "A company has 5,000,000 shares outstanding trading at ₹120 per share. What is the company's total market capitalization in Millions of Rupees?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "600"
    },
    {
        "id": 61,
        "category": "STOCK & TRADING CONCEPTS",
        "text": "A listed company reports net profit of ₹80,000,000 with 4,000,000 shares outstanding. If its current market share price is ₹400, what is its Price-to-Earnings (P/E) ratio?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "20"
    },
    {
        "id": 62,
        "category": "STOCK & TRADING CONCEPTS",
        "text": "A corporation announces a 1-for-4 bonus share issue (1 free share for every 4 held). If a shareholder holds 600 shares, how many total shares will they hold after the distribution?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "750"
    },
    {
        "id": 63,
        "category": "STOCK & TRADING CONCEPTS",
        "text": "A blue-chip stock trading at ₹250 pays an annual cash dividend of ₹15 per share. What is the dividend yield expressed as an integer percentage?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1600.0,
        "correct_answer": "6"
    },

    # PROBABILITY (8 questions)
    {
        "id": 64,
        "category": "PROBABILITY",
        "text": "A box contains 8 red, 7 green, and 5 blue tokens. If one token is drawn at random, what is the probability (expressed as an integer percentage) that it is NOT green?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "65"
    },
    {
        "id": 65,
        "category": "PROBABILITY",
        "text": "When three fair 6-sided dice are rolled simultaneously, what is the total number of distinct outcomes in the sample space?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "216"
    },
    {
        "id": 66,
        "category": "PROBABILITY",
        "text": "A fair coin is tossed 3 times. What is the total number of distinct outcomes that yield at least one Head?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1500.0,
        "correct_answer": "7"
    },
    {
        "id": 67,
        "category": "PROBABILITY",
        "text": "In a lottery of 100 tickets numbered 1 to 100, one ticket is drawn at random. What is the probability (as an integer percentage) that the ticket number is a multiple of 4?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "25"
    },
    {
        "id": 68,
        "category": "PROBABILITY",
        "text": "Two fair 6-sided dice are rolled. In how many different outcomes does the sum of the numbers equal exactly 8?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "5"
    },
    {
        "id": 69,
        "category": "PROBABILITY",
        "text": "How many total face cards (Jacks, Queens, Kings) are present in a standard deck of 52 playing cards?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1500.0,
        "correct_answer": "12"
    },
    {
        "id": 70,
        "category": "PROBABILITY",
        "text": "A bag contains 6 black balls and 4 white balls. How many distinct pairs of balls can be chosen simultaneously without replacement?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "45"
    },
    {
        "id": 71,
        "category": "PROBABILITY",
        "text": "A committee of 3 members is chosen at random from a group of 8 candidates. What is the total number of different ways to form the committee?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "56"
    },

    # PERMUTATION & COMBINATION (8 questions)
    {
        "id": 72,
        "category": "PERMUTATION & COMBINATION",
        "text": "In how many distinct ways can the letters of the word AUCTION be arranged using all letters without repetition?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "5040"
    },
    {
        "id": 73,
        "category": "PERMUTATION & COMBINATION",
        "text": "How many 4-digit positive integers can be formed using the digits 1, 2, 3, 4, 5, 6 with no digit repeated?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "360"
    },
    {
        "id": 74,
        "category": "PERMUTATION & COMBINATION",
        "text": "In how many ways can 6 executives be seated around a circular conference table?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "120"
    },
    {
        "id": 75,
        "category": "PERMUTATION & COMBINATION",
        "text": "How many distinct diagonals can be drawn in a regular decagon (a polygon having 10 sides)?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "35"
    },
    {
        "id": 76,
        "category": "PERMUTATION & COMBINATION",
        "text": "A sports squad of 11 players must be selected from a pool of 14 available athletes. In how many distinct ways can the squad be selected?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2100.0,
        "correct_answer": "364"
    },
    {
        "id": 77,
        "category": "PERMUTATION & COMBINATION",
        "text": "In how many distinct ways can the letters of the word LEADER be arranged?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1900.0,
        "correct_answer": "360"
    },
    {
        "id": 78,
        "category": "PERMUTATION & COMBINATION",
        "text": "How many even 3-digit numbers can be formed using digits 2, 3, 4, 5, 6 without repeating any digit?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "36"
    },
    {
        "id": 79,
        "category": "PERMUTATION & COMBINATION",
        "text": "How many total handshakes occur at an event where 12 participants each shake hands with every other participant exactly once?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "66"
    },

    # TIME/WORK & RELATIONS (6 questions)
    {
        "id": 80,
        "category": "TIME/WORK & RELATIONS",
        "text": "Worker A can complete a task in 12 days, and Worker B can complete the same task in 24 days. Working together, in how many days can they complete the task?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "8"
    },
    {
        "id": 81,
        "category": "TIME/WORK & RELATIONS",
        "text": "Pipe X fills a reservoir in 15 hours, and Pipe Y fills it in 30 hours. If both pipes are opened simultaneously, how many hours will it take to fill the reservoir?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "10"
    },
    {
        "id": 82,
        "category": "TIME/WORK & RELATIONS",
        "text": "If 15 analysts can complete 60 portfolio reviews in 8 days, how many portfolio reviews can 20 analysts complete in 6 days at the same pace?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "60"
    },
    {
        "id": 83,
        "category": "TIME/WORK & RELATIONS",
        "text": "A water inlet pipe fills a tank in 6 hours, but with a drain leak open it takes 8 hours to fill. How many hours would the leak alone take to completely empty a full tank?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "24"
    },
    {
        "id": 84,
        "category": "TIME/WORK & RELATIONS",
        "text": "Pointing to a boy in a photograph, John says: 'His mother is the only daughter of my mother.' (Enter 1 for Son, 2 for Nephew, 3 for Brother). What is the integer code for the relation?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "2"
    },
    {
        "id": 85,
        "category": "TIME/WORK & RELATIONS",
        "text": "Engineer A completes a design in 20 days, and Engineer B completes it in 30 days. In how many days can both engineers finish the design working together?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "12"
    },

    # RATIO/PROPORTION/VARIATION (5 questions)
    {
        "id": 86,
        "category": "RATIO/PROPORTION/VARIATION",
        "text": "The ratio of two capital allocations is 7:9. If the larger allocation is ₹45,000, what is the value of the smaller allocation in Rupees?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "35000"
    },
    {
        "id": 87,
        "category": "RATIO/PROPORTION/VARIATION",
        "text": "Three project investments A, B, and C are in the continuous ratio 2:3:5. If the sum of all three investments is ₹100, what is the integer value of investment C?",
        "type": "Numerical",
        "starting_bid": 400.0,
        "reward": 1600.0,
        "correct_answer": "50"
    },
    {
        "id": 88,
        "category": "RATIO/PROPORTION/VARIATION",
        "text": "A prize pool of ₹7,200 is divided among three participants X, Y, and Z in the ratio 2:3:4. How many Rupees does participant Y receive?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "2400"
    },
    {
        "id": 89,
        "category": "RATIO/PROPORTION/VARIATION",
        "text": "What is the fourth proportional to the numbers 12, 18, and 24?",
        "type": "Numerical",
        "starting_bid": 450.0,
        "reward": 1800.0,
        "correct_answer": "36"
    },
    {
        "id": 90,
        "category": "RATIO/PROPORTION/VARIATION",
        "text": "The price of a rare alloy varies directly as the square of its weight. A piece weighing 3 grams costs ₹1,800. What is the cost in Rupees of a piece of the same alloy weighing 5 grams?",
        "type": "Numerical",
        "starting_bid": 500.0,
        "reward": 2000.0,
        "correct_answer": "5000"
    }
]

def seed_host():
    """Seed host admin account."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            host_user = 'admin'
            host_pass = 'host123'
            host_hash = generate_password_hash(host_pass)
            cursor.execute(
                "INSERT INTO hosts (username, password_hash) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash)",
                (host_user, host_hash)
            )
        conn.commit()
        logger.info(f"Host seeded: {host_user}")
    finally:
        conn.close()

def seed_teams(count=80, default_password='TEST@123'):
    """
    Idempotently seeds sample test teams (TEAM001 to TEAM080).
    Ensures each has starting balance, correct status, and starting transaction.
    """
    cfg = get_config()
    starting_bal = getattr(cfg, 'STARTING_WALLET_BALANCE', 10000.0)
    target_count = getattr(cfg, 'MAX_TEAMS', count)
    pwd_hash = generate_password_hash(default_password)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for i in range(1, target_count + 1):
                code = f"TEAM{i:03d}"
                name = f"Team {i:02d}"
                cursor.execute(
                    """
                    INSERT INTO teams (
                        team_code, team_name, password_hash, starting_balance, current_balance,
                        questions_won, questions_completed, correct_answers, status,
                        violation_count, is_disqualified, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, 0, 0, 0, 'WAITING', 0, FALSE, TRUE)
                    ON DUPLICATE KEY UPDATE
                        team_name = VALUES(team_name),
                        password_hash = VALUES(password_hash),
                        is_active = TRUE
                    """,
                    (code, name, pwd_hash, starting_bal, starting_bal)
                )
                team_id = cursor.lastrowid
                if not team_id:
                    cursor.execute("SELECT id FROM teams WHERE team_code = %s", (code,))
                    row = cursor.fetchone()
                    team_id = row['id'] if row else None

                if team_id:
                    # Ensure starting balance transaction exists
                    cursor.execute(
                        "SELECT id FROM transactions WHERE team_id = %s AND transaction_type = 'STARTING_BALANCE'",
                        (team_id,)
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            """
                            INSERT INTO transactions (team_id, transaction_type, amount, description, balance_after)
                            VALUES (%s, 'STARTING_BALANCE', %s, 'Initial competition purse credit', %s)
                            """,
                            (team_id, starting_bal, starting_bal)
                        )
        conn.commit()
        logger.info(f"Successfully seeded {target_count} teams (TEAM001 - TEAM{target_count:03d}) with INR {starting_bal:,.2f}")
    finally:
        conn.close()

def seed_questions():
    """
    Idempotently seeds exactly 90 questions across the CRYTEX domains.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for q in QUESTIONS_BANK_90:
                cursor.execute(
                    """
                    INSERT INTO questions (
                        id, category, question_text, question_image, question_type,
                        options, starting_bid, reward, correct_answer, status
                    )
                    VALUES (%s, %s, %s, NULL, %s, NULL, %s, %s, %s, 'AVAILABLE')
                    ON DUPLICATE KEY UPDATE
                        category = VALUES(category),
                        question_text = VALUES(question_text),
                        question_type = VALUES(question_type),
                        starting_bid = VALUES(starting_bid),
                        reward = VALUES(reward),
                        correct_answer = VALUES(correct_answer),
                        status = IF(status = 'AVAILABLE', 'AVAILABLE', status)
                    """,
                    (
                        q['id'],
                        q['category'],
                        q['text'],
                        q['type'],
                        q['starting_bid'],
                        q['reward'],
                        q['correct_answer']
                    )
                )
        conn.commit()
        logger.info(f"Successfully seeded exactly {len(QUESTIONS_BANK_90)} CRYTEX questions in question bank.")
    finally:
        conn.close()

def reset_test_data():
    """
    Resets all dynamic competition state for clean event or testing runs.
    Preserves registered teams and questions bank.
    Only available in development / testing mode.
    """
    cfg = get_config()
    starting_bal = getattr(cfg, 'STARTING_WALLET_BALANCE', 10000.0)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Clean transactions, submissions, bids, auctions, violations
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("TRUNCATE TABLE violations")
            cursor.execute("TRUNCATE TABLE submissions")
            cursor.execute("TRUNCATE TABLE bids")
            cursor.execute("TRUNCATE TABLE auctions")
            cursor.execute("TRUNCATE TABLE transactions")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            # 2. Reset questions to AVAILABLE
            cursor.execute("UPDATE questions SET status = 'AVAILABLE'")

            # 3. Reset all teams to fresh starting state
            cursor.execute(
                """
                UPDATE teams
                SET current_balance = %s,
                    starting_balance = %s,
                    questions_won = 0,
                    questions_completed = 0,
                    correct_answers = 0,
                    status = 'WAITING',
                    violation_count = 0,
                    is_disqualified = FALSE
                """,
                (starting_bal, starting_bal)
            )

            # 4. Re-create starting balance transactions for all teams
            cursor.execute("SELECT id FROM teams")
            teams = cursor.fetchall()
            for t in teams:
                cursor.execute(
                    """
                    INSERT INTO transactions (team_id, transaction_type, amount, description, balance_after)
                    VALUES (%s, 'STARTING_BALANCE', %s, 'Initial competition purse credit', %s)
                    """,
                    (t['id'], starting_bal, starting_bal)
                )

        conn.commit()
        logger.info("Competition test data successfully reset.")
    finally:
        conn.close()
