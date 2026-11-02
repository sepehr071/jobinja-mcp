"""Jobinja tools: job search and detail, company profile, company jobs, company search, top companies, filter lists."""

from __future__ import annotations

import asyncio
import json
import math
import re
import statistics
from typing import Annotated, Any, Literal

from bs4 import BeautifulSoup
from bs4.element import Tag
from pydantic import Field

from .http import SITE, ApiError, fetch
from .registry import tool

PER_PAGE = 20
FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
TOKEN = re.compile(r"^[A-Za-z0-9]{3,12}$")
JOB_URL = re.compile(r"/companies/([A-Za-z0-9][A-Za-z0-9_.-]*)/jobs/([A-Za-z0-9]{3,12})")
META_ORDER = ("construction", "place", "resume")
LOGIN_NOTE = "(برای مشاهده حقوق وارد شوید)"  # lists hide salaries from logged-out visitors

# Filter values of jobinja.ir/jobs, read from its search form on 2026-10-31.
PROVINCES = [
    "تهران", "خراسان رضوی", "اصفهان", "البرز", "فارس", "مازندران", "قم", "گیلان", "آذربایجان شرقی", "خوزستان",
    "یزد", "کرمان", "قزوین", "هرمزگان", "گلستان", "سیستان و بلوچستان", "سمنان", "بوشهر", "مرکزی",
    "آذربایجان غربی", "اردبیل", "همدان", "زنجان", "کرمانشاه", "چهارمحال بختیاری", "ایلام", "کردستان", "لرستان",
    "خراسان شمالی", "خراسان جنوبی", "کهکیلویه و بویراحمد",
]  # fmt: skip
CATEGORIES = [
    "فروش و بازاریابی", "وب،\u200c برنامه\u200cنویسی و نرم\u200cافزار", "مالی و حسابداری", "تولید و مدیریت محتوا",
    "مسئول دفتر، اجرائی و اداری", "دیجیتال مارکتینگ", "پشتیبانی و امور مشتریان", "IT / DevOps / Server", "طراحی",
    "آموزش", "حوزه\u200c سینما و تصویر", "کارگر ساده، نیروی خدماتی", "منابع انسانی و کارگزینی",
    "مهندسی صنایع و مدیریت صنعتی", "مهندسی برق و الکترونیک", "خرید و بازرگانی", "مدیر محصول",
    "مهندسی عمران و معماری", "انبارداری", "تکنسین فنی، تعمیرکار", "پزشکی،\u200c پرستاری و دارویی", "هتلداری",
    "تحقیق بازار و تحلیل اقتصادی", "گردشگری", "حمل و نقل", "مهندسی مکانیک و هوافضا", "تحقیق و توسعه",
    "مدیریت بیمه", "کارگر ماهر، کارگر صنعتی", "کارشناس حقوقی،\u200c وکالت", "راننده، پیک موتوری", "صنایع غذایی",
    "نگهبان", "روابط عمومی", "HSE", "مهندسی نساجی، طراحی پارچه و لباس", "مهندسی شیمی و نفت", "ترجمه",
    "علوم زیستی و آزمایشگاهی", "مهندسی معدن و متالورژی", "مهندسی پزشکی", "حوزه\u200c موسیقی و صدا", "CEO",
    "شیمی، داروسازی", "تربیت بدنی", "مهندسی کشاورزی", "خبر\u200cنگاری", "مهندسی پلیمر",
]  # fmt: skip
SALARY_STEPS_MILLION = [10.3, 11, 15, 20, 30, 40, 50, 70, 100, 150, 200, 300, 400, 500]
INDUSTRIES = {  # name -> /company/list/<slug>
    "کامپیوتر، فناوری اطلاعات و اینترنت": "کامپیوتر-فناوری-اطلاعات-و-اینترنت",
    "تولید و صنایع": "تولید-و-صنایع",
    "تبلیغات، بازاریابی و برندسازی": "تبلیغات-بازاریابی-و-برندسازی",
    "خدمات درمانی، پزشکی و سلامت": "خدمات-درمانی-پزشکی-و-سلامت",
    "معماری و عمران": "معماری-و-عمران",
    "آموزش، مدارس و دانشگاه\u200cها": "آموزش-مدارس-و-دانشگاه-ها",
    "رسانه و انتشارات": "رسانه-و-انتشارات",
    "گردشگری و هتل\u200cها": "گردشگری-و-هتل-ها",
    "نفت و گاز": "نفت-و-گاز",
    "مالی و اعتباری": "مالی-و-اعتباری",
    "مخابرات و ارتباطات (تلکام)": "مخابرات-و-ارتباطات-تلکام",
    "املاک و مستغلات": "املاک-و-مستغلات",
    "بیمه": "بیمه",
    "منابع انسانی": "منابع-انسانی",
    "نیرو": "نیرو",
    "وکالت و حقوقی": "وکالت-و-حقوقی",
    "دولتی": "دولتی",
}
BENEFITS = {  # tool name -> filters[has_*]
    "usd": "has_usd", "military_placement": "has_military_placement", "loan": "has_loan", "project": "has_project",
    "bonus": "has_bonus", "commission": "has_commission", "overtime": "has_overtime_offering",
    "afternoon_shift": "has_afternoon_shift", "promotion": "has_promotion", "part_time": "has_part_time",
    "disability_support": "has_disability_support", "flexible_hours": "has_flexible_hours",
    "supplementary_insurance": "has_supplementary_insurance", "esop": "has_esop", "business_trip": "has_business_trip",
}  # fmt: skip
EXPERIENCE = {"any": "any", "under_2": "under_two", "3_6": "3_6", "7_plus": "7_plus"}
SORT = {"relevance": "relevance_desc", "newest": "published_at_desc", "salary": "salary_from_desc"}

