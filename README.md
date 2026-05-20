# Feed Intelligence

LinkedIn feed analyzer for content strategy. Scrapes your feed via Chrome, classifies posts with Claude, and generates a dark-themed intelligence report with actionable recommendations.

Built with [Claude Agent SDK](https://claude.salient.community/) + Next.js.

By [Gleb Kalinin](https://github.com/glebis).

## Architecture

```
web/          Next.js frontend (dark intelligence-tool UI)
  app/page.tsx        Dashboard with streaming status + report iframe
  app/api/analyze/    SSE endpoint that spawns the Python agent

agent/        Python Agent SDK agent
  main.py             Orchestrator with 3 tools: scrape → classify → report
  scraper.py          LinkedIn feed scraper via Chrome DevTools Protocol
  post_store.py       Persistent JSON store with dedup + file locking
  mock_data.py        Mock posts for testing without Chrome
```

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Chrome Beta with `--remote-debugging-port=9222`
- `agent-browser` CLI
- Anthropic API key

### Install

```bash
# Agent
cd agent
pip install -r requirements.txt
cp .env.example .env  # add your ANTHROPIC_API_KEY

# Frontend
cd web
npm install
```

### Run

1. Launch Chrome Beta with debug port:
```bash
"/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.chrome-beta-profile" &
```

2. Log into LinkedIn in Chrome Beta (first time only — session persists)

3. Start the dashboard:
```bash
cd web && PORT=3737 npm run dev
```

4. Open http://localhost:3737 and click **Run Analysis**

## Features

- Real LinkedIn feed scraping via Chrome DevTools Protocol
- Post deduplication across runs (persistent JSON store)
- Promoted post detection and filtering
- Topic/engagement/format/promoted filters in the report
- Clickable author profiles
- Dark intelligence-tool aesthetic (JetBrains Mono, red accent)
- XSS-safe report rendering in sandboxed iframe
- Origin-locked API with concurrency protection
