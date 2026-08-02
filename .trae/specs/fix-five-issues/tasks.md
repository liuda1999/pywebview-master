# Tasks

- [x] Task 1: 修复 #1 - 多窗口管理
  - [x] 在 `controller.py` 添加 `MultiWindowManager` 类
  - [x] 添加 CLI `multi-window` 命令
  - [x] 实现同时打开多个窗口并在同一 session 中管理

- [x] Task 2: 修复 #2 - 动态内容抓取
  - [x] extract 命令添加 `--wait-selector` 选项
  - [x] extract 命令添加 `--wait-dynamic` 选项
  - [x] 在 `/api/extract` 也支持等待参数

- [x] Task 3: 修复 #3 - 多步表单填写
  - [x] 新增 CLI `fill-steps` 命令
  - [x] 支持 `--step "action:selector:value"` 格式
  - [x] 支持 fill / click / wait / type / select / extract 六种步骤动作
  - [x] 支持 `--step-file` 从文件读取步骤

- [x] Task 4: 修复 #4 - 登录命令
  - [x] 新增 CLI `login` 命令
  - [x] 支持 `--username` / `--password` 参数
  - [x] 支持自定义选择器 `--username-selector` / `--password-selector` / `--submit-selector`
  - [x] 登录后支持 `--extract` 提取内容

- [x] Task 5: 修复 #5 - 搜索结果提取
  - [x] search 命令添加 `--extract-result` 选项
  - [x] search 命令添加 `--wait-result` 等待搜索结果加载时间
  - [x] 搜索完成后自动提取并输出结果

# Task Dependencies
- 所有 Task 互相独立，可并行实现
