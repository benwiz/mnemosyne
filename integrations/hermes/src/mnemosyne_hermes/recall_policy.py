"""Provider-boundary policy for rendering durable memory in Hermes prompts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class RecallItem:
    text: str
    category: str = "episodic"
    source: str = ""
    valid: bool = True
    superseded: bool = False
    task_id: str = ""
    relevance: float = 0.0


def normalize_item(raw: Any) -> RecallItem:
    if isinstance(raw, RecallItem):
        return raw
    if isinstance(raw, str):
        return RecallItem(text=raw)
    if isinstance(raw, Mapping):
        metadata = raw.get("metadata") or {}
        status = str(raw.get("status") or metadata.get("status") or "").casefold()
        return RecallItem(
            text=str(raw.get("text") or raw.get("content") or ""),
            category=str(raw.get("category") or metadata.get("category") or "episodic"),
            source=str(raw.get("source") or metadata.get("source") or ""),
            valid=bool(raw.get("valid", metadata.get("valid", True))) and status not in {"invalid", "expired"},
            superseded=(
                bool(raw.get("superseded", metadata.get("superseded", False)))
                or bool(raw.get("superseded_by") or metadata.get("superseded_by"))
                or status == "superseded"
            ),
            task_id=str(raw.get("task_id") or metadata.get("task_id") or ""),
            relevance=float(raw.get("relevance", metadata.get("relevance", 0.0)) or 0.0),
        )
    return RecallItem(text=str(raw))


def select_recall(
    records: Iterable[Any], *, query: str = "", task_id: str = "", limit: int = 24,
) -> list[RecallItem]:
    """Drop invalid memory and keep task progress opt-in and bounded."""
    query_l = query.casefold()
    continuation = any(x in query_l for x in ("where did we leave off", "continue", "status", "progress"))
    out: list[RecallItem] = []
    for raw in records:
        item = normalize_item(raw)
        if not item.text.strip() or not item.valid or item.superseded:
            continue
        is_task_progress = item.category == "task:progress" or "task:progress" in item.source.casefold()
        query_matches_task = bool(item.task_id and item.task_id.casefold() in query_l)
        if is_task_progress and not (
            continuation or query_matches_task or (task_id and item.task_id == task_id)
        ):
            continue
        out.append(item)
    out.sort(key=lambda item: item.relevance, reverse=True)
    return out[: max(0, limit)]


def render_context(records: Iterable[Any], *, query: str = "", task_id: str = "", char_budget: int = 6000) -> str:
    selected = select_recall(records, query=query, task_id=task_id)
    lines: list[str] = []
    used = 0
    for item in selected:
        line = f"- {item.text.strip()}"
        if used + len(line) + 1 > char_budget:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)
