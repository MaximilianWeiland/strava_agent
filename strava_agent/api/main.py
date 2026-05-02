import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agents.mcp import MCPServerStdio
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from langfuse import get_client

from strava_agent.api.chat import router, init_agent
from strava_agent.api.db import init_db, close_db

load_dotenv()

# initialize Langfuse as the OTEL exporter before instrumenting
get_client()
# instrument the OpenAI Agents SDK — all Runner.run* calls are automatically traced to Langfuse
OpenAIAgentsInstrumentor().instrument()


# decorator turns the app into an asynchronous context manager
# code before yield runs on startup, after it on shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):

    # initialize the db, communication via db url (localhost)
    await init_db(os.environ["DATABASE_URL"])

    # start the MCP server which runs a child process, communication via stdio
    # with block ensures MCP server properly shuts down
    async with MCPServerStdio(
        name="Strava AI Agent",
        params={
            "command": "uv",
            "args": ["run", "strava_agent/mcp_server/mcp_server.py"],
        },
        cache_tools_list=True,
    ) as server:
        # initialize the agent
        await init_agent(server)
        yield
    # close the db after shutdown of the app
    await close_db()


app = FastAPI(lifespan=lifespan)

# allow frontend to communicate to the backend, otherwise browser would block
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# include the API endpoints for posting and deleting a chat
app.include_router(router)
