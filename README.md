# 数据岗位需求雷达（DA Job Radar）

## 做什么

每日自动更新的数据类岗位市场监测看板：聚合7个免key公开API的在架岗位，规则分类+关键词技能提取，累积去重追踪，生成静态看板页。GitHub Actions每日北京时间06:30自动抓取、统计、重建并发布到GitHub Pages。

作品集定位：证明「不止会分析一份静态数据，还能搭一条持续运转的数据管线」。多源抗失效、增量统计、条件降级（LLM简报无key时回落规则版）都是刻意保留的工程展示点。

## 怎么跑

本地单次运行（零第三方依赖，LLM简报可选）：

```bash
python src/fetch_jobs.py     # 抓取7源 -> data/raw/当日.json
python src/parse_skills.py   # 分类+技能提取+去重累积 -> data/jobs.csv, data/daily_stats.json
python src/daily_brief.py    # 当日简报 -> data/brief.json（设ANTHROPIC_API_KEY则用LLM版）
python src/build_site.py     # 渲染看板 -> docs/index.html
```

## 部署为每日自动更新（GitHub Desktop向，一次性10分钟）

1. GitHub Desktop：File → Add local repository → 选本项目文件夹 → create a repository here → Publish repository（去掉private勾选）
2. 仓库网页 → Settings → Pages → Source选「Deploy from a branch」→ Branch选main、目录选`/docs` → Save
3. 仓库网页 → Actions → 启用workflows → 手动跑一次`daily-update`验证
4. 可选：Settings → Secrets and variables → Actions → 新建`ANTHROPIC_API_KEY`，简报升级为LLM生成
5. 把`src/build_site.py`里的`REPO_URL`换成你的仓库地址，重跑一次

## 目录结构

```
├── src/
│   ├── fetch_jobs.py      # 7源抓取，单源失败不拖垮整体
│   ├── parse_skills.py    # 岗位分类/技能关键词提取/去重累积/每日统计
│   ├── daily_brief.py     # 每日简报（LLM可选，自动降级）
│   └── build_site.py      # 静态看板渲染（ECharts）
├── data/
│   ├── raw/               # 每日原始快照
│   ├── jobs.csv           # 去重累积的岗位明细
│   ├── daily_stats.json   # 逐日统计（趋势图数据源）
│   └── brief.json         # 当日简报
├── docs/index.html        # 看板页（GitHub Pages发布目录）
└── .github/workflows/update.yml   # 每日定时管线
```

## 数据源与口径

7个免key公开API：RemoteOK、Remotive（data类目）、ArbeitNow（德国）、Jobicy（data-science类目）、Working Nomads、Himalayas、电鸭社区（中文远程）。

**口径限制（如实声明）**：样本为国际远程岗为主+少量中文远程岗，不代表中国大陆主流招聘市场。技能识别是关键词正则匹配，透明可复核但有少量噪声（如R语言的词边界误配）。岗位类别按职位名规则分类，源级已限定数据类目的源兜底进「其他数据岗」。

## 依赖

- Python 3.10+（管线本体仅标准库）
- anthropic（可选，仅LLM简报）

## 备注

- 首日数据2026-07-05：675条原始岗位，149条数据相关岗，7源全部成功
- 趋势图随运行天数累积，上线第一周点数少是正常状态
- 中国大陆市场快照（人工采集+自动分析）计划作为配套模块，见工作日志