Page = Annotated[int, Field(description="Page number, 1-based.", ge=1, le=500)]
Slug = Annotated[
    str,
    Field(description="Company slug from a Jobinja company or job URL, e.g. payampardaz.", pattern=SLUG.pattern),
]


def _num(s: str) -> str:
    return s.translate(FA_DIGITS)


def _t(e: Tag | None) -> str:
    """Whitespace-collapsed text of a tag, '' if missing."""
    return re.sub(r"\s+", " ", e.get_text(" ")).strip() if e else ""


def _norm(s: str) -> str:
    """Comparison key for Persian names: no spaces, ZWNJ or commas, Arabic letters folded."""
    return re.sub(r"[\s\u200c،,]", "", s).replace("ي", "ی").replace("ك", "ک").lower()


def _pick(value: str, options: list[str], what: str) -> str:
    """The option that equals `value` (ignoring spaces/ZWNJ) or is the only one containing it."""
    key = _norm(value)
    hits = [o for o in options if _norm(o) == key] or [o for o in options if key and key in _norm(o)]
    if len(hits) != 1:
        raise ApiError(f"Unknown {what} {value!r}. Valid values: {', '.join(options)}. (jj_filters lists them.)")
    return hits[0]


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _int(s: str) -> int | None:
    m = re.search(r"\d[\d,]*", _num(s))
    return int(m.group().replace(",", "")) if m else None


def _name(s: str) -> dict[str, str]:
    """Jobinja company names read 'فارسی | English'."""
    fa, _, en = s.partition("|")
    return {"name": fa.strip(), **({"name_en": en.strip()} if en.strip() else {})}


