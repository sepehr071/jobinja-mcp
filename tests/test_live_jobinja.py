import pytest

pytestmark = [pytest.mark.live, pytest.mark.anyio]

COMPANY = "payampardaz"  # Payam Pardaz, a long-lived company page


async def test_live_search(client):
    r = (await client.call_tool("jj_search_jobs", {"keyword": "python"})).structured_content
    assert r["found"] > 20 and len(r["jobs"]) == 20 and r["pages"] > 1
    assert all("/" in j["id"] and j["title"] for j in r["jobs"])


async def test_live_search_filters(client):
    r = (await client.call_tool("jj_search_jobs", {"keyword": "python", "remote": True})).structured_content
    base = (await client.call_tool("jj_search_jobs", {"keyword": "python"})).structured_content
    assert 0 < r["found"] < base["found"]


async def test_live_search_single_filter_redirect(client):
    r = (await client.call_tool("jj_search_jobs", {"province": "تهران", "page": 2})).structured_content
    assert r["found"] > 1000 and len(r["jobs"]) == 20


async def test_live_job(client):
    s = (await client.call_tool("jj_search_jobs", {"keyword": "python"})).structured_content
    r = (await client.call_tool("jj_job", {"job": s["jobs"][0]["id"]})).structured_content
    assert r["title"] and r["description"] and r["salary"] and r["company_slug"]


async def test_live_salary_sorted(client):
    s = (
        await client.call_tool("jj_search_jobs", {"keyword": "python", "sort": "salary", "min_salary": 30})
    ).structured_content
    r = (await client.call_tool("jj_job", {"job": s["jobs"][0]["id"]})).structured_content
    assert r["salary_min_toman"] >= 30_000_000


async def test_live_company(client):
    r = (await client.call_tool("jj_company", {"slug": COMPANY})).structured_content
    assert r["name_en"] == "Payam Pardaz" and r["founded"] == 1375 and r["sections"]


async def test_live_company_jobs(client):
    r = (await client.call_tool("jj_company_jobs", {"slug": COMPANY})).structured_content
    assert r["count"] > 0 and not any(j.get("expired") for j in r["jobs"])
    old = (await client.call_tool("jj_company_jobs", {"slug": COMPANY, "expired_page": 1})).structured_content
    assert old["count"] > 0 and all(j["expired"] for j in old["jobs"])


async def test_live_search_companies(client):
    r = (await client.call_tool("jj_search_companies", {"keyword": "دیجی کالا"})).structured_content
    assert any(c["slug"] == "digikala" for c in r["companies"]), r
    r = (await client.call_tool("jj_search_companies", {"industry": "بیمه"})).structured_content
    assert len(r["companies"]) == 8


async def test_live_top_companies(client):
    r = (await client.call_tool("jj_top_companies", {})).structured_content
    assert len(r["companies"]) == 50 and r["companies"][0]["score"] >= r["companies"][-1]["score"]


async def test_live_city_and_benefits(client):
    r = (await client.call_tool("jj_search_jobs", {"city": "مشهد"})).structured_content
    assert r["found"] > 100 and r["jobs"][0]["city"].endswith("مشهد")
    r = (await client.call_tool("jj_search_jobs", {"keyword": "python", "benefits": ["usd"]})).structured_content
    assert r["found"] >= 0


async def test_live_market_and_skills(client):
    m = (await client.call_tool("jj_market", {"province": "اصفهان"})).structured_content
    assert len(m["categories"]) == 48 and m["provinces"][0]["name"] == "تهران" and m["cities"]
    r = (await client.call_tool("jj_skills", {"query": "python"})).structured_content
    assert r["skills"][0]["skill"] == "Python" and r["skills"][0]["ads_ever"] > 1000


async def test_live_salary_stats(client):
    r = (await client.call_tool("jj_salary_stats", {"keyword": "python", "sample": 4})).structured_content
    assert r["n_sampled"] == 4 and len(r["ads"]) == 4


async def test_live_company_jobs_limit(client):
    r = (
        await client.call_tool("jj_company_jobs", {"slug": COMPANY, "expired_page": 1, "limit": 100})
    ).structured_content
    assert len(r["jobs"]) > 30
