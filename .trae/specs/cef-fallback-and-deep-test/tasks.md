# Tasks

## T1 - CEF 引擎回退机制

- [x] T1.1: 在 controller.py 新增 `get_available_gui()` 工具函数 — 检测顺序：环境变量 → WebView2 可用性 → CEF 可导入性 → 默认 None
- [x] T1.2: 修改 `BrowserController.run()` — 使用 `get_available_gui()` 替代硬编码 `gui=None`
- [x] T1.3: 修改 `MultiWindowManager.run()` — 使用 `get_available_gui()` 替代硬编码 `gui=None`
- [x] T1.4: 修改 `WindowPool.run()` — 使用 `get_available_gui()` 替代硬编码 `gui=None`
- [x] T1.5: 在 `doctor` 命令中增加 GUI 后端检测信息 — 显示当前后端、可用后端列表、CEF 状态

## T2 - 深度交互能力检测

- [x] T2.1: 在 `doctor` 命令中增加功能完整性自检 — 列出 actions.py 和 parser.py 的方法数量、CLI 命令数量、覆盖度

## T3 - 验证测试

- [x] T3.1: 运行 `doctor` 命令验证 GUI 后端检测输出正确
- [x] T3.2: 运行 `python -m browser_cli.cli --help` 验证所有 CLI 命令注册正确
- [x] T3.3: 验证 `get_available_gui()` 函数逻辑正确（通过导入测试）

# Task Dependencies

- T1.1 完成后 T1.2/T1.3/T1.4 可并行 (已完成)
- T1.5 和 T2.1 都依赖 T1.1 完成 (已完成)
- T3 依赖 T1 和 T2 全部完成 (已完成)