def _job_id(url: str) -> str | None:
    m = JOB_URL.search(url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def _job_url(jid: str) -> str:
    slug, token = jid.split("/")
    return f"{SITE}/companies/{slug}/jobs/{token}"


def _cards(root: Tag | BeautifulSoup) -> list[dict[str, Any]]:
    """Job cards (`li.c-jobListView__item`) as compact dicts."""
    out = []
    for li in root.select("li.c-jobListView__item"):
        a = li.select_one("a.c-jobListView__titleLink")
        jid = _job_id(a["href"]) if a else None
        if not a or not jid:
            continue
        meta = {}
        for i, m in enumerate(li.select(".c-jobListView__metaItem")):
            classes = m.select_one("i").get("class", []) if m.select_one("i") else []
            icon = next((c[8:] for c in classes if c.startswith("c-icon--") and c[8:9].isalpha()), "")
            # fallback if the icon classes change: the site always lists company, place, contract in that order
            meta[icon or (META_ORDER[i] if i < 3 else f"x{i}")] = _t(m).replace(LOGIN_NOTE, "").strip()
        days = _t(li.select_one(".c-jobListView__passedDays")).strip("() ")
        title = _t(a)
        gone = title.endswith("(منقضی شده)") or days == "منقضی شده"  # company pages mark expired ads in the age slot
        out.append(
            {
                "id": jid,
                "title": title.removesuffix("(منقضی شده)").strip(),
                "company": meta.get("construction"),
                "city": meta.get("place"),
                "contract": meta.get("resume"),
                "posted": None if gone else _num(days) or None,
                "promoted": "c-jobListView__item--premium" in li.get("class", []) or None,
                "expired": gone or None,
                "url": _job_url(jid),
            }
        )
    return out


def _company_cards(soup: BeautifulSoup) -> list[dict[str, Any]]:
    out = []
    for a in soup.select("a.c-companyOverview"):
        m = re.search(r"/companies/([^/?#]+)", a.get("href", ""))
        if not m:
            continue
        tags = a.select(".c-companyOverview__tags span")
        plain = [_t(x) for x in tags if "green" not in x.get("class", [])]
        out.append(
            {
                "slug": m.group(1),
                **_name(_t(a.select_one(".c-companyOverview__title"))),
                "city": plain[0] if plain else None,
                "industry": plain[1] if len(plain) > 1 else None,
                "hiring": any("green" in x.get("class", []) for x in tags) or None,
            }
        )
    return out


def _text(html: str, limit: int) -> str:
    """Plain text of an HTML snippet, one line per block, clipped."""
    soup = _soup(html)
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for blk in soup.find_all(["p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6"]):
        blk.insert(0, "\n- " if blk.name == "li" else "\n")
        blk.append("\n")
    s = "\n".join(x for x in (re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in soup.get_text().splitlines()) if x)
    return s if len(s) <= limit else s[:limit].rstrip() + " ... [clipped]"


def _search_params(
    keyword,
    province,
    category,
    remote,
    job_type,
    internship,
    experience,
    min_salary,
    sort,
    page,
    city=None,
    benefits=(),
) -> list[tuple[str, str]]:
    p: list[tuple[str, str]] = []
    if keyword and keyword.strip():
        p.append(("filters[keywords][]", keyword.strip()))
    if province:
        p.append(("filters[locations][]", _pick(province, PROVINCES, "province")))
    if city and city.strip():
        p.append(("filters[locations][]", city.strip()))
    if category:
        p.append(("filters[job_categories][]", _pick(category, CATEGORIES, "category")))
    if job_type:
        p.append(("filters[job_types][]", {"fulltime": "is_fulltime", "parttime": "is_parttime"}[job_type]))
    if remote:
        p.append(("filters[remote]", "1"))
    if internship:
        p.append(("filters[internship]", "1"))
    if experience:
        p.append(("filters[w_e][]", EXPERIENCE[experience]))
    if min_salary:
        step = max((s for s in SALARY_STEPS_MILLION if s <= min_salary), default=SALARY_STEPS_MILLION[0])
        p.append(("filters[sal_min][]", f"{round(step * 1_000_000)}:"))
    p.extend((f"filters[{BENEFITS[b]}]", "1") for b in benefits)
    if sort != "relevance":
        p.append(("sort_by", SORT[sort]))
    if page > 1:
        p.append(("page", str(page)))
    return p


@tool("Search jobs")
async def jj_search_jobs(
    keyword: Annotated[
        str | None,
        Field(description="Words in the title or text, Persian or English (python, حسابدار, react).", max_length=100),
    ] = None,
    province: Annotated[str | None, Field(description="Province name, e.g. تهران, اصفهان (see jj_filters).")] = None,
    category: Annotated[
        str | None,
        Field(
            description="Job category, e.g. 'وب، برنامه\u200cنویسی و نرم\u200cافزار' or just 'برنامه\u200cنویسی' (see jj_filters)."
        ),
    ] = None,
    remote: Annotated[bool, Field(description="Only remote (دورکاری) jobs.")] = False,
    city: Annotated[
        str | None, Field(description="City name, e.g. مشهد, کرج (jj_market lists cities with ad counts).")
    ] = None,
    benefits: Annotated[
        list[Literal[tuple(BENEFITS)]] | None,  # type: ignore[valid-type]
        Field(description="Only ads offering all of these benefits, e.g. ['loan', 'flexible_hours', 'esop']."),
    ] = None,
    job_type: Annotated[Literal["fulltime", "parttime"] | None, Field(description="Contract type.")] = None,
    internship: Annotated[bool, Field(description="Only internships (کارآموزی).")] = False,
    experience: Annotated[
        Literal["any", "under_2", "3_6", "7_plus"] | None,
        Field(description="Required work experience in years: any, under 2, 3 to 6, 7 or more."),
    ] = None,
    min_salary: Annotated[
        float | None,
        Field(
            description="Minimum monthly salary in million Toman; rounded down to Jobinja's steps (10.3, 11, 15, 20, 30, 40, 50, 70, 100, 150, 200, 300, 400, 500).",
            gt=0,
        ),
    ] = None,
    sort: Annotated[
        Literal["relevance", "newest", "salary"],
        Field(description="Order: relevance (default), newest, or highest salary."),
    ] = "relevance",
    page: Page = 1,
) -> dict[str, Any]:
    """Search Jobinja job ads by keyword, province, city, category, remote, contract type, experience, benefits and minimum salary.

    Use for "find python jobs in Isfahan" or "remote jobs paying 50 million". Returns 20 ads per page with an id
    (company/token), company, city, contract type and age. Jobinja hides salaries in lists; call jj_job with an id
    for the salary, skills and full description. Filters combine with AND.
    """
    params = _search_params(
        keyword,
        province,
        category,
        remote,
        job_type,
        internship,
        experience,
        min_salary,
        sort,
        page,
        city,
        benefits or (),
    )
    url, html = await fetch("/jobs", params)
    soup = _soup(html)
    found = _int(_t(soup.select_one(".c-jobSearchState__numberOfResultsEcho"))) or 0
    jobs = _cards(soup)
    return {
        "found": found,
        "page": page,
        "pages": math.ceil(found / PER_PAGE),
        "jobs": jobs,
        "next": "Raise page for more, narrow with filters, or call jj_job with an id."
        if jobs
        else "No ads on this page (check the city spelling with jj_market, or loosen the filters).",
    }


def _salary(text: str) -> dict[str, Any]:
    """Salary box text -> {salary, min/max Toman per month}; 'توافقی' means negotiable."""
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", _num(text))]
    out: dict[str, Any] = {"salary": text or None}
    if nums and "تومان" in text:
        out["salary_min_toman"] = nums[0]
        if len(nums) > 1:
            out["salary_max_toman"] = nums[1]
    elif "توافقی" in text:
        out["salary_negotiable"] = True
    return out


def _job(soup: BeautifulSoup, jid: str) -> dict[str, Any]:
    ld: dict[str, Any] = {}
    tag = soup.find("script", type="application/ld+json")
    if tag and tag.string:
        try:
            ld = json.loads(tag.string)
        except ValueError:
            pass
    info: dict[str, Any] = {}
    for li in soup.select("ul.c-infoBox li.c-infoBox__item"):
        k = _t(li.select_one(".c-infoBox__itemTitle"))
        tags = [_t(s) for s in li.select(".tags span")]
        v = _t(li).removeprefix(k).strip()
        info[k] = tags if k == "مهارت\u200cهای مورد نیاز" else v
    org = ld.get("hiringOrganization") or {}
    title = ld.get("title") or _t(soup.select_one(".c-jobView__titleText")).removeprefix("استخدام ").strip()
    return {
        "id": jid,
        "url": _job_url(jid),
        "title": title,
        "expired": "این آگهی منقضی شده است" in _t(soup) or None,
        "company": _t(soup.select_one(".c-companyHeader__name")) or org.get("name"),
        "company_slug": jid.split("/")[0],
        "company_website": org.get("sameAs"),
        "posted": ld.get("datePosted"),
        "category": info.get("دسته\u200cبندی شغلی"),
        "location": info.get("موقعیت مکانی"),
        "contract": info.get("نوع همکاری"),
        "experience": info.get("حداقل سابقه کار"),
        **_salary(info.get("حقوق", "")),
        "skills": info.get("مهارت\u200cهای مورد نیاز"),
        "gender": info.get("جنسیت"),
        "military": info.get("وضعیت نظام وظیفه"),
        "degree": info.get("حداقل مدرک تحصیلی"),
        "description": _text(ld.get("description", ""), 6000) or None,
    }


def _parse_job_id(job: str) -> str:
    """'company/token' or any Jobinja job URL -> 'company/token'."""
    s = job.strip()
    if jid := _job_id(s):
        return jid
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9]{3,12}", s):
        return s
    raise ApiError("Pass a job id like 'payampardaz/tuAE' (from jj_search_jobs) or a Jobinja job URL.")


