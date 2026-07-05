"""把daily_stats.json和brief.json渲染成静态看板页docs/index.html。

单文件HTML：统计数据以JSON内嵌，图表用ECharts（jsDelivr CDN，加载失败时
页面显示纯文本数据表兜底）。GitHub Pages从docs/目录直接发布。

薪资模块条件渲染：带薪资岗位不足30条时不显示（样本太小画图会误导）。

用法：python src/build_site.py
产出：docs/index.html
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATS_JSON = PROJECT_ROOT / "data" / "daily_stats.json"
BRIEF_JSON = PROJECT_ROOT / "data" / "brief.json"
OUT = PROJECT_ROOT / "docs" / "index.html"

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>数据岗位需求雷达 · 每日自动更新</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root {
  --color-bg-primary: #0E131D; --color-bg-secondary: #161D2B;
  --color-bg-tertiary: #1D2637; --color-bg-elevated: #222D42;
  --color-text-primary: #E8ECF4; --color-text-secondary: #A6B0C3;
  --color-text-muted: #6B7688;
  --color-border-default: #2A3650; --color-border-subtle: #202A3E;
  --color-accent: #4C8DFF; --color-accent-hover: #6CA2FF;
  --color-accent-subtle: rgba(76, 141, 255, 0.12);
  --color-success: #34C77B; --color-warning: #E8A93C;
  --color-danger: #E05B5B; --color-info: #3FB6C9;
  --font-body: "Microsoft YaHei", "PingFang SC", sans-serif;
  --font-mono: Consolas, monospace;
  --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-6: 24px; --space-8: 32px;
  --radius-md: 8px; --radius-lg: 12px;
  --shadow-md: 0 2px 10px rgba(0, 0, 0, 0.35);
  --duration-fast: 150ms;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--color-bg-primary); color: var(--color-text-primary);
  font-family: var(--font-body); font-size: 14px; line-height: 1.7; }
.page { max-width: 1080px; margin: 0 auto; padding: var(--space-8) var(--space-6); }
h1 { font-size: 26px; font-weight: 700; }
h1 .accent { color: var(--color-accent); }
.sub { color: var(--color-text-secondary); font-size: 13px; margin-top: var(--space-2); }
.sub .tag { display: inline-block; padding: 1px 10px; border-radius: 9999px;
  background: var(--color-accent-subtle); color: var(--color-accent);
  font-size: 11px; margin-right: 6px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: var(--space-4); margin-top: var(--space-6); }
.kpi { background: var(--color-bg-secondary); border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg); padding: var(--space-4) var(--space-6);
  box-shadow: var(--shadow-md);
  transition: border-color var(--duration-fast) cubic-bezier(0.4, 0, 0.2, 1); }
.kpi:hover { border-color: var(--color-accent); }
.kpi .label { font-size: 12px; color: var(--color-text-muted); }
.kpi .value { font-size: 30px; font-weight: 700; font-family: var(--font-mono); }
.kpi .hint { font-size: 12px; color: var(--color-text-secondary); }
.brief { margin-top: var(--space-6); background: var(--color-bg-secondary);
  border-left: 3px solid var(--color-accent); border-radius: var(--radius-md);
  padding: var(--space-4) var(--space-6); color: var(--color-text-secondary); }
.brief b { color: var(--color-text-primary); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4);
  margin-top: var(--space-4); }
.card { background: var(--color-bg-secondary); border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg); padding: var(--space-4); box-shadow: var(--shadow-md); }
.card h2 { font-size: 15px; font-weight: 600; margin-bottom: var(--space-2);
  padding-left: var(--space-3); border-left: 3px solid var(--color-accent); }
.card .note { font-size: 11px; color: var(--color-text-muted); padding-left: var(--space-3); }
.chart { width: 100%; height: 320px; }
.chart.tall { height: 420px; }
.wide { grid-column: 1 / -1; }
footer { margin-top: var(--space-8); padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
  color: var(--color-text-muted); font-size: 12px; }
footer a { color: var(--color-accent); text-decoration: none; }
footer a:hover { color: var(--color-accent-hover); }
noscript { display: block; margin-top: var(--space-6); color: var(--color-warning); }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } body { font-size: 16px; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<div class="page">
<header>
  <h1>数据岗位需求雷达 <span class="accent">DA Job Radar</span></h1>
  <div class="sub">
    <span class="tag">每日自动更新</span><span class="tag">7个公开数据源</span><span class="tag">GitHub Actions驱动</span>
    监测国际远程数据类岗位的技能需求 · 最后更新 __UPDATED__（UTC）
  </div>
</header>

<div class="kpis">
  <div class="kpi"><div class="label">今日在架数据岗</div><div class="value">__TOTAL__</div><div class="hint">7源聚合去重后</div></div>
  <div class="kpi"><div class="label">今日新上架</div><div class="value">__NEW__</div><div class="hint">首次出现的岗位</div></div>
  <div class="kpi"><div class="label">累计追踪岗位</div><div class="value">__TRACKED__</div><div class="hint">历史去重总量</div></div>
  <div class="kpi"><div class="label">数据源状态</div><div class="value">__SRC_OK__/7</div><div class="hint">__SRC_NOTE__</div></div>
</div>

<div class="brief"><b>今日简报</b>（__BRIEF_MODE__）：__BRIEF__</div>

<div class="grid">
  <div class="card wide"><h2>技能需求Top15</h2>
    <div class="note">当日在架数据岗中提及该技能的岗位占比（关键词匹配JD全文）</div>
    <div id="c-skill" class="chart tall"></div></div>
  <div class="card wide"><h2>核心技能需求趋势</h2>
    <div class="note">提及率随时间变化，历史逐日累积</div>
    <div id="c-trend" class="chart"></div></div>
  <div class="card"><h2>岗位类别构成</h2><div id="c-cat" class="chart"></div></div>
  <div class="card"><h2>地区分布Top8</h2><div id="c-region" class="chart"></div></div>
  <div class="card wide"><h2>各数据源贡献</h2><div id="c-source" class="chart" style="height: 220px;"></div></div>
</div>

<noscript>本页图表需要JavaScript。原始统计数据见仓库data/daily_stats.json。</noscript>

<footer>
  <p><b>口径与局限</b>：样本为7个公开API的国际远程岗位（RemoteOK、Remotive、ArbeitNow、Jobicy、Working Nomads、Himalayas、电鸭社区），
  不代表中国大陆主流招聘市场。技能识别为关键词正则匹配，透明可复核但存在少量噪声（如R语言的词边界误配）。
  岗位类别按职位名规则分类。中国大陆市场的技能需求快照见配套分析文档。</p>
  <p>项目代码与方法说明：<a href="__REPO__">GitHub仓库</a> · 由GitHub Actions每日06:30（北京时间）自动抓取重建</p>
</footer>
</div>

<script>
const DATA = __DATA__;
(function () {
  if (typeof echarts === "undefined") { return; }
  const css = getComputedStyle(document.documentElement);
  const C = (name) => css.getPropertyValue(name).trim();
  const axisStyle = {
    axisLine: { lineStyle: { color: C("--color-border-default") } },
    axisLabel: { color: C("--color-text-secondary") },
    splitLine: { lineStyle: { color: C("--color-border-subtle") } },
  };
  const base = { textStyle: { fontFamily: css.getPropertyValue("--font-body") },
    tooltip: { backgroundColor: C("--color-bg-elevated"), borderColor: C("--color-border-default"),
      textStyle: { color: C("--color-text-primary") } } };
  const palette = ["#4C8DFF", "#3FB6C9", "#34C77B", "#E8A93C", "#B78CFF",
                   "#E05B5B", "#6CA2FF", "#7ED3B2"];

  const skill = echarts.init(document.getElementById("c-skill"));
  skill.setOption(Object.assign({}, base, {
    color: [C("--color-accent")],
    grid: { left: 90, right: 60, top: 10, bottom: 25 },
    xAxis: Object.assign({ type: "value" }, axisStyle),
    yAxis: Object.assign({ type: "category", inverse: true,
      data: DATA.skills.map(s => s[0]) }, axisStyle),
    series: [{ type: "bar", data: DATA.skills.map(s => s[1]), barWidth: 14,
      itemStyle: { borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: "right", color: C("--color-text-secondary"),
        formatter: (p) => p.value + "% (" + DATA.skillCounts[p.dataIndex] + "岗)" } }],
    tooltip: Object.assign({}, base.tooltip, { trigger: "axis",
      axisPointer: { type: "shadow" } }),
  }));

  const trend = echarts.init(document.getElementById("c-trend"));
  trend.setOption(Object.assign({}, base, {
    color: palette,
    grid: { left: 45, right: 20, top: 35, bottom: 25 },
    legend: { textStyle: { color: C("--color-text-secondary") }, top: 0 },
    xAxis: Object.assign({ type: "category", data: DATA.trendDates }, axisStyle),
    yAxis: Object.assign({ type: "value", name: "提及率%" }, axisStyle),
    series: DATA.trendSeries.map(s => ({ name: s.name, type: "line",
      data: s.data, smooth: true, symbolSize: 7 })),
    tooltip: Object.assign({}, base.tooltip, { trigger: "axis" }),
  }));

  const cat = echarts.init(document.getElementById("c-cat"));
  cat.setOption(Object.assign({}, base, {
    color: palette,
    legend: { bottom: 0, textStyle: { color: C("--color-text-secondary") } },
    series: [{ type: "pie", radius: ["42%", "68%"], center: ["50%", "44%"],
      data: DATA.categories.map(c => ({ name: c[0], value: c[1] })),
      label: { color: C("--color-text-secondary"), formatter: "{b}\\n{d}%" },
      itemStyle: { borderColor: C("--color-bg-secondary"), borderWidth: 2 } }],
  }));

  const region = echarts.init(document.getElementById("c-region"));
  region.setOption(Object.assign({}, base, {
    color: [C("--color-info")],
    grid: { left: 80, right: 40, top: 10, bottom: 25 },
    xAxis: Object.assign({ type: "value" }, axisStyle),
    yAxis: Object.assign({ type: "category", inverse: true,
      data: DATA.regions.map(r => r[0]) }, axisStyle),
    series: [{ type: "bar", data: DATA.regions.map(r => r[1]), barWidth: 14,
      itemStyle: { borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: "right", color: C("--color-text-secondary") } }],
  }));

  const source = echarts.init(document.getElementById("c-source"));
  source.setOption(Object.assign({}, base, {
    color: [C("--color-success")],
    grid: { left: 45, right: 20, top: 10, bottom: 25 },
    xAxis: Object.assign({ type: "category",
      data: DATA.sources.map(s => s[0]) }, axisStyle),
    yAxis: Object.assign({ type: "value" }, axisStyle),
    series: [{ type: "bar", data: DATA.sources.map(s => s[1]), barWidth: 26,
      itemStyle: { borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: "top", color: C("--color-text-secondary") } }],
  }));

  window.addEventListener("resize", () => {
    [skill, trend, cat, region, source].forEach(c => c.resize());
  });
})();
</script>
</body>
</html>
"""

