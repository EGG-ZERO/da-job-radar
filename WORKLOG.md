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
1. ~~GitHub Desktop发布仓库~~ 已改走gh CLI，见下一条记录
2. ~~REPO_URL替换~~ 已完成
3. 可选：仓库Secrets加ANTHROPIC_API_KEY升级LLM简报
4. 中国市场快照模块：用户决定暂不做（2026-07-05），看板页脚与文档已如实标注口径限制

## 2026-07-05 20:25

发布上线（装gh CLI+设备码登录，账号EGG-ZERO）：

- 仓库 https://github.com/EGG-ZERO/da-job-radar 已推送；Pages已启用（main分支/docs目录），看板在线：**https://egg-zero.github.io/da-job-radar/**（已验证HTTP 200）
- REPO_URL已替换为真实地址并重建站点
- **遗留一个用户动作**：OAuth令牌无workflow权限（两次设备码补授权都超时未完成），工作流文件暂移至`setup/update.yml`。用户需按`setup/README.md`在GitHub网页把它建回`.github/workflows/update.yml`（2分钟），否则每日自动更新不会启动，看板停留在首日数据
- 踩坑：gh auth login的输出接`| head`会截断管道导致进程被SIGPIPE杀死（第一次登录假成功）；设备码流程stdin被关闭会context deadline exceeded，须用`{ printf '\n'; sleep 900; }|`保持stdin打开

## 2026-07-06 01:18

工作流归位并完成云端闭环验证：

- 用户完成workflow scope设备码授权（第三次，前两次15分钟窗口过期）
- setup/update.yml归位到.github/workflows/，setup/临时目录删除，推送成功
- 手动触发首跑：run 28746963724 success。云端管线完整执行（抓取7源→解析→简报→建站→bot提交），产生commit 12f7efc
- 线上验证：egg-zero.github.io/da-job-radar 页面时间戳已变为云端运行时间（16:14 UTC），证明看板脱离本机自主运转
- 明起每日北京时间06:30自动更新，无需任何人工介入

项目状态：完成并在线运行。后续可选增强见README备注（中国快照模块、薪资模块等30条带薪岗位后自动启用）。
