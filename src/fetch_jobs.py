"""从三个免key公开API抓取在架岗位，规范化后落盘当日快照。

数据源（全部无需注册，选择多源是为了抗单点失效：任一源挂掉管线继续跑）：
- RemoteOK        https://remoteok.com/api
- Remotive        https://remotive.com/api/remote-jobs?category=data（源级已限定data类）
- ArbeitNow       https://www.arbeitnow.com/api/job-board-api（德国岗位板）
- Jobicy          https://jobicy.com/api/v2/remote-jobs?industry=data-science（源级已限定）
- Working Nomads  https://www.workingnomads.com/api/exposed_jobs/
- Himalayas       https://himalayas.app/jobs/api（带薪资字段）
- 电鸭社区        https://svc.eleduck.com/api/v1/posts?category=5（中文远程岗）

口径：国际远程岗为主+少量中文远程岗，非中国大陆主流市场样本。看板页脚和README如实标注。

用法：python src/fetch_jobs.py
产出：data/raw/YYYY-MM-DD.json（当日全量快照，UTC日期）
退出码：三源全挂时非0，任一源成功则0。
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (compatible; da-job-radar/1.0; portfolio project)"}
TAG_RE = re.compile(r"<[^>]+>")


def get_json(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", text or "")).strip()


def fetch_remoteok() -> list[dict]:
    data = get_json("https://remoteok.com/api")
    jobs = []
    for item in data:
        if not isinstance(item, dict) or "id" not in item or "position" not in item:
            continue  # 首元素是法律声明
        jobs.append({
            "source": "remoteok",
            "source_id": str(item["id"]),
            "title": item.get("position", ""),
            "company": item.get("company", ""),
            "location": item.get("location", "") or "Remote",
            "tags": [str(t).lower() for t in (item.get("tags") or [])],
            "salary_min": item.get("salary_min") or None,
            "salary_max": item.get("salary_max") or None,
            "url": item.get("url", ""),
            "published_at": item.get("date", ""),
            "description": strip_html(item.get("description", ""))[:4000],
        })
    return jobs


def fetch_remotive() -> list[dict]:
    data = get_json("https://remotive.com/api/remote-jobs?category=data")
    jobs = []
    for item in data.get("jobs", []):
        jobs.append({
            "source": "remotive",
            "source_id": str(item.get("id")),
            "title": item.get("title", ""),
            "company": item.get("company_name", ""),
            "location": item.get("candidate_required_location", "") or "Remote",
            "tags": [str(t).lower() for t in (item.get("tags") or [])],
            "salary_min": None,
            "salary_max": None,
            "salary_raw": item.get("salary", ""),
            "url": item.get("url", ""),
            "published_at": item.get("publication_date", ""),
            "description": strip_html(item.get("description", ""))[:4000],
        })
    return jobs


def fetch_arbeitnow() -> list[dict]:
    jobs = []
    url = "https://www.arbeitnow.com/api/job-board-api"
    for _ in range(3):  # 最多翻3页，避免无限翻页
        data = get_json(url)
        for item in data.get("data", []):
            jobs.append({
                "source": "arbeitnow",
                "source_id": item.get("slug", ""),
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("location", "") or "Remote",
                "tags": [str(t).lower() for t in (item.get("tags") or [])],
                "salary_min": None,
                "salary_max": None,
                "url": item.get("url", ""),
                "published_at": str(item.get("created_at", "")),
                "description": strip_html(item.get("description", ""))[:4000],
            })
        url = (data.get("links") or {}).get("next")
        if not url:
            break
    return jobs


def fetch_jobicy() -> list[dict]:
    data = get_json("https://jobicy.com/api/v2/remote-jobs?count=100&industry=data-science")
    jobs = []
    for item in data.get("jobs", []):
        jobs.append({
            "source": "jobicy",
            "source_id": str(item.get("id")),
            "title": item.get("jobTitle", ""),
            "company": item.get("companyName", ""),
            "location": item.get("jobGeo", "") or "Remote",
            "tags": [str(item.get("jobLevel", "")).lower()],
            "salary_min": item.get("annualSalaryMin") or None,
            "salary_max": item.get("annualSalaryMax") or None,
            "url": item.get("url", ""),
            "published_at": str(item.get("pubDate", "")),
            "description": strip_html(item.get("jobDescription", "") or item.get("jobExcerpt", ""))[:4000],
        })
    return jobs


def fetch_workingnomads() -> list[dict]:
    data = get_json("https://www.workingnomads.com/api/exposed_jobs/")
    jobs = []
    for item in data:
        jobs.append({
            "source": "workingnomads",
            "source_id": item.get("url", "")[-80:],
            "title": item.get("title", ""),
            "company": item.get("company_name", ""),
            "location": item.get("location", "") or "Remote",
            "tags": [t.strip().lower() for t in (item.get("tags") or "").split(",") if t.strip()]
                    + [str(item.get("category_name", "")).lower()],
            "salary_min": None,
            "salary_max": None,
            "url": item.get("url", ""),
            "published_at": str(item.get("pub_date", "")),
            "description": strip_html(item.get("description", ""))[:4000],
        })
    return jobs


def fetch_himalayas() -> list[dict]:
    jobs = []
    for offset in (0, 20, 40, 60, 80):
        data = get_json(f"https://himalayas.app/jobs/api?limit=20&offset={offset}")
        batch = data.get("jobs", [])
        for item in batch:
            jobs.append({
                "source": "himalayas",
                "source_id": f"{item.get('companySlug', '')}-{item.get('title', '')}"[:120],
                "title": item.get("title", ""),
                "company": item.get("companyName", ""),
                "location": ",".join(item.get("locationRestrictions") or []) or "Remote",
                "tags": [str(item.get("seniority", "")).lower()],
                "salary_min": item.get("minSalary") or None,
                "salary_max": item.get("maxSalary") or None,
                "url": f"https://himalayas.app/companies/{item.get('companySlug', '')}/jobs",
                "published_at": str(item.get("pubDate", "")),
                "description": strip_html(item.get("description", "") or item.get("excerpt", ""))[:4000],
            })
        if len(batch) < 20:
            break
    return jobs


def fetch_eleduck() -> list[dict]:
    data = get_json("https://svc.eleduck.com/api/v1/posts?category=5")
    jobs = []
    for item in data.get("posts", []):
        if item.get("closed") or item.get("deleted"):
            continue
        jobs.append({
            "source": "eleduck",
            "source_id": str(item.get("id")),
            "title": item.get("title", "") or item.get("full_title", ""),
            "company": "",
            "location": "中文远程",
            "tags": [],
            "salary_min": None,
            "salary_max": None,
            "url": f"https://eleduck.com/posts/{item.get('id')}",
            "published_at": str(item.get("published_at", "")),
            "description": strip_html(item.get("summary", ""))[:4000],
        })
    return jobs


def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    all_jobs: list[dict] = []
    failures: list[str] = []
    for name, fn in [("remoteok", fetch_remoteok),
                     ("remotive", fetch_remotive),
                     ("arbeitnow", fetch_arbeitnow),
                     ("jobicy", fetch_jobicy),
                     ("workingnomads", fetch_workingnomads),
                     ("himalayas", fetch_himalayas),
                     ("eleduck", fetch_eleduck)]:
        try:
            jobs = fn()
            print(f"[OK] {name}: {len(jobs)} 条")
            all_jobs.extend(jobs)
        except Exception as exc:  # noqa: BLE001 单源失败不拖垮整体
            print(f"[FAIL] {name}: {exc}")
            failures.append(name)

    if not all_jobs:
        print("三个源全部失败，退出")
        sys.exit(1)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"{today}.json"
    out.write_text(json.dumps({
        "date": today,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "failed_sources": failures,
        "jobs": all_jobs,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"快照已保存: {out} 共{len(all_jobs)}条（含非数据岗，分类在下一步）")


if __name__ == "__main__":
    main()
