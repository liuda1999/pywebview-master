# Tasks

## P0 - 基础操作补全

- [x] P0.1: 新增 hover 悬停操作 — 在 actions.py 添加 `hover` 方法，在 cli.py 添加 `hover` 命令
- [x] P0.2: 新增 scroll 滚动操作 — 在 actions.py 添加 `scroll_to_selector` 和 `scroll_by` 方法，cli 添加 `scroll-to` / `scroll-down` 命令
- [x] P0.3: 新增 press 按键操作 — 在 actions.py 添加 `press_key` 方法，cli 添加 `press` 命令
- [x] P0.4: 新增 `wait-for-timeout` cli 命令
- [x] P0.5: 新增 `wait-for-url` cli 命令（轮询 URL 直到匹配 glob 模式）
- [x] P0.6: 新增 `snapshot` cli 命令（输出 DOM 文本快照）
- [x] P0.7: 新增 `upload` 文件上传操作 — 在 actions.py 添加 `upload_file` 方法，cli 添加 `upload` 命令
- [x] P0.8: 在 fill-steps 支持新增操作类型：hover/scroll/press/upload/snapshot

## P1 - 环境与诊断

- [x] P1.1: 新增 `doctor` cli 命令 — 检查 Python 版本、pywebview 依赖、WebView2 可用性
- [x] P1.2: 新增 `browsers` cli 命令 — 列出系统已安装浏览器（Windows 下探测 Edge/Chrome/Firefox 路径）

## P2 - 截图增强

- [x] P2.1: 增强 `screenshot` cli 命令 — 添加 `--selector` 选项，支持仅截取指定元素

## P3 - 录制与回放

- [x] P3.1: 新增 `record` cli 命令 — 注入 JS 事件监听器，记录用户操作到 JSON 文件
- [x] P3.2: 新增 `replay` cli 命令 — 回放 JSON 格式的操作序列，支持 `--speed` 速度调节

## P4 - 批量执行与 CI/CD

- [x] P4.1: 新增 `batch` cli 命令 — 逐行读取文件中的 URL 或命令，批量执行
- [x] P4.2: 添加环境变量配置读取 — 读取 `BROWSER_CLI_*` 环境变量覆盖默认值

## P5 - 导出 PDF

- [x] P5.1: 新增 `pdf` cli 命令 — 通过浏览器打印 API 导出页面为 PDF

# Task Dependencies

- P0 任务全部完成后才能开始 P1 (已完成)
- P0 不依赖其他任务 (已完成)