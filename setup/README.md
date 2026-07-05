# 启用每日自动更新（一次性，2分钟，在GitHub网页完成）

`update.yml`是每日自动更新的工作流文件。因上传时的令牌没有workflow权限，暂放本目录，需要你在网页上把它放回正确位置：

1. 打开仓库页面 → 点上方「Add file」→「Create new file」
2. 文件名输入：`.github/workflows/update.yml`（会自动创建目录）
3. 把本目录`update.yml`的全部内容复制粘贴进去（在GitHub里打开该文件点Raw复制最方便）
4. 点「Commit changes」提交

完成后：仓库「Actions」页签 → 左侧选`daily-update` → 「Run workflow」手动跑一次验证。以后每天北京时间06:30自动运行。

验证通过后可以删除本setup目录。
