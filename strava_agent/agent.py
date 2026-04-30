import asyncio

from dotenv import load_dotenv
from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServerStdio, MCPServer
from openai.types.responses import ResponseTextDeltaEvent

load_dotenv()

async def main() -> None:

    async with MCPServerStdio(
        name="Strava AI Agent",
        params={
            "command": "uv",
            "args": ["run", "strava_agent/mcp_server/mcp_server.py"],
        },
        cache_tools_list=True,
    ) as server:
        trace_id = gen_trace_id()

        with trace(workflow_name="Strava MCP Agent", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}\n")
            await run(server)



async def run(mcp_server: MCPServer):

    prompt_result = await mcp_server.get_prompt("system_prompt")
    instructions = prompt_result.messages[0].content.text

    agent = Agent(
        name="Personal Strava Agent",
        instructions=instructions,
        mcp_servers=[mcp_server]
    )

    input_items = []

    print("=== Strava Agent ===")
    print("Type 'exit' to end the conversation")

    while True:
        user_input = input("\nUser: ").strip()

        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        result = Runner.run_streamed(
            agent,
            input=input_items + [{"role": "user", "content": user_input}],
        )
        print("\nAgent: ", end="", flush=True)

        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    print(f"\n-- Calling {event.item.raw_item.name}...")
                elif event.item.type == "tool_call_output_item":
                    print("-- Tool call completed.")

        input_items = result.to_input_list()
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
