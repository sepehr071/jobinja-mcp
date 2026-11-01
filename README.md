<!-- mcp-name: io.github.sepehr071/jobinja-mcp -->

<div align="center">

# jobinja-mcp: Jobinja (جابینجا) Iran job search MCP server for AI agents

**jobinja-mcp is an unofficial, read-only MCP server that gives AI agents the job ads and company pages of Jobinja (جابینجا, jobinja.ir), the Iranian job portal.**<br>
Its 7 tools search ads by keyword, province, category, remote, contract type, experience and minimum salary, read a full ad with its salary and skills,<br>
look up companies and their open ads, and read Jobinja's top-50 company scores.
No API key or Jobinja account is needed. It works in Claude, Cursor, Copilot and any other MCP client.

[![PyPI](https://img.shields.io/pypi/v/jobinja-mcp?color=2563eb)](https://pypi.org/project/jobinja-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/jobinja-mcp)](https://pypi.org/project/jobinja-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/sepehr071/jobinja-mcp/blob/main/LICENSE)

[For AI agents](#for-ai-agents) · [Quick start](#quick-start) · [Tools](#tools) · [Limits](#limits) · [فارسی](#فارسی)

</div>

---

## For AI agents

- **What:** unofficial MCP server (model context protocol) for jobinja.ir: job ad search with filters, ad details (salary, skills, degree, military status, description), company profiles, a company's open and past ads, company search by name or industry, and the top-50 company scores.
- **Install:** `uvx jobinja-mcp` or `claude mcp add jobinja -- uvx jobinja-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none, no API key or account. Optional `JOBINJA_MCP_PROXY` (HTTP proxy URL, or a comma-separated list); system proxy settings are ignored.
- **Access:** read-only. It cannot log in, apply, post or save anything, so no confirmation is needed before calling any tool.
- **Network:** jobinja.ir answers only Iranian networks (other countries get HTTP 403). Run it from Iran, or route it through an Iranian proxy with `JOBINJA_MCP_PROXY`.
- **Tools:** 10, all prefixed `jj_`. Typical sequences: `jj_search_jobs` -> `jj_job`; `jj_search_companies` -> `jj_company` -> `jj_company_jobs`; `jj_filters` when a province, category or industry name is rejected.
- **Use when:** the user wants jobs in Iran (استخدام), asks what a company is hiring for, what an ad pays or requires, or which companies Jobinja ranks best.
- **Do not use when:** the user wants reviews or ratings of a company's work culture (Jobinja has none), or jobs outside Iran.
- **Output:** compact JSON; names and descriptions are Persian as Jobinja has them. Salaries are monthly, in Toman.

## Quick start

```bash
claude mcp add jobinja -- uvx jobinja-mcp
```

Or in any MCP client config:

```json
{ "mcpServers": { "jobinja": { "command": "uvx", "args": ["jobinja-mcp"] } } }
```

## Tools

| Tool | What it does |
|---|---|
| `jj_search_jobs` | Ads by keyword, province, city, category, remote, full/part time, internship, experience, benefits (loan, esop, ...), minimum salary, sort; 20 per page |
| `jj_job` | One ad: salary (monthly, Toman), contract, experience, skills, degree, gender, military status, description, similar ads |
| `jj_company` | Company profile: founding year, industry, size, website, open job count, intro, culture and benefits text |
| `jj_company_jobs` | A company's open ads, or its expired ads (hiring history) page by page, up to 100 rows |
| `jj_search_companies` | Companies by name, or one industry, 8 per page |
| `jj_top_companies` | Jobinja's top-50 companies with score out of 10 and three sub-scores |
| `jj_filters` | Exact province, category and industry names, experience levels, salary steps |
| `jj_market` | Live open-ad counts per category, province, city, industry and top skill |
| `jj_skills` | Skills matching a word with how many ads ever listed each |
| `jj_salary_stats` | Min/median/max of stated monthly salaries, sampled from the ad pages of the top results |

> **You:** Remote Python jobs that pay at least 30 million Toman a month?
>
> **Agent:** *calls* `jj_search_jobs(keyword="python", remote=True, min_salary=30)`, then `jj_job` on the best ids.

## Limits

- Ad lists hide salaries from logged-out visitors; the salary is read from each ad page (`jj_job`).
- Jobinja has no employee reviews or salary surveys, so there are none here. The only rating is the top-50 score.
- A search with a single filter (only a province, only a category, only remote) is served from one of Jobinja's SEO pages; results are the same.

## فارسی

`jobinja-mcp` یک سرور MCP غیررسمی و فقط‌خواندنی برای جابینجا (jobinja.ir) است: جستجوی آگهی‌های استخدام با فیلتر استان، دسته‌بندی، دورکاری، نوع قرارداد، سابقه و حداقل حقوق، خواندن کامل آگهی (حقوق، مهارت‌ها، مدرک)، پروفایل شرکت‌ها و آگهی‌های باز آن‌ها، و امتیاز ۵۰ شرکت برتر. نیازی به کلید یا حساب کاربری نیست. جابینجا فقط از شبکه‌های ایران پاسخ می‌دهد.

## License

MIT. Unofficial; not affiliated with Jobinja. Author: Sepehr Radmard (سپهر رادمرد), github.com/sepehr071.
