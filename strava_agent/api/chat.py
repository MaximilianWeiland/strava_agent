import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents import Agent, Runner
from agents.mcp import MCPServer
from openai.types.responses import ResponseTextDeltaEvent
from langfuse import propagate_attributes

from strava_agent.api.db import get_input_items, save_input_items

router = APIRouter()

_agent: Agent | None = None


async def init_agent(server: MCPServer) -> None:
    global _agent
    # get the system prompt stored on the MCP-server
    prompt_result = await server.get_prompt("system_prompt")
    instructions = prompt_result.messages[0].content.text
    # initialize the (globally set) agent
    _agent = Agent(
        name="Personal Strava Agent",
        instructions=instructions,
        mcp_servers=[server],
    )


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    # fetch current conversation history from db
    input_items = await get_input_items(req.session_id)

    async def stream():
        # attach session_id to the Langfuse trace so runs are grouped by conversation
        with propagate_attributes(session_id=req.session_id):
            # append the latest user message to the conversation history
            result = Runner.run_streamed(
                _agent,
                input=input_items + [{"role": "user", "content": req.message}],
            )
            # run the agent loop and yield SSE events as they come in
            async for event in result.stream_events():
                # send the (final) raw response to the frontend
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    yield f"data: {json.dumps({'type': 'text', 'delta': event.data.delta})}\n\n"
                # send the selected tool-name to the frontend
                elif event.type == "run_item_stream_event":
                    if event.item.type == "tool_call_item":
                        yield f"data: {json.dumps({'type': 'tool_call', 'name': event.item.raw_item.name})}\n\n"
            # save conversation history to the db and yield done message to frontend
            await save_input_items(req.session_id, result.to_input_list())
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    # stream response to the frontend instead of waiting for the final message
    return StreamingResponse(stream(), media_type="text/event-stream")


@router.delete("/chat/{session_id}")
async def clear_chat(session_id: str) -> dict:
    # wipe the full conversation history from the db
    await save_input_items(session_id, [])
    return {"status": "cleared"}
