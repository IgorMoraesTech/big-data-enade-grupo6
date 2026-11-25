from app.search import PUBLIC_FIELDS, cache_key, search_body, query_questions


def test_combined_filters_and_pagination():
    body = search_body("ética", 2023, "SI", "Tecnologia", "CE",
                       "objective", "competência", 2, 10)
    assert body["from"] == 10
    assert body["size"] == 10
    filters = body["query"]["bool"]["filter"]
    assert {"term": {"year": 2023}} in filters
    assert {"term": {"competencies": "competência"}} in filters


def test_public_search_excludes_answer():
    assert "answer" not in PUBLIC_FIELDS


def test_cache_key_stable():
    body = search_body("ética", None, None, None, None, None, None, 1, 10)
    assert cache_key(body) == cache_key(body)


class FakeElastic:
    def search(self, **kwargs):
        return {"hits": {"total": {"value": 1}, "hits": [{
            "_source": {"id": "abc", "statement": "Ética"},
            "highlight": {"statement": ["<mark>Ética</mark>"]},
        }]}}


def test_results_shape():
    body = search_body(None, None, None, None, None, None, None, 1, 10)
    result = query_questions(FakeElastic(), body, 1, 10)
    assert result["total"] == 1
    assert result["items"][0]["highlights"]["statement"] == ["<mark>Ética</mark>"]
