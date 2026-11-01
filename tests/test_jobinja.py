import httpx
import pytest
from conftest import page

from jobinja_mcp import http, jobs

pytestmark = pytest.mark.anyio


async def test_search_params_and_cards(client, site):
    site["/jobs"] = "search.html"
    r = (
        await client.call_tool(
            "jj_search_jobs",
            {
                "keyword": "python",
                "province": "اصفهان",
                "category": "برنامه\u200cنویسی",
                "min_salary": 35,
                "sort": "newest",
                "page": 2,
            },
        )
    ).structured_content
    q = site.calls[0].url.params.multi_items()
    assert ("filters[keywords][]", "python") in q and ("filters[locations][]", "اصفهان") in q
    assert ("filters[job_categories][]", "وب،\u200c برنامه\u200cنویسی و نرم\u200cافزار") in q
    assert ("filters[sal_min][]", "30000000:") in q and ("sort_by", "published_at_desc") in q and ("page", "2") in q
    assert r["found"] == 327 and r["pages"] == 17 and len(r["jobs"]) == 3
    first = r["jobs"][0]
    assert first["id"] == "izad-takvin-houshmand-ariana/turn" and first["url"].endswith("/jobs/turn")
    assert first["company"] and first["city"] and first["posted"] == "20 روز پیش" and first["promoted"] is True
    assert "برای مشاهده حقوق" not in first["contract"]


async def test_search_follows_seo_redirect_and_keeps_page(client, site):
    site["/jobs"] = lambda req: httpx.Response(301, headers={"location": "/jobs/tehran-seo"})
    site["/jobs/tehran-seo"] = "search.html"
    await client.call_tool("jj_search_jobs", {"province": "تهران", "page": 3})
    assert site.calls[1].url.path == "/jobs/tehran-seo" and site.calls[1].url.params["page"] == "3"


async def test_unknown_province_lists_options(client, site):
    r = await client.call_tool("jj_search_jobs", {"province": "پاریس"})
    assert r.is_error and "تهران" in r.content[0].text


async def test_job_detail(client, site):
    site["/companies/payampardaz/jobs/tuAE"] = "job.html"
    r = (
        await client.call_tool("jj_job", {"job": "https://jobinja.ir/companies/payampardaz/jobs/tuAE/x-y?_ref=1"})
    ).structured_content
    assert r["id"] == "payampardaz/tuAE" and r["company_slug"] == "payampardaz"
    assert r["salary_negotiable"] is True and "salary_min_toman" not in r  # ld+json baseSalary is a placeholder
    assert r["skills"] == ["Python", "Linux", "SQL"] and r["degree"] == "کارشناسی"
    assert r["posted"] == "2026-10-24" and "Senior Python Developer" in r["description"] and "\n" in r["description"]
    assert r["similar"] and "expired" not in r


async def test_job_expired_and_salary_number(client, site):
    site["/companies/payampardaz/jobs/CCTw"] = "job_expired.html"
    r = (await client.call_tool("jj_job", {"job": "payampardaz/CCTw"})).structured_content
    assert r["expired"] is True


def test_salary_parse():
    assert jobs._salary("از ۵۰۰,۰۰۰,۰۰۰ تومان") == {"salary": "از ۵۰۰,۰۰۰,۰۰۰ تومان", "salary_min_toman": 500_000_000}
    assert jobs._salary("۱۵,۰۰۰,۰۰۰ تا ۲۰,۰۰۰,۰۰۰ تومان")["salary_max_toman"] == 20_000_000
    assert jobs._salary("توافقی")["salary_negotiable"] is True


async def test_job_bad_id(client, site):
    r = await client.call_tool("jj_job", {"job": "not a job"})
    assert r.is_error and "payampardaz/tuAE" in r.content[0].text


async def test_company(client, site):
    site["/companies/payampardaz"] = "company.html"
    site["/companies/payampardaz/about"] = "company_about.html"
    r = (await client.call_tool("jj_company", {"slug": "payampardaz"})).structured_content
    assert r["name_en"] == "Payam Pardaz" and r["founded"] == 1375 and r["size"] == "51 تا 200 نفر"
    assert r["website"] == "payampardaz.com/" and r["open_jobs"] == 12 and "فناوری" in r["industry"]
    assert r["sections"][0]["title"].startswith("معرفی") and len(r["sections"]) == 2


async def test_company_jobs_open_and_expired(client, site):
    site["/companies/payampardaz/jobs"] = "company_jobs.html"
    r = (await client.call_tool("jj_company_jobs", {"slug": "payampardaz"})).structured_content
    assert r["count"] == 2 and not any(j.get("expired") for j in r["jobs"])
    r = (await client.call_tool("jj_company_jobs", {"slug": "payampardaz", "expired_page": 1})).structured_content
    assert r["count"] == 2 and all(j["expired"] for j in r["jobs"]) and "posted" not in r["jobs"][0]
    assert site.calls[1].url.params["expired_jobs_page"] == "1"


