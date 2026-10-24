"""判分器：输入判分规则 + agent 结果，输出 (是否通过, 失败原因)。"""
from __future__ import annotations

import re
from pathlib import Path


def check(spec: dict, result: dict, workspace: Path) -> tuple[bool, str]:
    """spec 来自 tasks.yaml 的 check 字段；result 是 agent 跑完的结果。"""
    kind = spec.get("type")
    final = (result.get("answer") or result.get("final_answer") or "").strip()

    if kind == "contains":
        needle = str(spec["value"])
        if needle in final:
            return True, ""
        return False, f"答案中缺少 {needle!r}；实际答案：{final[:200]!r}"

    if kind == "contains_any":
        # 同一个事实有多种合法写法（2026-03-15 / 2026 年 3 月 15 日），
        # 判分不该因为格式判人失败
        needles = [str(v) for v in spec["values"]]
        for needle in needles:
            if needle in final:
                return True, ""
        return False, f"答案中缺少任一表述 {needles}；实际答案：{final[:200]!r}"

    if kind == "not_contains":
        needle = str(spec["value"])
        if needle not in final:
            return True, ""
        return False, f"答案中不应出现 {needle!r}"

    if kind == "regex":
        pattern = str(spec["value"])
        if re.search(pattern, final):
            return True, ""
        return False, f"答案不匹配正则 {pattern!r}；实际答案：{final[:200]!r}"

    if kind == "file_exists":
        p = workspace / str(spec["value"])
        if p.exists():
            return True, ""
        return False, f"文件不存在：{p}"

    if kind == "file_contains":
        p = workspace / str(spec["value"])
        text = str(spec.get("text", ""))
        if not p.exists():
            return False, f"文件不存在：{p}"
        content = p.read_text(encoding="utf-8", errors="ignore")
        if text in content:
            return True, ""
        return False, f"{p.name} 里找不到 {text!r}；实际内容：{content[:200]!r}"

    return False, f"未知的判分类型：{kind}"