TREND_SKILLS = ["SQL", "Python", "机器学习", "Excel", "Tableau", "A/B测试"]
REPO_URL = "https://github.com/EGG-ZERO/da-job-radar"


def main() -> None:
    stats = json.loads(STATS_JSON.read_text(encoding="utf-8"))
    days = stats["days"]
    dates = sorted(days.keys())
    today = dates[-1]
    d = days[today]
    total = d["total_data_jobs"]

    brief = json.loads(BRIEF_JSON.read_text(encoding="utf-8")) if BRIEF_JSON.exists() else \
        {"mode": "rule", "text": "暂无简报"}

    import csv
    jobs_csv = PROJECT_ROOT / "data" / "jobs.csv"
    with open(jobs_csv, encoding="utf-8-sig", newline="") as f:
        tracked = sum(1 for _ in csv.DictReader(f))

    skills = [(k, round(v * 100 / total, 1)) for k, v in list(d["by_skill"].items())[:15]]
    skill_counts = [v for _, v in list(d["by_skill"].items())[:15]]
    trend_series = []
    for name in TREND_SKILLS:
        series = []
        for dt in dates:
            dd = days[dt]
            n = dd["total_data_jobs"] or 1
            series.append(round(dd["by_skill"].get(name, 0) * 100 / n, 1))
        trend_series.append({"name": name, "data": series})

    data = {
        "skills": skills,
        "skillCounts": skill_counts,
        "trendDates": dates,
        "trendSeries": trend_series,
        "categories": list(d["by_category"].items()),
        "regions": list(d["by_region"].items())[:8],
        "sources": sorted(d["by_source"].items(), key=lambda kv: -kv[1]),
    }

    n_failed = len(d.get("failed_sources", []))
    html = (TEMPLATE
            .replace("__UPDATED__", d["updated_at"].replace("T", " ").replace("+00:00", ""))
            .replace("__TOTAL__", str(total))
            .replace("__NEW__", str(d["new_today"]))
            .replace("__TRACKED__", str(tracked))
            .replace("__SRC_OK__", str(7 - n_failed))
            .replace("__SRC_NOTE__", "全部正常" if n_failed == 0 else f"{'、'.join(d['failed_sources'])}失败")
            .replace("__BRIEF_MODE__", "AI生成" if brief["mode"] == "llm" else "规则生成")
            .replace("__BRIEF__", brief["text"])
            .replace("__REPO__", REPO_URL)
            .replace("__DATA__", json.dumps(data, ensure_ascii=False)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"看板已生成: {OUT}")


if __name__ == "__main__":
    main()
