# Personal Strava AI Agent

A personal AI assistant that lets you have conversations with your Strava data. Ask questions about your recent activities, your training progression, specfic segments or your planned routes.

## How it works

The agent uses an MCP server to expose Strava API endpoints as tools. When you ask a question, the AI decides which tools to call, fetches the relevant data, and synthesizes a response. Conversation history is persisted in a Postgres database. All conversations are traced via Langfuse.

To get an overview about all available tools (the Strava API endpoints) have a look at Strava's [Swagger Playground](https://developers.strava.com/playground/#/Activities/getLoggedInAthleteActivities).

## Stack

- **Frontend** — React + Vite, streams responses in real time
- **Backend** — FastAPI, manages the agent loop and conversation history
- **Agent** — OpenAI Agents SDK with a custom MCP server wrapping the Strava API
- **Database** — Postgres for storing the conversation history

## Prerequisites

- Python 3.13+
- Node.js 18+
- Docker (for Postgres)
- A Strava API application ([create one here](https://www.strava.com/settings/api)). You need a Strava access and refresh token which grants you access to retrieve data from your account.
- An OpenAI API key
- A Langfuse API key

## Setup

**1. Clone and install dependencies**
```bash
git clone <repo-url>
cd strava_agent
uv sync
cd frontend && npm install
```

**2. Configure environment variables**

Copy `.env.example` to `.env` and fill in your credentials:
```
OPENAI_API_KEY=...
STRAVA_CLIENT_ID=...
STRAVA_CLIENT_SECRET=...
STRAVA_ACCESS_TOKEN=...
STRAVA_REFRESH_TOKEN=...
STRAVA_TOKEN_EXPIRES_AT=...
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/strava_agent
LANGFUSE_SECRET_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_BASE_URL="https://cloud.langfuse.com"
```

**3. Start Postgres**
```bash
docker compose up -d
```

## Running locally

```bash
# Terminal 1 — backend
uv run uvicorn strava_agent.api.main:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `localhost:5173` and chat with your Strava data.