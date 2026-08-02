# CEF 引擎回退与深度交互测试 - 验证清单

## T1 - CEF 引擎回退机制

- [x] T1.1: `get_available_gui()` 函数存在且逻辑正确（环境变量优先 → WebView2 → CEF → None）
- [x] T1.2: `BrowserController.run()` 使用 `get_available_gui()` 而非硬编码 `gui=None`
- [x] T1.3: `MultiWindowManager.run()` 使用 `get_available_gui()` 而非硬编码 `gui=None`
- [x] T1.4: `WindowPool.run()` 使用 `get_available_gui()` 而非硬编码 `gui=None`
- [x] T1.5: `doctor` 输出包含 GUI 后端信息（当前后端、可用后端列表、CEF 状态）

## T2 - 深度交互能力检测

- [x] T2.1: `doctor` 输出包含功能完整性统计（actions 方法数、parser 方法数、CLI 命令数、覆盖度）

## T3 - 验证测试

- [x] T3.1: `doctor` 命令执行成功且输出包含 GUI 后端信息和功能统计
- [x] T3.2: `--help` 输出包含全部 25 个 CLI 命令
- [x] T3.3: `get_available_gui()` 导入测试通过，返回值符合预期