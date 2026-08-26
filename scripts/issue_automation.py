#!/usr/bin/env python3
"""Parse and validate the task / delivery / review issue templates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

TASK_SECTION = "📋 任务描述"
TASK_DELIVERABLES = "✅ 交付清单"
TASK_META = "📊 任务元数据（Skill 解析用）"
TASK_REFERENCES = "📎 参考资料"
TASK_PRIORITY_VALUES = ("P0", "P1", "P2", "P3")
DELIVERY_LINK = "🔗 关联任务"
DELIVERY_STATUS = "✅ 交付清单完成情况"
DELIVERY_META = "📊 交付元数据（Skill 解析用）"
REVIEW_LINK = "🔗 审查任务"
REVIEW_CHECKLIST = "✅ 审查清单"
REVIEW_META = "📊 审查元数据（Skill 解析用）"
REVIEW_CONCLUSION = "🔄 审查结论"

PLACEHOLDER_PATTERNS = (
    "（可选）",
    "X 小时",
    "YYYY-MM-DD HH:MM",
    "YYYY-MM-DD",
    "1 / 2 / 3 / 4 / 5",
    "P0 / P1 / P2 / P3",
    "1-5",
    "#（编号）",
    "@（执行人）",
    "@（当前审查人）",
    "PR #XX",
    "commit XXX",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    pattern = rf"(?:^|\n)##\s+{re.escape(heading)}\s*\n([\s\S]*?)(?=\n##\s+|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def parse_markdown_table(text: str) -> Dict[str, str]:
    rows: List[List[str]] = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2:
            rows.append(cells)
    if len(rows) < 2:
        return {}
    result: Dict[str, str] = {}
    for row in rows[2:]:
        if len(row) >= 2:
            result[row[0]] = row[1]
    return result




def subsection(text: str, heading: str) -> str:
    pattern = rf"(?:^|\n)###\s+{re.escape(heading)}\s*\n([\s\S]*?)(?=\n###\s+|\n##\s+|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""

def parse_bullets(text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ["):
            continue
        checked = stripped.startswith("- [x]") or stripped.startswith("- [X]")
        label = re.sub(r"^- \[[ xX]\]\s*", "", stripped).strip()
        items.append({"checked": checked, "text": label})
    return items


def has_placeholder(value: str) -> bool:
    return any(marker in value for marker in PLACEHOLDER_PATTERNS)


def parse_task(text: str) -> Dict[str, Any]:
    meta = parse_markdown_table(section(text, TASK_META))
    return {
        "type": "task",
        "description": section(text, TASK_SECTION),
        "deliverables": parse_bullets(section(text, TASK_DELIVERABLES)),
        "complexity": meta.get("复杂度等级", "").strip(),
        "priority": meta.get("任务优先级", "").strip(),
        "estimate_hours": meta.get("预估工时", "").strip(),
        "ddl": meta.get("截止时间 (DDL)", "").strip(),
        "milestone": meta.get("关联里程碑", "").strip(),
        "references": section(text, TASK_REFERENCES),
        "raw_metadata": meta,
    }


def parse_delivery(text: str) -> Dict[str, Any]:
    meta = parse_markdown_table(section(text, DELIVERY_META))
    link = section(text, DELIVERY_LINK)
    issue_match = re.search(r"关联 Issue:\s*(#\S+)", link)
    self_score_match = re.search(r"自评分:\s*([1-5])/5", text)
    self_reason_match = re.search(r"理由:\s*(.+)$", text, re.M)
    return {
        "type": "delivery",
        "issue": issue_match.group(1) if issue_match else "",
        "completed_items": parse_bullets(subsection(section(text, DELIVERY_STATUS), "完全完成")),
        "conditional_items": parse_bullets(subsection(section(text, DELIVERY_STATUS), "有条件完成")),
        "unfinished_items": parse_bullets(subsection(section(text, DELIVERY_STATUS), "未完成")),
        "completion_percent": meta.get("完成度自评", "").strip(),
        "is_delayed": meta.get("是否延期", "").strip(),
        "delay_reason": meta.get("延期原因", "").strip(),
        "actual_finished_at": meta.get("实际完成时间", "").strip(),
        "deliverable_links": meta.get("交付物链接", "").strip(),
        "self_score": self_score_match.group(1) if self_score_match else "",
        "self_reason": self_reason_match.group(1).strip() if self_reason_match else "",
        "risk": section(text, "⚠️ 风险说明"),
        "next_step": section(text, "下一步"),
        "raw_metadata": meta,
    }


def parse_review(text: str) -> Dict[str, Any]:
    meta = parse_markdown_table(section(text, REVIEW_META))
    link = section(text, REVIEW_LINK)
    issue_match = re.search(r"关联 Issue:\s*(#\S+)", link)
    executor_match = re.search(r"执行人:\s*(@\S+)", link)
    reviewer_match = re.search(r"Reviewer:\s*(@\S+)", link)
    return {
        "type": "review",
        "issue": issue_match.group(1) if issue_match else "",
        "executor": executor_match.group(1) if executor_match else "",
        "reviewer": reviewer_match.group(1) if reviewer_match else "",
        "checklist": parse_bullets(section(text, REVIEW_CHECKLIST)),
        "score": meta.get("综合评分", "").strip(),
        "decision": meta.get("是否通过", "").strip(),
        "rejection_reason": meta.get("不通过原因", "").strip(),
        "notes": section(text, "📝 详细意见"),
        "conclusion_choices": parse_bullets(section(text, REVIEW_CONCLUSION)),
        "raw_metadata": meta,
    }


def require_non_placeholder(name: str, value: str, errors: List[str]) -> None:
    if not value or has_placeholder(value):
        errors.append(f"{name} 不能为空或占位符未清理。")


def validate_task(doc: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    require_non_placeholder("任务描述", doc["description"], errors)
    if len(doc["deliverables"]) < 1:
        errors.append("交付清单至少需要 1 个条目。")
    for idx, item in enumerate(doc["deliverables"], 1):
        if not item["text"] or has_placeholder(item["text"]):
            errors.append(f"交付清单第 {idx} 项不能为空或占位符未清理。")
    require_non_placeholder("复杂度等级", doc["complexity"], errors)
    require_non_placeholder("任务优先级", doc["priority"], errors)
    require_non_placeholder("预估工时", doc["estimate_hours"], errors)
    require_non_placeholder("截止时间 (DDL)", doc["ddl"], errors)
    if doc["complexity"] not in {"1", "2", "3", "4", "5"}:
        errors.append("复杂度等级必须是 1 到 5 的整数。")
    if doc["priority"] not in TASK_PRIORITY_VALUES:
        errors.append("任务优先级必须是 P0、P1、P2 或 P3。")
    if not re.fullmatch(r"\d+(?:\.\d+)?\s*小时", doc["estimate_hours"]):
        errors.append("预估工时格式必须类似 `8 小时`。")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", doc["ddl"]):
        errors.append("截止时间 (DDL) 格式必须为 `YYYY-MM-DD HH:MM`。")
    if doc["milestone"] and has_placeholder(doc["milestone"]):
        errors.append("关联里程碑占位符未清理。")
    return errors


def validate_delivery(doc: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    require_non_placeholder("关联 Issue", doc["issue"], errors)
    if not re.fullmatch(r"#\d+", doc["issue"]):
        errors.append("关联 Issue 必须是 `#编号` 格式。")
    all_items = doc["completed_items"] + doc["conditional_items"] + doc["unfinished_items"]
    if not all_items:
        errors.append("交付清单完成情况至少需要填写一项。")
    for name, items in (("完全完成", doc["completed_items"]), ("有条件完成", doc["conditional_items"]), ("未完成", doc["unfinished_items"])):
        for idx, item in enumerate(items, 1):
            if not item["text"] or has_placeholder(item["text"]):
                errors.append(f"{name} 第 {idx} 项不能为空或占位符未清理。")
    require_non_placeholder("完成度自评", doc["completion_percent"], errors)
    require_non_placeholder("是否延期", doc["is_delayed"], errors)
    require_non_placeholder("实际完成时间", doc["actual_finished_at"], errors)
    require_non_placeholder("交付物链接", doc["deliverable_links"], errors)
    if doc["completion_percent"] and not re.fullmatch(r"\d{1,3}%", doc["completion_percent"]):
        errors.append("完成度自评格式必须类似 `80%`。")
    if doc["is_delayed"] not in {"是", "否"}:
        errors.append("是否延期必须是 `是` 或 `否`。")
    if doc["actual_finished_at"] and not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", doc["actual_finished_at"]):
        errors.append("实际完成时间格式必须为 `YYYY-MM-DD HH:MM`。")
    if doc["self_score"] and not re.fullmatch(r"[1-5]", doc["self_score"]):
        errors.append("自评分必须是 1 到 5。")
    if doc["self_reason"] and has_placeholder(doc["self_reason"]):
        errors.append("自评理由占位符未清理。")
    return errors


def validate_review(doc: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    require_non_placeholder("关联 Issue", doc["issue"], errors)
    if not re.fullmatch(r"#\d+", doc["issue"]):
        errors.append("关联 Issue 必须是 `#编号` 格式。")
    require_non_placeholder("执行人", doc["executor"], errors)
    require_non_placeholder("Reviewer", doc["reviewer"], errors)
    if not doc["checklist"]:
        errors.append("审查清单至少需要 1 个条目。")
    for idx, item in enumerate(doc["checklist"], 1):
        if not item["text"] or has_placeholder(item["text"]):
            errors.append(f"审查清单第 {idx} 项不能为空或占位符未清理。")
    require_non_placeholder("综合评分", doc["score"], errors)
    require_non_placeholder("是否通过", doc["decision"], errors)
    if doc["score"] not in {"1", "2", "3", "4", "5"}:
        errors.append("综合评分必须是 1 到 5 的整数。")
    if doc["decision"] not in {"通过", "不通过", "有条件通过"}:
        errors.append("是否通过必须是 `通过`、`不通过` 或 `有条件通过`。")
    if doc["decision"] == "不通过" and not doc["rejection_reason"]:
        errors.append("不通过时必须填写不通过原因。")
    chosen = [item for item in doc["conclusion_choices"] if item["checked"]]
    if not chosen:
        errors.append("审查结论至少需要勾选一个选项。")
    return errors


def task_completion_stats(issues_path: Path) -> str:
    data = json.loads(issues_path.read_text(encoding="utf-8"))
    issues = data.get("items", data) if isinstance(data, dict) else data
    if not isinstance(issues, list):
        raise ValueError("任务统计输入必须是 Issue 对象数组，或包含 items 数组的对象。")

    stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "completed": 0, "unfinished": 0})
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        title = str(issue.get("title", ""))
        if not re.match(r"^\[TASK\]\s+\S", title):
            continue
        body = str(issue.get("body", ""))
        try:
            task = parse_task(body)
            priority = task.get("priority") or "未标注"
        except ValueError:
            priority = "未标注"
        state = str(issue.get("state", "")).lower()
        completed = state in {"closed", "completed"}
        stats[priority]["total"] += 1
        stats[priority]["completed" if completed else "unfinished"] += 1

    lines = ["| 优先级 | 总任务 | 已完成 | 未完成 | 完成率 |", "| --- | ---: | ---: | ---: | ---: |"]
    priorities = [priority for priority in TASK_PRIORITY_VALUES if priority in stats]
    priorities.extend(sorted(priority for priority in stats if priority not in TASK_PRIORITY_VALUES))
    for priority in priorities:
        item = stats[priority]
        total = item["total"]
        rate = (item["completed"] / total * 100) if total else 0.0
        lines.append("| {} | {} | {} | {} | {:.1f}% |".format(priority, total, item["completed"], item["unfinished"], rate))
    if len(lines) == 2:
        lines.append("| - | 0 | 0 | 0 | 0.0% |")
    return "\n".join(lines)


def format_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def parse_any(path: Path) -> Dict[str, Any]:
    text = read_text(path)
    if section(text, TASK_SECTION):
        return parse_task(text)
    if section(text, DELIVERY_LINK):
        return parse_delivery(text)
    if section(text, REVIEW_LINK):
        return parse_review(text)
    raise ValueError(f"无法识别模板类型: {path}")


def leaderboard(ledger: Path) -> str:
    lines = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return "| Member | Score | Events |\n| --- | ---: | ---: |"
    header = rows[0]
    data = rows[2:]
    scores = defaultdict(float)
    events = defaultdict(int)
    for row in data:
        if len(row) != len(header):
            continue
        item = dict(zip(header, row))
        actor = item.get("Actor", "")
        if not actor:
            continue
        try:
            delta = float(item.get("Delta", "0"))
        except ValueError:
            delta = 0.0
        scores[actor] += delta
        if item.get("Type") in {"reward", "penalty"}:
            events[actor] += 1
    lines_out = ["| Member | Score | Events |", "| --- | ---: | ---: |"]
    for actor, value in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])):
        lines_out.append(f"| {actor} | {value:.1f} | {events[actor]} |")
    return "\n".join(lines_out)


def cmd_validate(args: argparse.Namespace) -> int:
    parsed = parse_any(Path(args.file))
    if parsed["type"] == "task":
        errors = validate_task(parsed)
    elif parsed["type"] == "delivery":
        errors = validate_delivery(parsed)
    else:
        errors = validate_review(parsed)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(format_json(parsed))
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    print(format_json(parse_any(Path(args.file))))
    return 0


def cmd_leaderboard(args: argparse.Namespace) -> int:
    print(leaderboard(Path(args.ledger)))
    return 0


def cmd_task_stats(args: argparse.Namespace) -> int:
    print(task_completion_stats(Path(args.issues_json)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Issue template automation")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="Validate a task/delivery/review markdown file")
    p_validate.add_argument("file")
    p_validate.set_defaults(func=cmd_validate)

    p_parse = sub.add_parser("parse", help="Parse a task/delivery/review markdown file")
    p_parse.add_argument("file")
    p_parse.set_defaults(func=cmd_parse)

    p_board = sub.add_parser("leaderboard", help="Generate a leaderboard table from ledger/score-log.md")
    p_board.add_argument("ledger", nargs="?", default="ledger/score-log.md")
    p_board.set_defaults(func=cmd_leaderboard)

    p_task_stats = sub.add_parser("task-stats", help="Generate task completion statistics grouped by priority")
    p_task_stats.add_argument("issues_json", help="JSON file from GitHub Issues API or gh issue list --json")
    p_task_stats.set_defaults(func=cmd_task_stats)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
