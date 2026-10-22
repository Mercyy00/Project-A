# Benchmark Suite Script - Not a unit test
__test__ = False

import asyncio
import websockets
import json
import time

async def run_benchmark_query(q, mode="attentive"):
    uri = "ws://127.0.0.1:8000/ws/jarvis"
    try:
        async with asyncio.timeout(10.0):
            async with websockets.connect(uri) as ws:
                t0 = time.time()
                await ws.send(json.dumps({"action": "chat", "text": q, "mode": mode}))
                while True:
                    raw = await ws.recv()
                    msg = json.loads(raw)
                    if msg.get("type") == "response":
                        dur = time.time() - t0
                        print(f'[{dur:.2f}s] Query: "{q}" ({mode}) -> {msg.get("text")[:60]}...', flush=True)
                        break
    except Exception as exc:
        print(f'Query: "{q}" FAILED with {exc}', flush=True)

async def main():
    print("--- BENCHMARK SUITE ---", flush=True)
    await run_benchmark_query("Hello")
    await run_benchmark_query("What time is it?")
    await run_benchmark_query("System stats")
    await run_benchmark_query("What is the weather today?")
    await run_benchmark_query("Create a file on my desktop called jarvis_demo.txt with content Hello World", mode="combat")
    await run_benchmark_query("Status report", mode="combat")

if __name__ == "__main__":
    asyncio.run(main())
