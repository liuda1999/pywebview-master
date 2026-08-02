# 功能差距分析与补全 Spec

## Why
browser-cli 当前已实现基础导航、提取、表单填写、搜索、登录、截图、多窗口等核心功能，但与完整浏览器自动化工具相比，仍有大量功能缺失。需要系统性地分析差距，优先实现 pywebview 架构下可行的功能。

## What Changes

### 可实现的缺失功能（按优先级排列）

**P0 - 基础操作补全：**
- 新增 `hover` 悬停操作
- 新增 `scroll-to` / `scroll-down` 滚动操作
- 新增 `press` 按键操作（Enter、Tab、Escape 等）
- 新增 `wait-for-timeout` 纯等待命令
- 新增 `wait-for-url` 等待 URL 变化命令
- 新增 `snapshot` DOM 文本快照输出
- 新增 `upload` 文件上传（通过 JS 注入设置文件路径）

**P1 - 录制与回放：**
- 新增 `record` 交互式录制命令（注入事件监听器，记录操作序列）
- 新增 `replay` 回放录制的操作序列
- 支持导出录制结果为 JSON/YAML

**P2 - 环境与诊断：**
- 新增 `doctor` 系统环境诊断命令
- 新增 `browsers` 列出已安装浏览器命令

**P3 - 截图增强：**
- 新增元素截图 `screenshot --selector ".main-content"`
- 新增 `pdf` 页面导出 PDF（通过浏览器打印 API）

**P4 - 批量与 CI/CD：**
- 新增 `batch` 批量执行命令（从文件读取 URL 列表或命令序列）
- 支持环境变量配置（`BROWSER_CLI_*` 环境变量）
- 所有命令返回标准退出码

### 平台限制（pywebview 架构不可行）

以下功能需要 Chromium/Firefox 级别 API，pywebview 无法实现：
- 设备仿真（viewport/UA/touch 模拟）
- 网络请求拦截与 Mock
- 网络条件模拟（throttle/offline）
- 视频录制
- 并行多浏览器实例（pywebview 单进程限制）
- 代理/自定义证书
- 浏览器扩展加载
- 代码生成（Playwright/Cypress 代码）
- Trace Viewer
- 测试框架集成（并行 workers、报告器、重试）

## Impact
- Affected specs: fix-five-issues, web-ui
- Affected code: actions.py, cli.py, controller.py, parser.py, webui.py, templates/index.html

## ADDED Requirements

### Requirement: Hover Operation
The system SHALL support hovering over elements via CSS selector.

#### Scenario: Hover over element
- **WHEN** user executes `hover "selector"`
- **THEN** the system dispatches mouseenter/mouseover events on the matched element

### Requirement: Scroll Operations
The system SHALL support scrolling to elements and by pixel amounts.

#### Scenario: Scroll to element
- **WHEN** user executes `scroll-to "footer"`
- **THEN** the element is scrolled into view

#### Scenario: Scroll by pixels
- **WHEN** user executes `scroll-down 500`
- **THEN** the page scrolls down by 500 pixels

### Requirement: Key Press
The system SHALL support simulating keyboard key presses.

#### Scenario: Press Enter key
- **WHEN** user executes `press "Enter"`
- **THEN** a KeyboardEvent with key="Enter" is dispatched on the active element

### Requirement: Wait Commands
The system SHALL support waiting for time duration and URL changes.

#### Scenario: Wait for timeout
- **WHEN** user executes `wait-for-timeout 3000`
- **THEN** the system sleeps for 3000ms

#### Scenario: Wait for URL change
- **WHEN** user executes `wait-for-url "**/success"`
- **THEN** the system polls current URL until it matches the glob pattern or timeout

### Requirement: DOM Snapshot
The system SHALL output a text snapshot of the page DOM.

#### Scenario: Take snapshot
- **WHEN** user executes `snapshot`
- **THEN** the system outputs the page's visible text content and key element structure

### Requirement: File Upload
The system SHALL support setting file input values.

#### Scenario: Upload file
- **WHEN** user executes `upload "input[type=file]" ./report.pdf`
- **THEN** the system attempts to set the file input's value via JS

### Requirement: Interactive Recording
The system SHALL support recording user interactions in the browser.

#### Scenario: Record interactions
- **WHEN** user executes `record --output script.json`
- **THEN** the system opens a browser window, injects event listeners, and records clicks/inputs/scrolls to a JSON file

### Requirement: Replay Recorded Script
The system SHALL support replaying recorded interaction scripts.

#### Scenario: Replay script
- **WHEN** user executes `replay script.json --speed 1.5`
- **THEN** the system executes the recorded operations with the specified speed multiplier

### Requirement: System Diagnostics
The system SHALL provide a `doctor` command to diagnose environment issues.

#### Scenario: Run diagnostics
- **WHEN** user executes `doctor`
- **THEN** the system checks Python version, pywebview dependencies, Edge WebView2 availability, and reports issues with fix suggestions

### Requirement: Browser Listing
The system SHALL provide a `browsers` command to list available browsers.

#### Scenario: List browsers
- **WHEN** user executes `browsers`
- **THEN** the system lists installed browsers detected on the system

### Requirement: Element Screenshot
The system SHALL support taking screenshots of specific elements.

#### Scenario: Screenshot element
- **WHEN** user executes `screenshot element.png --selector ".main-content"`
- **THEN** the system captures only the selected element area

### Requirement: PDF Export
The system SHALL support exporting pages as PDF.

#### Scenario: Export PDF
- **WHEN** user executes `pdf output.pdf --format A4`
- **THEN** the system triggers the browser's print-to-PDF functionality

### Requirement: Batch Execution
The system SHALL support batch execution of URLs or commands from a file.

#### Scenario: Batch URLs
- **WHEN** user executes `batch urls.txt`
- **THEN** the system sequentially navigates to each URL and performs configured actions

### Requirement: Environment Variable Configuration
The system SHALL support configuration via `BROWSER_CLI_*` environment variables.

#### Scenario: Configure via env
- **WHEN** `BROWSER_CLI_TIMEOUT=60` is set
- **THEN** all commands use 60 seconds as default timeout

## MODIFIED Requirements

### Requirement: Screenshot Command
The existing screenshot command SHALL be enhanced to support `--selector` for element-level screenshots.

### Requirement: Wait Command
The existing `wait-for-selector` SHALL be complemented by `wait-for-timeout` and `wait-for-url` commands.

### Requirement: Fill-Steps Command
The existing fill-steps command SHALL support `hover`, `scroll`, `press`, `upload` as new step action types.