@tool("Job details")
async def jj_job(
    job: Annotated[
        str,
        Field(
            description="Job id 'company-slug/token' from jj_search_jobs or jj_company_jobs, e.g. payampardaz/tuAE, or the job page URL.",
            max_length=400,
        ),
    ],
) -> dict[str, Any]:
    """Read one Jobinja job ad: title, company, salary, contract, experience, skills, degree, gender, military status and the full description.

    Use after jj_search_jobs or jj_company_jobs. The salary is the monthly figure in Toman shown on the ad page
    (minimum, or negotiable). Check `expired` before recommending it. Call jj_company with company_slug for the employer.
    """
    jid = _parse_job_id(job)
    _, html = await fetch(f"/companies/{jid.split('/')[0]}/jobs/{jid.split('/')[1]}")
    soup = _soup(html)
    out = _job(soup, jid)
    out["similar"] = _cards(soup)[:6]
    return out


@tool("Company profile")
async def jj_company(slug: Slug) -> dict[str, Any]:
    """Read a company's Jobinja profile: name, founding year, industry, size, website, open job count and its intro, culture and benefits text.

    Use after a job or company search. Jobinja has no employee reviews or ratings (only the top-50 score, see
    jj_top_companies). Call jj_company_jobs for the open ads.
    """
    (_, main), (_, about) = await asyncio.gather(fetch(f"/companies/{slug}"), fetch(f"/companies/{slug}/about"))
    head = _soup(main).select_one(".c-companyHeader")
    out: dict[str, Any] = {
        "slug": slug,
        "url": f"{SITE}/companies/{slug}",
        **_name(_t(head.select_one(".c-companyHeader__name")) if head else ""),
    }
    for m in head.select(".c-companyHeader__metaItem") if head else []:
        s = _t(m)
        link = m.select_one("a[href^=http]")
        if s.startswith("تاسیس"):
            out["founded"] = _int(s)
        elif "نفر" in s:
            out["size"] = _num(s)
        elif link and "jobinja.ir" not in link["href"]:
            out["website"] = s
        else:
            out["industry"] = s
    out["open_jobs"] = _int(_t(head.select_one(".c-companyHeader__navigatorOpenJobs"))) if head else None
    out["sections"] = [
        {
            "title": _t(sec.select_one(".c-cardText__title")),
            "text": _text(str(sec.select_one(".c-cardText__body")), 1500),
        }
        for sec in _soup(about).select("section.c-cardText")
    ]
    return out


