"""
Direct CLI for the multi-agent system — no HTTP layer.

The coordinator runs in-process here; FastAPI is only needed for HTTP consumers
(the React UI, or approving actions over REST). Useful for quick testing and for
scripted evaluation runs.

    python cli.py                          # interactive
    python cli.py "how many open defects?" # single question
    python cli.py --file questions.txt     # batch

Note this goes through Coordinator.chat(), which applies guardrails and memory.
Invoking the underlying LangGraph agent directly would skip both.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from agent_factory import AgentFactory


def _print_result(result: dict, show_agents: bool = True):
    print(result["response"])
    if show_agents:
        agents = result.get("agents_used") or []
        if result.get("blocked"):
            print(f"\n  [blocked: {result.get('block_reason')}]")
        elif agents:
            print(f"\n  [agents: {', '.join(agents)}]")


async def ask_once(coordinator, question: str, conversation_id: str):
    result = await coordinator.chat(question, conversation_id=conversation_id)
    _print_result(result)
    return result


async def interactive(coordinator, factory):
    print("Automotive MAS — type a question, or 'quit' to exit.")
    print("Commands: /pending, /approve <id>, /reject <id>\n")

    conversation_id = "cli-session"
    loop = asyncio.get_event_loop()

    while True:
        try:
            line = (await loop.run_in_executor(None, input, "> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            break

        if line.startswith("/"):
            _handle_command(line, factory)
            continue

        try:
            await ask_once(coordinator, line, conversation_id)
        except Exception as e:
            print(f"  error: {type(e).__name__}: {e}")
        print()


def _handle_command(line: str, factory):
    parts = line.split()
    cmd = parts[0].lower()
    store = factory.get_approval_store()

    if cmd == "/pending":
        actions = store.list_pending()
        if not actions:
            print("  no pending actions")
        for a in actions:
            print(f"  {a['action_id']}  {a['tool_name']}  {a['args']}")

    elif cmd == "/approve" and len(parts) > 1:
        action = store.approve(parts[1])
        if not action:
            print("  not found or already resolved")
        else:
            # The unwrapped tool — the registered one is approval-gated and
            # would simply re-queue the action.
            tool = factory.get_executable_tool(action["tool_name"])
            if tool is None:
                print(f"  no executable tool for '{action['tool_name']}'")
            else:
                result = tool.invoke(action["args"])
                store.set_result(parts[1], result)
                print(f"  executed: {result}")

    elif cmd == "/reject" and len(parts) > 1:
        ok = store.reject(parts[1], "rejected from CLI")
        print("  rejected" if ok else "  not found or already resolved")

    else:
        print("  usage: /pending | /approve <id> | /reject <id>")
    print()


async def main():
    parser = argparse.ArgumentParser(description="Automotive MAS CLI")
    parser.add_argument("question", nargs="*", help="question to ask")
    parser.add_argument("--file", help="file with one question per line")
    parser.add_argument("--conversation-id", default="cli-session")
    args = parser.parse_args()

    factory = AgentFactory()
    coordinator = factory.build()

    try:
        if args.file:
            questions = [
                q.strip()
                for q in Path(args.file).read_text().splitlines()
                if q.strip() and not q.startswith("#")
            ]
            for q in questions:
                print(f"\n=== {q}")
                await ask_once(coordinator, q, args.conversation_id)

        elif args.question:
            await ask_once(coordinator, " ".join(args.question), args.conversation_id)

        else:
            await interactive(coordinator, factory)

    finally:
        factory.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
