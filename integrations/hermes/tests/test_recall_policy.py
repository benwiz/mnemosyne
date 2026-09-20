from mnemosyne_hermes.recall_policy import render_context, select_recall


def test_unrelated_requests_do_not_receive_task_progress():
    records = [
        {"text": "Open issue 42 is halfway complete", "category": "task:progress", "task_id": "issue-42"},
        {"text": "User prefers concise answers", "category": "stable"},
    ]
    rendered = render_context(records, query="What is the weather?")
    assert "halfway" not in rendered
    assert "concise" in rendered


def test_matching_continuation_retrieves_task_progress():
    records = [{"text": "Open issue 42 is halfway complete", "category": "task:progress", "task_id": "issue-42"}]
    rendered = render_context(records, query="Where did we leave off on issue 42?")
    assert "halfway complete" in rendered


def test_invalid_and_superseded_records_are_not_rendered():
    records = [
        {"text": "old preference", "category": "stable", "superseded": True},
        {"text": "invalid preference", "category": "stable", "valid": False},
        {"text": "current preference", "category": "stable", "valid": True},
    ]
    assert render_context(records) == "- current preference"


def test_rendering_is_bounded_and_relevance_ordered():
    records = [{"text": f"fact-{i}", "relevance": i} for i in range(10)]
    selected = select_recall(records, limit=3)
    assert [item.text for item in selected] == ["fact-9", "fact-8", "fact-7"]
    assert len(render_context(records, char_budget=15).splitlines()) == 1

def test_canonical_task_progress_source_requires_matching_query():
    records = [{
        "content": "checkpoint",
        "source": "canonical:task:progress",
        "task_id": "alpha-42",
    }]

    assert select_recall(records, query="unrelated question") == []
    assert [item.text for item in select_recall(records, query="resume alpha-42")] == ["checkpoint"]


def test_status_and_superseded_by_are_provider_boundary_guards():
    records = [
        {"content": "invalid", "status": "invalid"},
        {"content": "old", "superseded_by": "new-memory-id"},
        {"content": "current"},
    ]

    assert [item.text for item in select_recall(records)] == ["current"]