@tool("Company open jobs")
async def jj_company_jobs(
    slug: Slug,
    expired_page: Annotated[
        int | None,
        Field(description="Set to read that page of the company's expired ads instead of the open ones.", ge=1, le=100),
    ] = None,
    limit: Annotated[int, Field(description="Most rows to return (expired pages hold up to 100).", ge=1, le=100)] = 30,
) -> dict[str, Any]:
    """List a company's open job ads on Jobinja (or, with expired_page, its past ads, which show its hiring history).

    Use to see what a company is hiring for. Each row has an id for jj_job. Expired pages hold 100 ads each.
    """
    url, html = await fetch(
        f"/companies/{slug}/jobs", [("expired_jobs_page", str(expired_page))] if expired_page else None
    )
    soup = _soup(html)
    expired = soup.select_one("#expired_jobs")
    if expired_page:
        jobs = _cards(expired) if expired else []
    else:
        if expired:
            expired.extract()
        jobs = _cards(soup)
    return {"slug": slug, "expired": bool(expired_page), "count": len(jobs), "jobs": jobs[:limit]}


@tool("Search companies")
async def jj_search_companies(
    keyword: Annotated[
        str | None, Field(description="Company name words, e.g. دیجی\u200cکالا or snapp.", max_length=100)
    ] = None,
    industry: Annotated[
        str | None, Field(description="Industry name instead of a keyword, e.g. 'بیمه' or 'کامپیوتر' (see jj_filters).")
    ] = None,
    page: Page = 1,
) -> dict[str, Any]:
    """Find companies on Jobinja by name, or browse one industry (8 per page).

    Use to get the slug for jj_company / jj_company_jobs. Give keyword or industry (industry wins).
    """
    if industry:
        name = _pick(industry, list(INDUSTRIES), "industry")
        path, params = f"/company/list/{INDUSTRIES[name]}", [("page", str(page))] if page > 1 else []
    else:
        path = "/companies"
        params = ([("keyword", keyword.strip())] if keyword and keyword.strip() else []) + (
            [("page", str(page))] if page > 1 else []
        )
    _, html = await fetch(path, params)
    companies = _company_cards(_soup(html))
    return {
        "page": page,
        "companies": companies,
        "next": "Raise page for more." if len(companies) >= 8 else "Last page.",
    }


