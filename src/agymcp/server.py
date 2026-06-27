"""FastMCP server — 将 Antigravity CLI (agy) 包装为 MCP 工具。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("Antigravity MCP Server")

# 从 agy log 中提取会话 UUID 的正则
_CONV_RE = re.compile(r"(?:Created|Streaming) conversation ([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")


def _run_agy(cmd: list[str], cwd: str, log_path: str) -> tuple[str, Optional[str]]:
    """执行 agy 子进程，返回 (stdout文本, conversation_id)。"""
    agy_bin = shutil.which("agy") or "agy"
    cmd[0] = agy_bin

    proc = subprocess.Popen(
        cmd,
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # 日志走 --log-file，stderr 不需要
        universal_newlines=True,
        encoding="utf-8",
        cwd=cwd,
    )
    stdout, _ = proc.communicate(timeout=180)

    # 从 log 文件里解析 conversation UUID
    conversation_id: Optional[str] = None
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = _CONV_RE.search(line)
                if m:
                    conversation_id = m.group(1)
    except OSError:
        pass

    return stdout.strip(), conversation_id


@mcp.tool(
    name="agy",
    description="""
    调用 Antigravity CLI (agy) 执行 AI 任务，返回模型回复文本和会话 ID。

    **返回结构：**
    - `success`: 是否成功
    - `SESSION_ID`: 会话 UUID，用于多轮对话续话
    - `agent_messages`: 模型回复文本
    - `error`: 失败时的错误描述

    **使用规范：**
    - 每次调用后必须保存 `SESSION_ID`，多轮对话时通过 `SESSION_ID` 参数续话
    - 仅在用户明确指定时才传 `model` 参数
    - 前端设计、UI 组件、CSS 样式等任务优先使用此工具
    """,
    meta={"version": "0.1.0", "author": "local"},
)
async def agy(
    PROMPT: Annotated[str, "发送给 Antigravity 的任务指令。"],
    cd: Annotated[Path, "执行任务时 agy 的工作目录（workspace root）。"],
    SESSION_ID: Annotated[
        str,
        "续话会话 ID。为空时开启新会话，非空时继续指定会话。",
    ] = "",
    sandbox: Annotated[
        bool,
        Field(description="是否启用沙箱模式（文件修改隔离）。默认 False。"),
    ] = False,
    model: Annotated[
        str,
        "指定使用的模型。除非用户明确要求，否则留空让 agy 使用默认模型。",
    ] = "",
) -> Dict[str, Any]:
    """执行 agy CLI 并返回结果。"""

    if not cd.exists():
        return {
            "success": False,
            "error": f"工作目录不存在：{cd.absolute().as_posix()}",
        }

    # 用临时文件捕获 agy 日志（提取 conversation_id 用）
    log_fd, log_path = tempfile.mkstemp(suffix=".log", prefix="agymcp_")
    os.close(log_fd)

    cmd = ["agy", "--print", PROMPT, "--log-file", log_path]

    if sandbox:
        cmd.append("--sandbox")
    if model:
        cmd.extend(["--model", model])
    if SESSION_ID:
        cmd.extend(["--conversation", SESSION_ID])

    try:
        text, conv_id = _run_agy(cmd, cwd=cd.absolute().as_posix(), log_path=log_path)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "agy 执行超时（180s）"}
    except Exception as e:
        return {"success": False, "error": f"执行异常：{e}"}
    finally:
        try:
            os.unlink(log_path)
        except OSError:
            pass

    if conv_id is None:
        return {
            "success": False,
            "error": "无法从 agy 日志中获取 SESSION_ID，请检查 agy 是否正常运行。",
        }

    if not text:
        return {
            "success": False,
            "error": f"agy 返回了空响应。SESSION_ID={conv_id}，可用此 ID 续话。",
        }

    return {
        "success": True,
        "SESSION_ID": conv_id,
        "agent_messages": text,
    }


def run() -> None:
    """以 stdio 模式启动 MCP server。"""
    mcp.run(transport="stdio")
