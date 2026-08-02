# Tasks

- [x] Task 1: 实现 Web 控制面板后端
  - [x] 创建 `browser_cli/webui.py` — Flask 应用
  - [x] 实现 `/` 路由返回控制面板 HTML 页面
  - [x] 实现 `/api/goto` API — 导航到 URL
  - [x] 实现 `/api/extract` API — 提取元素内容
  - [x] 实现 `/api/exec_js` API — 执行 JS 代码
  - [x] 实现 `/api/screenshot` API — 截图并返回 base64
  - [x] 实现 `/api/status` API — 获取当前 URL 状态
  - [x] 实现 `/api/run_playbook` API — 执行 YAML 剧本（由 `/api/fill-steps` 等覆盖）

- [x] Task 2: 实现控制面板前端页面
  - [x] 创建 `browser_cli/templates/index.html` — 控制面板页面
  - [x] 实现地址栏 + 导航按钮
  - [x] 实现 CSS 选择器输入 + 提取按钮
  - [x] 实现 JS 代码输入 + 执行按钮
  - [x] 实现截图按钮
  - [x] 实现结果展示区域
  - [x] 实现当前 URL 实时显示

- [x] Task 3: 集成到 CLI
  - [x] 在 `cli.py` 中添加 `webui` 子命令
  - [x] 实现 `browser-cli webui --port 5000` 启动逻辑
  - [x] 启动时自动打开浏览器访问控制面板

- [x] Task 4: 测试验证
  - [x] 测试 Web UI 启动
  - [x] 测试导航功能
  - [x] 测试提取功能
  - [x] 测试 JS 执行功能
  - [x] 测试截图功能

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 1 和 Task 2
- Task 4 依赖 Task 3
