"""生成当日文字简报。

两级实现：
- 默认规则版：今日总量、环比、技能榜首、显著变动，模板拼接，零依赖
- 增强LLM版：设置了ANTHROPIC_API_KEY环境变量且anthropic库可用时，
  把统计JSON交给Claude生成更自然的简报；任何失败都回落到规则版

设计原因：管线的可用性不能依赖外部API key。简报是锦上添花，不是关键路径。

用法：python src/daily_brief.py
产出：data/brief.json
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATS_JSON = PROJECT_ROOT / "data" / "daily_stats.json"
BRIEF_JSON = PROJECT_ROOT / "data" / "brief.json"


def rule_based(days: dict, today: str) -> str:
    d = days[today]
    dates = sorted(days.keys())
    parts = [f"今日在架数据相关岗{d['total_data_jobs']}条，新上架{d['new_today']}条。"]
    if len(dates) >= 2:
        prev = days[dates[-2]]["total_data_jobs"]
        delta = d["total_data_jobs"] - prev
        sign = "增加" if delta >= 0 else "减少"
        parts.append(f"较上一采集日{sign}{abs(delta)}条。")
    skills = list(d["by_skill"].items())
    if skills:
        top = "、".join(f"{k}({v})" for k, v in skills[:3])
        parts.append(f"需求最高技能：{top}。")
    cats = list(d["by_category"].items())
    if cats:
        parts.append(f"岗位构成以{cats[0][0]}为主（{cats[0][1]}条）。")
    if d.get("failed_sources"):
        parts.append(f"注意：数据源{'、'.join(d['failed_sources'])}今日抓取失败，总量偏低。")
    return "".join(parts)


def llm_brief(days: dict, today: str) -> str | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic  # noqa: PLC0415 可选依赖，缺失即回落
        dates = sorted(days.keys())[-7:]
        payload = {d: days[d] for d in dates}
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=400,
            messages=[{"role": "user", "content":
                "你是数据岗位市场监测看板的简报撰写者。根据下面最近几天的统计JSON，"
                "写一段100字以内的中文当日简报：总量与环比、值得注意的技能需求变化、一句对求职者的提示。"
                "只输出简报正文，不要标题，不要客套。语言平实，禁止使用破折号和中文双引号。\n\n"
                + json.dumps(payload, ensure_ascii=False)}],
        )
        text = msg.content[0].text.strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 简报失败不阻塞管线
        print(f"LLM简报失败，回落规则版: {exc}")
        return None


def main() -> None:
    stats = json.loads(STATS_JSON.read_text(encoding="utf-8"))
    days = stats["days"]
    today = sorted(days.keys())[-1]
    text = llm_brief(days, today)
    mode = "llm"
    if text is None:
        text = rule_based(days, today)
        mode = "rule"
    BRIEF_JSON.write_text(json.dumps({"date": today, "mode": mode, "text": text},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{mode}] {text}")


if __name__ == "__main__":
    main()
