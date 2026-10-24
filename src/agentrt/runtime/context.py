"""上下文压缩：控制 messages 的体积。

铁律：绝不能删掉 assistant(tool_calls) 与对应 tool 消息的配对，
否则 API 会返回 400。只能压缩 content，不能拆散结构。
"""
from __future__ import annotations

import json

# L1：单条工具输出上限（字符）
MAX_TOOL_CONTENT = 3000
# L2：最近多少条消息保持原样
KEEP_RECENT = 6
# L2：被裁的老消息，其 content 保留多少字符
OLD_HEAD = 200
OLD_TAIL = 100


def _shrink_text(text: str, head: int, tail: int) -> str:
    """保留头 head 字符 + 尾 tail 字符，中间用省略标记代替。"""
    if len(text) <= head + tail + 40:
        return text
    omitted = len(text) - head - tail
    return f"{text[:head]}\n...[省略 {omitted} 字符]...\n{text[-tail:]}"


def compress_messages(messages: list[dict], keep_recent: int = KEEP_RECENT) -> list[dict]:
    """返回压缩后的新列表，不修改原列表。"""
    if not messages:
        return []

    # system 永远完整保留
    system = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]

    # 分界点：最近 keep_recent 条不动
    cut = max(0, len(rest) - keep_recent)
    old, recent = rest[:cut], rest[cut:]

    out: list[dict] = list(system)

    for m in old:
        role = m.get("role")
        new = dict(m)                      # 浅拷贝，只改 content

        if role == "tool":
            content = new.get("content") or ""
            if len(content) > MAX_TOOL_CONTENT:
                new["content"] = _shrink_text(content, MAX_TOOL_CONTENT * 3 // 5,
                                             MAX_TOOL_CONTENT * 2 // 5)
            else:
                new["content"] = _shrink_text(content, OLD_HEAD, OLD_TAIL)
            # tool_call_id 必须原样保留
        elif role == "assistant":
            content = new.get("content") or ""
            if content:
                new["content"] = _shrink_text(content, OLD_HEAD, OLD_TAIL)
            # tool_calls 原样保留！否则下面的 tool 消息会变成孤儿
        elif role == "user":
            content = new.get("content") or ""
            new["content"] = _shrink_text(content, OLD_HEAD, OLD_TAIL)

        out.append(new)

    out.extend(recent)
    return out


def estimate_chars(messages: list[dict]) -> int:
    """粗估字符数（1 token ≈ 1.5 中文字符 / 4 英文字符，这里只用于对比）。"""
    total = 0
    for m in messages:
        total += len(m.get("content") or "")
        if m.get("tool_calls"):
            total += len(json.dumps(m["tool_calls"], ensure_ascii=False))
    return total