@tool("Top 50 companies")
async def jj_top_companies(
    limit: Annotated[int, Field(description="How many of the 50.", ge=1, le=50)] = 50,
) -> dict[str, Any]:
    """Jobinja's yearly list of the 50 best companies to work for, with each one's score out of 10 and its three sub-scores.

    This is the only company rating data on Jobinja. Sub-scores: popularity among job seekers, variety of job
    openings, handling of received resumes. Use the slug with jj_company.
    """
    _, html = await fetch("/top50")
    out = []
    for li in _soup(html).select("li.c-topCompanies__each")[:limit]:
        a = li.select_one("a.c-topCompanies__goToCompany")
        metas = [_t(x) for x in li.select(".c-topCompanies__metasItem")]
        subs = {
            _t(p).removeprefix(_t(p.select_one("i"))).strip(): _int(_t(p.select_one("i")))
            for p in li.select(".c-topCompanies__parameter")
        }
        score = _num(_t(li.select_one(".c-topCompanies__rate"))).replace("/", ".")
        out.append(
            {
                "rank": _int(_t(li.select_one(".c-topCompanies__counter"))),
                **_name(_t(li.select_one(".c-topCompanies__name"))),
                "slug": (a["href"].rstrip("/").rsplit("/", 1)[-1]) if a else None,
                "score": float(re.search(r"[\d.]+", score).group()) if re.search(r"\d", score) else None,
                "industry": metas[0] if metas else None,
                "size": _num(metas[1]) if len(metas) > 1 else None,
                "open_jobs": _int(metas[2]) if len(metas) > 2 else None,
                "sub_scores": subs,
            }
        )
    return {"companies": out}


async def _api(path: str, params: list[tuple[str, str]] | None = None) -> Any:
    """Jobinja's public JSON API (/api/v10/...), parsed."""
    _, body = await fetch(path, params, json=True)
    try:
        return json.loads(body)
    except ValueError as e:
        raise ApiError("Jobinja returned an unexpected (non-JSON) answer; try again later.") from e


def _counts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(({"name": r["name"], "ads": r["job_count"]} for r in rows), key=lambda x: -x["ads"])


@tool("Job market counts")
async def jj_market(
    province: Annotated[
        str | None, Field(description="Province name to also list its cities with ad counts, e.g. اصفهان.")
    ] = None,
) -> dict[str, Any]:
    """Count the open Jobinja ads right now per job category, province, company industry and top skill (live site statistics).

    Use for market-size questions ("how many programming jobs are open", "which province hires most"), or with
    province to get exact city names and their ad counts for the city filter of jj_search_jobs.
    """
    d = (await _api("/api/v10/job_search_meta")).get("data", {})
    out: dict[str, Any] = {
        "categories": _counts(d.get("job_categories", [])),
        "provinces": _counts(d.get("locations", [])),
        "industries": _counts(d.get("company_categories", [])),
        "top_skills": _counts(d.get("skills", [])),
    }
    if province:
        name = _pick(province, PROVINCES, "province")
        loc = next((x for x in d.get("locations", []) if _norm(x["name"]) == _norm(name)), None)
        out["cities"] = _counts(loc["cities"]) if loc else []
        out["cities"] = [c for c in out["cities"] if c["ads"]]
    return out


