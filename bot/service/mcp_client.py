"""Minimal MCP stdio client.

Spawns the tradingview-mcp server (`node src/server.js`) as a subprocess and
talks JSON-RPC 2.0 over stdin/stdout. We only need three message types:

    1. initialize
    2. notifications/initialized
    3. tools/call

The client keeps the subprocess alive across polls. On unexpected exit it
auto-restarts on the next call.
"""

from __future__ import annotations

import asyncio
import json
import shlex
from typing import Any, Optional

from .config import settings
from .logging import log


class MCPError(Exception):
    pass


class MCPStdioClient:
    def __init__(self, cmd: str | None = None, cwd: str | None = None) -> None:
        self.cmd = cmd or settings.mcp_server_cmd
        self.cwd = cwd or settings.mcp_server_cwd
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._next_id = 0
        self._lock = asyncio.Lock()
        self._reader_task: Optional[asyncio.Task] = None
        self._responses: dict[int, asyncio.Future] = {}

    async def start(self) -> None:
        argv = shlex.split(self.cmd)
        self._proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=self.cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader_task = asyncio.create_task(self._read_stdout())
        asyncio.create_task(self._drain_stderr())
        await self._initialize()
        log.info("mcp_started", pid=self._proc.pid)

    async def stop(self) -> None:
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._proc.kill()
        if self._reader_task:
            self._reader_task.cancel()
        self._proc = None
        self._reader_task = None
        self._responses.clear()

    async def _ensure_alive(self) -> None:
        if self._proc is None or self._proc.returncode is not None:
            log.warning("mcp_restart")
            await self.stop()
            await self.start()

    async def _read_stdout(self) -> None:
        assert self._proc and self._proc.stdout
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                log.warning("mcp_stdout_eof")
                # Fail in-flight requests so callers can retry.
                for fut in self._responses.values():
                    if not fut.done():
                        fut.set_exception(MCPError("mcp server closed stdout"))
                self._responses.clear()
                return
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = msg.get("id")
            if rid is None:
                continue  # notification or server-originated request; ignore
            fut = self._responses.pop(rid, None)
            if fut and not fut.done():
                if "error" in msg:
                    fut.set_exception(MCPError(str(msg["error"])))
                else:
                    fut.set_result(msg.get("result"))

    async def _drain_stderr(self) -> None:
        assert self._proc and self._proc.stderr
        while True:
            line = await self._proc.stderr.readline()
            if not line:
                return
            text = line.decode(errors="replace").rstrip()
            if text:
                log.debug("mcp_stderr", line=text)

    async def _send(self, method: str, params: dict | None = None, *, is_notification: bool = False) -> Any:
        await self._ensure_alive()
        assert self._proc and self._proc.stdin
        if is_notification:
            msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
            self._proc.stdin.write((json.dumps(msg) + "\n").encode())
            await self._proc.stdin.drain()
            return None
        self._next_id += 1
        rid = self._next_id
        msg = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._responses[rid] = fut
        self._proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self._proc.stdin.drain()
        try:
            return await asyncio.wait_for(fut, timeout=30)
        except asyncio.TimeoutError as e:
            self._responses.pop(rid, None)
            raise MCPError(f"mcp call timed out: {method}") from e

    async def _initialize(self) -> None:
        await self._send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mnq-bot", "version": "0.1.0"},
            },
        )
        await self._send("notifications/initialized", {}, is_notification=True)

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        async with self._lock:
            result = await self._send(
                "tools/call", {"name": name, "arguments": arguments or {}}
            )
        # MCP tool results are { content: [{type:"text", text:"<json string>"}], isError?: bool }
        if not isinstance(result, dict):
            raise MCPError(f"unexpected mcp result shape: {result!r}")
        if result.get("isError"):
            raise MCPError(f"tool error: {result}")
        content = result.get("content") or []
        if not content:
            return {}
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise MCPError(f"tool returned non-json content: {text[:200]!r}") from e


_singleton: MCPStdioClient | None = None


async def get_mcp() -> MCPStdioClient:
    global _singleton
    if _singleton is None:
        _singleton = MCPStdioClient()
        await _singleton.start()
    return _singleton