async def test_search_companies(client, site):
    site["/companies"] = "companies.html"
    r = (await client.call_tool("jj_search_companies", {"keyword": "دیجی"})).structured_content
    assert site.calls[0].url.params["keyword"] == "دیجی"
    assert r["companies"][0]["slug"] == "digikala" and r["companies"][0]["hiring"] is True
    site["/company/list/بیمه"] = "companies.html"
    r = (await client.call_tool("jj_search_companies", {"industry": "بیمه", "page": 2})).structured_content
    assert len(r["companies"]) == 3


async def test_top_companies(client, site):
    site["/top50"] = "top50.html"
    r = (await client.call_tool("jj_top_companies", {"limit": 2})).structured_content
    first = r["companies"][0]
    assert len(r["companies"]) == 2 and first["rank"] == 1 and first["score"] == 9.8 and first["slug"] == "rirais"
    assert first["open_jobs"] == 37 and first["sub_scores"]["محبوبیت میان کارجویان"] == 10


async def test_filters(client):
    r = (await client.call_tool("jj_filters", {})).structured_content
    assert "تهران" in r["provinces"] and len(r["categories"]) == 48 and len(r["industries"]) == 17


async def test_404_and_403_messages(client, site):
    r = await client.call_tool("jj_company", {"slug": "nope"})
    assert r.is_error and "404" in r.content[0].text
    site["/top50"] = lambda req: httpx.Response(403, text="Access Denied")
    r = await client.call_tool("jj_top_companies", {})
    assert r.is_error and "Iranian" in r.content[0].text


async def test_host_allowlist(site):
    with pytest.raises(http.ApiError, match="unexpected host"):
        await http.fetch("https://evil.example/jobs")


async def test_tools_listed_with_read_only(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {
        "jj_search_jobs", "jj_job", "jj_company", "jj_company_jobs", "jj_search_companies", "jj_top_companies", "jj_filters",
        "jj_market", "jj_skills", "jj_salary_stats",
    }  # fmt: skip
    assert all(t.annotations.read_only_hint for t in tools.values())


async def test_search_city_and_benefits(client, site):
    site["/jobs"] = "search.html"
    await client.call_tool("jj_search_jobs", {"city": "مشهد", "benefits": ["loan", "overtime"]})
    q = site.calls[0].url.params.multi_items()
    assert ("filters[locations][]", "مشهد") in q and ("filters[has_loan]", "1") in q
    assert ("filters[has_overtime_offering]", "1") in q


def test_cards_survive_missing_icons():
    html = page("search.html").replace("c-icon--construction", "x").replace("c-icon--place", "y")
    first = jobs._cards(jobs._soup(html))[0]
    assert first["company"] and first["city"]


async def test_company_jobs_limit(client, site):
    site["/companies/payampardaz/jobs"] = "company_jobs.html"
    r = (await client.call_tool("jj_company_jobs", {"slug": "payampardaz", "limit": 1})).structured_content
    assert r["count"] == 2 and len(r["jobs"]) == 1


async def test_market(client, site):
    site["/api/v10/job_search_meta"] = "job_search_meta.json"
    r = (await client.call_tool("jj_market", {"province": "تهران"})).structured_content
    assert site.calls[0].headers["accept"].startswith("application/json")
    assert r["categories"][0]["ads"] >= r["categories"][-1]["ads"] and r["provinces"][0]["name"]
    assert r["cities"] and all(c["ads"] for c in r["cities"]) and "top_skills" in r


async def test_request_headers(client, site):
    site["/api/v10/job-skills/search"] = "skills.json"
    site["/top50"] = "top50.html"
    await client.call_tool("jj_skills", {"query": "react"})
    await client.call_tool("jj_top_companies", {})
    api, doc = (c.headers for c in site.calls[:2])
    assert api["accept"].startswith("application/json, text/javascript") and api["x-requested-with"] == "XMLHttpRequest"
    assert api["referer"] == "https://jobinja.ir/jobs" and api["sec-fetch-site"] == "same-origin"
    assert api["sec-fetch-mode"] == "cors" and "origin" not in api and "sec-fetch-user" not in api
    assert (
        doc["referer"] == "https://jobinja.ir/"
        and doc["sec-fetch-mode"] == "navigate"
        and doc["sec-fetch-user"] == "?1"
    )
    assert doc["accept"].startswith("text/html")


async def test_skills(client, site):
    site["/api/v10/job-skills/search"] = "skills.json"
    r = (await client.call_tool("jj_skills", {"query": "react"})).structured_content
    assert site.calls[0].url.params["q"] == "react"
    assert r["skills"][0] == {"skill": "React", "ads_ever": 10001} and len(r["skills"]) == 5


async def test_salary_stats(client, site):
    site["/jobs"] = "search.html"
    for c in jobs._cards(jobs._soup(page("search.html"))):
        slug, token = c["id"].split("/")
        site[f"/companies/{slug}/jobs/{token}"] = "job_expired.html"
    r = (await client.call_tool("jj_salary_stats", {"keyword": "python", "sample": 3})).structured_content
    assert r["n_sampled"] == 3 and r["n_with_salary"] + r["n_negotiable"] <= 3 and len(r["ads"]) == 3
