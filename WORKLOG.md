## 2026-07-05 19:46

从0到1建成数据岗位需求雷达（作品集第一刀：给全是静态报告的作品集补一个「活的」数据产品）。

产出：
- `src/fetch_jobs.py`：7个免key公开API聚合（RemoteOK/Remotive/ArbeitNow/Jobicy/WorkingNomads/Himalayas/电鸭），单源失败不拖垮整体。首日675条原始岗位
- `src/parse_skills.py`：职位名规则分类（中英文）+20项技能关键词正则提取+跨日去重累积。首日筛出149条数据相关岗；remotive/jobicy源级已限定数据类目，兜底进其他数据岗
- `src/daily_brief.py`：当日简报，LLM版（ANTHROPIC_API_KEY存在时）自动降级规则版
- `src/build_site.py`：ECharts暗色看板（docs/index.html），技能Top15/趋势/类别环图/地区/源贡献，薪资模块样本<30条时不渲染
- `.github/workflows/update.yml`：每日北京时间06:30定时管线，data与docs自动commit
- README含GitHub Desktop向部署步骤（用户不用命令行）

首日数据：SQL提及率38.3%、Python 31.5%、机器学习42.3%、A/B测试12.8%；类别构成其他数据岗39%/分析BI 30%/科学算法21%/开发工程10%；USA岗位最多

踩坑：
- 初版只有3个源时数据岗仅24条/日，撑不起看板。加4个源后149条/日够用
- 正文恰好排满整页时，独立PageBreak段落会产生空白页（见简历项目同日记录），此坑在Word排版通用

待办（用户动作）：
1. GitHub Desktop发布仓库（public）→ Settings/Pages选main分支/docs目录 → Actions手动跑一次验证
2. 把`src/build_site.py`的REPO_URL换成真实仓库地址重跑build_site
3. 可选：仓库Secrets加ANTHROPIC_API_KEY升级LLM简报
4. 中国市场快照模块：等Chrome扩展连上（半自动采集）或用户手动Ctrl+S保存BOSS直聘搜索页到china_snapshot/inbox/，解析脚本届时补
