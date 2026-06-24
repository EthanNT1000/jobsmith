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


def test_source_104_salary_from_low_high(monkeypatch):
    # 真實 104 回傳：salaryDesc 不存在，數值在 salaryLow/salaryHigh + 型態碼 s10
    payload = {"data": [
        {"jobName": "月薪職", "custName": "A", "salaryLow": 48000, "salaryHigh": 70000,
         "s10": 50, "link": {"job": "https://x/1"}},
        {"jobName": "年薪職", "custName": "B", "salaryLow": 800000, "salaryHigh": 1300000,
         "s10": 60, "link": {"job": "https://x/2"}},
        {"jobName": "面議職", "custName": "C", "salaryLow": 0, "salaryHigh": 0,
         "s10": 10, "link": {"job": "https://x/3"}},
    ]}
    monkeypatch.setattr(source_104, "http_get", lambda *a, **k: FakeResp(json_data=payload))
    res = source_104.search("AI", limit=5)
    salaries = [j.salary for j in res.jobs]
    assert salaries[0] == "月薪 NT$48,000–70,000"
    assert salaries[1] == "年薪 NT$800,000–1,300,000"
    assert salaries[2] == "面議"


def test_source_104_ignores_legacy_salarydesc(monkeypatch):
    # 即使有舊的 salaryDesc 字串也不再採用，一律以 low/high 計算
    payload = {"data": [{"jobName": "x", "custName": "A", "salaryDesc": "舊字串",
                         "salaryLow": 40000, "salaryHigh": 50000, "s10": 50,
                         "link": {"job": "https://x/1"}}]}
    monkeypatch.setattr(source_104, "http_get", lambda *a, **k: FakeResp(json_data=payload))
    j = source_104.search("AI").jobs[0]
    assert j.salary == "月薪 NT$40,000–50,000"


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
