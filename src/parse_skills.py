"""岗位分类、技能提取、去重累积与每日统计。

流程：读当日快照 → 过滤出数据相关岗 → 分类（分析/科学/工程/其他数据岗）
→ 技能关键词提取 → 累积到jobs.csv（按uid去重，维护first_seen/last_seen）
→ 当日统计写入daily_stats.json（供build_site.py画趋势）。

技能提取是关键词正则匹配，不是NLP。这是刻意选择：口径透明、可解释、
可人工验证，比黑盒模型更适合监测类产品。局限（如R语言的边界匹配噪声）
在README如实记录。

用法：python src/parse_skills.py
产出：data/jobs.csv, data/daily_stats.json
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
JOBS_CSV = PROJECT_ROOT / "data" / "jobs.csv"
STATS_JSON = PROJECT_ROOT / "data" / "daily_stats.json"

# 技能词表：label -> 编译好的正则（作用于小写文本）
SKILL_PATTERNS = {
    "SQL": r"\bsql\b",
    "Python": r"\bpython\b",
    "Excel": r"\bexcel\b",
    "Tableau": r"\btableau\b",
    "Power BI": r"\bpower\s*bi\b",
    "Looker": r"\blooker\b",
    "R": r"\br\b(?!&)",
    "Spark": r"\bspark\b",
    "Snowflake": r"\bsnowflake\b",
    "dbt": r"\bdbt\b",
    "Airflow": r"\bairflow\b",
    "AWS": r"\baws\b",
    "Azure": r"\bazure\b",
    "GCP": r"\bgcp\b|google cloud",
    "BigQuery": r"\bbigquery\b",
    "A/B测试": r"a/b[\s-]*test|\bab test|experimentation",
    "机器学习": r"machine learning|\bml\b",
    "统计学": r"\bstatistic",
    "ETL": r"\betl\b",
    "pandas": r"\bpandas\b",
}
SKILLS = {k: re.compile(v) for k, v in SKILL_PATTERNS.items()}

CAT_SCIENTIST = re.compile(r"data scien|machine learning|\bml (engineer|scientist)|数据科学|算法")
CAT_ENGINEER = re.compile(r"data engineer|analytics engineer|etl|data platform|data infra|数据开发|数仓|数据仓库")
CAT_ANALYST = re.compile(r"analyst|analytics|business intelligence|\bbi\b|数据分析|商业分析|经营分析|数据运营")
DATA_HINT = re.compile(r"\bdata\b|数据")

# 这两个源在API层就已限定为数据类目，岗位名不含关键词时兜底进「其他数据岗」
TRUSTED_DATA_SOURCES = {"remotive", "jobicy"}

CAT_LABELS = {"analyst": "数据分析/BI", "scientist": "数据科学/算法",
              "engineer": "数据开发/工程", "other_data": "其他数据岗"}


def classify(title: str, tags: list[str]) -> str | None:
    t = title.lower()
    if CAT_SCIENTIST.search(t):
        return "scientist"
    if CAT_ENGINEER.search(t):
        return "engineer"
    if CAT_ANALYST.search(t):
        return "analyst"
    if DATA_HINT.search(t) or any(tag in ("data", "analytics", "sql") for tag in tags):
        return "other_data"
    return None


def extract_skills(job: dict) -> list[str]:
    text = " ".join([job.get("title", ""), " ".join(job.get("tags", [])),
                     job.get("description", "")]).lower()
    return [label for label, pat in SKILLS.items() if pat.search(text)]


def normalize_region(job: dict) -> str:
    loc = (job.get("location") or "").lower()
    if job["source"] == "arbeitnow":
        return "Germany"  # 该源为德国岗位板，location只给城市
    mapping = [("united states", "USA"), ("usa", "USA"), ("us only", "USA"),
               ("north america", "北美"), ("europe", "欧洲"), ("emea", "欧洲"),
               ("united kingdom", "UK"), ("uk", "UK"), ("canada", "加拿大"),
               ("germany", "Germany"), ("worldwide", "全球远程"), ("anywhere", "全球远程"),
               ("remote", "全球远程"), ("latam", "拉美"), ("asia", "亚洲"), ("india", "印度")]
    for key, label in mapping:
        if key in loc:
            return label
    return "其他"


def load_snapshot() -> dict:
    latest = sorted(RAW_DIR.glob("*.json"))[-1]
    return json.loads(latest.read_text(encoding="utf-8"))


def load_jobs_csv() -> dict[str, dict]:
    if not JOBS_CSV.exists():
        return {}
    with open(JOBS_CSV, encoding="utf-8-sig", newline="") as f:
        return {row["uid"]: row for row in csv.DictReader(f)}


def save_jobs_csv(jobs: dict[str, dict]) -> None:
    fields = ["uid", "source", "title", "company", "region", "category",
              "skills", "salary_min", "salary_max", "url",
              "first_seen", "last_seen"]
    with open(JOBS_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in jobs.values():
            writer.writerow(row)


def main() -> None:
    snap = load_snapshot()
    date = snap["date"]
    accumulated = load_jobs_csv()

    today_jobs = []
    for job in snap["jobs"]:
        cat = classify(job.get("title", ""), job.get("tags", []))
        if cat is None and job["source"] in TRUSTED_DATA_SOURCES:
            cat = "other_data"
        if cat is None:
            continue
        uid = f"{job['source']}:{job['source_id']}"
        skills = extract_skills(job)
        region = normalize_region(job)
        today_jobs.append({"uid": uid, "category": cat, "skills": skills,
                           "region": region, "job": job})
        if uid in accumulated:
            accumulated[uid]["last_seen"] = date
        else:
            accumulated[uid] = {
                "uid": uid, "source": job["source"], "title": job["title"],
                "company": job["company"], "region": region, "category": cat,
                "skills": "|".join(skills),
                "salary_min": job.get("salary_min") or "",
                "salary_max": job.get("salary_max") or "",
                "url": job["url"], "first_seen": date, "last_seen": date,
            }

    new_today = [j for j in today_jobs if accumulated[j["uid"]]["first_seen"] == date]
    n = len(today_jobs)
    skill_counts = {}
    for j in today_jobs:
        for s in j["skills"]:
            skill_counts[s] = skill_counts.get(s, 0) + 1
    cat_counts = {}
    region_counts = {}
    source_counts = {}
    for j in today_jobs:
        cat_counts[j["category"]] = cat_counts.get(j["category"], 0) + 1
        region_counts[j["region"]] = region_counts.get(j["region"], 0) + 1
        source_counts[j["job"]["source"]] = source_counts.get(j["job"]["source"], 0) + 1

    salaries = [(j["job"].get("salary_min"), j["job"].get("salary_max"))
                for j in today_jobs
                if j["job"].get("salary_min") and j["job"].get("salary_max")]

    stats = json.loads(STATS_JSON.read_text(encoding="utf-8")) if STATS_JSON.exists() else {"days": {}}
    stats["days"][date] = {
        "total_data_jobs": n,
        "new_today": len(new_today),
        "failed_sources": snap.get("failed_sources", []),
        "by_skill": dict(sorted(skill_counts.items(), key=lambda kv: -kv[1])),
        "by_category": {CAT_LABELS[k]: v for k, v in sorted(cat_counts.items(), key=lambda kv: -kv[1])},
        "by_region": dict(sorted(region_counts.items(), key=lambda kv: -kv[1])),
        "by_source": source_counts,
        "salary_usd_year": {
            "n": len(salaries),
            "median_min": sorted(s[0] for s in salaries)[len(salaries) // 2] if salaries else None,
            "median_max": sorted(s[1] for s in salaries)[len(salaries) // 2] if salaries else None,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    STATS_JSON.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    save_jobs_csv(accumulated)

    print(f"{date}: 数据相关岗{n}条（新上架{len(new_today)}），累计追踪{len(accumulated)}条")
    print("分类:", {CAT_LABELS[k]: v for k, v in cat_counts.items()})
    print("技能Top10:", dict(list(sorted(skill_counts.items(), key=lambda kv: -kv[1]))[:10]))
    print(f"带薪资岗位: {len(salaries)}条")


if __name__ == "__main__":
    main()
