# BTC Desk Live

A personal, paper-money dashboard for a small team of AI bots that make practice bets on
Polymarket's **"Bitcoin Up or Down"** markets. This is Reed's own project. It is shared with a few
friends to look at, not offered to the public.

## What you're looking at

Every 5 minutes (and, on a separate desk, every 15 minutes) Polymarket opens a market asking one
question: **will Bitcoin's price be higher at the end of this window than at the start?**

- The price comes from Chainlink, averaged over the last 60 seconds (TWAP60).
- If the end price is **equal to or higher than** the start price, **UP** wins. Ties count as UP.
- A winning share pays **$1**. You buy shares at whatever price the market charges, e.g. 84¢.
  A $14 bet at 84¢ buys about 16.7 shares, which pay $16.67 if right and $0 if wrong.

Each open bet on the dashboard says in plain words what was bet, what it pays, the start price to
beat, whether it's winning right now, and when the window closes. After a window closes the
official result takes a few minutes to post (about 5–6 minutes on 5m, about 30 minutes on 15m).
The card shows when to expect it, then shows **WON** or **LOST** for two minutes.

**Everything is paper money. No real trades are placed.**

## How the desk works

Each desk (5m and 15m) is a chain of bots, and their totals are always kept separate:

1. **Tracker** watches the market and Bitcoin price feeds and records the start price.
2. **Analyst** estimates how likely the current leader is to hold, and what the order book costs.
3. **Predictor** decides whether to bet (flat $14) or skip, following written entry rules
   (price limits, minimum edge, a "pair lock" that buys both sides when together they cost under $1,
   and an early cash-out at 95¢).
4. **Risk** has a veto. It pauses the desk after 2 red days in a row, 5 losses in a row, or
   accuracy under 50% after 20+ calls, and checks every bet against the rules.

An Orchestrator bot coordinates each desk. Rule changes need Risk's sign-off.

## How the page gets its data

The bots write to files on a private machine. `pusher.py` packs a snapshot every few seconds,
**encrypts it** (AES-GCM, key derived from a passphrase) and uploads it to a Firebase Realtime
Database. This page (GitHub Pages) streams that blob and decrypts it in your browser after you
enter the passphrase. Without the passphrase the data is unreadable.

## Want your own? Fork it — don't contribute here

This repo stays Reed's alone. **Pull requests, issues, and contributions are not accepted.**
If a friend (or a friend's AI agent) wants to run this, **fork or copy the repo and run your own
copy**; any changes you make stay in your fork.

What you'll need to set up yourself, because **none of these secrets are in this repo**:

- **Your own bots** writing the desk files (`predictions.jsonl`, `current.json`,
  `analysis_current.json`, `risk_state.json`, `paper_summary.json`, heartbeats) to a folder like
  `/home/box/shared/btc5m/`. The dashboard only reads them.
- **Your own passphrase** (`.passphrase`, never committed) used to encrypt the data.
- **Your own Firebase Realtime Database** with public read and secret-only writes; put its URL in
  `index.html` / `pusher.py` and its secret in `.firebase_secret` (never committed).
- **GitHub Pages** turned on for your fork.

Then run `watchdog.sh`, which keeps `pusher.py` running. `HANDOFF.md` has the technical details.

Not financial advice. It's a learning project that runs on paper money.
