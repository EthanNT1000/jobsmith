from app.sources import source_104, source_yourator, source_cake


class FakeResp:
    def __init__(self, ok=True, status=200, json_data=None, text=""):
        self.ok = ok
        self.status_code = status
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


def test_source_104_parses(monkeypatch):
    payload = {"data": [{
        "jobName": "[[[AI]]]工程師", "custName": "未來智能", "jobAddrNoDesc": "台北",
        "salaryDesc": "面議", "descSnippet": "做 [[[Python]]] 開發",
        "link": {"job": "https://www.104.com.tw/job/abc"},
    }]}
    monkeypatch.setattr(source_104, "http_get", lambda *a, **k: FakeResp(json_data=payload))
    res = source_104.search("AI", limit=5)
    assert res.blocked is False
    assert len(res.jobs) == 1
    j = res.jobs[0]
    assert j.title == "AI工程師"          # [[[ ]]] 已清除
    assert j.company == "未來智能"
    assert j.url.endswith("/abc")
    assert "Python" in j.snippet and "[[[" not in j.snippet


def test_source_104_blocked_on_error(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("nope")
    monkeypatch.setattr(source_104, "http_get", boom)
    res = source_104.search("AI")
    assert res.blocked is True and res.jobs == []


def test_source_104_blocked_on_non_ok(monkeypatch):
    monkeypatch.setattr(source_104, "http_get", lambda *a, **k: FakeResp(ok=False, status=403))
    res = source_104.search("AI")
    assert res.blocked is True and res.error == "HTTP 403"


def test_source_yourator_parses(monkeypatch):
    payload = {"payload": {"jobs": [{
        "name": "AI 工程師", "location": "台北市", "salary": "NT$ 40,000",
        "path": "/companies/x/jobs/1", "tags": ["AI", "Python"],
        "company": {"brand": "某公司"},
    }]}}
    monkeypatch.setattr(source_yourator, "http_get", lambda *a, **k: FakeResp(json_data=payload))
    res = source_yourator.search("AI")
    assert len(res.jobs) == 1
    j = res.jobs[0]
    assert j.company == "某公司"
    assert j.url == "https://www.yourator.co/companies/x/jobs/1"
    assert "Python" in j.requirements


def test_source_cake_blocked_when_no_next_data(monkeypatch):
    monkeypatch.setattr(source_cake, "http_get", lambda *a, **k: FakeResp(text="<html>no data</html>"))
    res = source_cake.search("AI")
    assert res.blocked is True


def test_registry_search_all_aggregates(monkeypatch):
    from app.sources import registry
    from app.models import SearchResult
    monkeypatch.setattr(registry, "SEARCHABLE", {
        "104": lambda kw, limit=15: SearchResult(source="104"),
        "yourator": lambda kw, limit=15: SearchResult(source="yourator"),
    })
    results = registry.search_all("AI")
    assert [r.source for r in results] == ["104", "yourator"]


def test_linkedin_search_url():
    from app.sources.registry import linkedin_search_url
    url = linkedin_search_url("AI 工程師")
    assert url.startswith("https://www.linkedin.com/jobs/search/")
    assert "Taiwan" in url