@tool("Skill demand")
async def jj_skills(
    query: Annotated[str, Field(description="Skill words, e.g. react, python, حسابداری.", min_length=1, max_length=60)],
) -> dict[str, Any]:
    """Find skills on Jobinja matching a word, with how many ads ever listed each (a demand signal).

    Use to compare skills ("react vs vue") or to pick the exact skill spelling. The counts cover all ads on the
    site including expired ones, so they rank skills but are not today's openings; use jj_search_jobs for those.
    """
    rows = await _api("/api/v10/job-skills/search", [("q", query.strip())])
    seen: dict[str, int] = {}
    for x in rows if isinstance(rows, list) else []:
        n = (x.get("name") or "").strip()
        seen[n] = seen.get(n, 0) + (x.get("total") or 0)
    skills = [{"skill": k, "ads_ever": v} for k, v in sorted(seen.items(), key=lambda kv: -kv[1]) if k]
    return {"query": query, "skills": skills[:15]}


@tool("Salary statistics")
async def jj_salary_stats(
    keyword: Annotated[
        str | None, Field(description="Words in the title or text, e.g. python.", max_length=100)
    ] = None,
    province: Annotated[str | None, Field(description="Province name (see jj_filters).")] = None,
    category: Annotated[str | None, Field(description="Job category (see jj_filters).")] = None,
    remote: Annotated[bool, Field(description="Only remote jobs.")] = False,
    experience: Annotated[Literal["any", "under_2", "3_6", "7_plus"] | None, Field(description="Experience.")] = None,
    sample: Annotated[int, Field(description="How many ads to read (each is one request).", ge=3, le=30)] = 12,
) -> dict[str, Any]:
    """Estimate monthly salaries (Toman) for a kind of job by reading the ad pages of the top search results.

    Use for "what does a python developer earn" questions. Lists hide salaries, so this opens `sample` ads from the
    first page of results and summarises the stated minimums; most ads say negotiable, so check n_with_salary.
    A sample, not a survey: say so when reporting. The ads are returned so you can cite them with jj_job.
    Makes one request per sampled ad, at most 30 (`sample`).
    """
    params = _search_params(keyword, province, category, remote, None, False, experience, None, "relevance", 1)
    _, html = await fetch("/jobs", params)
    cards = _cards(_soup(html))[:sample]
    pages = await asyncio.gather(*(fetch(_job_url(c["id"]).removeprefix(SITE)) for c in cards))
    ads = [
        {k: v for k, v in _job(_soup(h), c["id"]).items() if k in _SAL_KEYS}
        for c, (_, h) in zip(cards, pages, strict=True)
    ]
    mins = [a["salary_min_toman"] for a in ads if "salary_min_toman" in a]
    out: dict[str, Any] = {
        "n_sampled": len(ads),
        "n_with_salary": len(mins),
        "n_negotiable": sum(1 for a in ads if a.get("salary_negotiable")),
    }
    if mins:
        out.update(min=min(mins), median=int(statistics.median(mins)), max=max(mins), mean=int(statistics.mean(mins)))
    out["ads"] = ads
    return out


_SAL_KEYS = {"id", "title", "company", "salary", "salary_min_toman", "salary_max_toman", "salary_negotiable"}


@tool("Search filter values")
async def jj_filters() -> dict[str, Any]:
    """List every value the Jobinja search accepts: provinces, job categories, industries, experience levels, salary steps, sort orders.

    Use when a province, category or industry name is rejected or you need the exact spelling.
    """
    return {
        "provinces": PROVINCES,
        "categories": CATEGORIES,
        "industries": list(INDUSTRIES),
        "experience": list(EXPERIENCE),
        "min_salary_million_toman": SALARY_STEPS_MILLION,
        "sort": list(SORT),
        "job_type": ["fulltime", "parttime"],
    }
