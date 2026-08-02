# CEF 引擎回退与深度交互测试 Spec

## Why
1. 当前代码中 `webview.start(gui=None)` 依赖自动检测，在 WebView2 不可用时可能崩溃。需要将已安装的 CEF 作为保底引擎。
2. 需要系统性地检测当前项目是否具备深度网页交互、数据提取过滤、多表单填写能力，确保 CLI 命令完整覆盖。

## What Changes

### 1. CEF 引擎回退机制
- 在 `BrowserController`、`MultiWindowManager`、`WindowPool` 的 `run()` 方法中增加 GUI 后端检测
- 检测顺序：WebView2 (edgechromium) → CEF → 默认
- 增加 `get_available_gui()` 工具函数，检测已安装的 GUI 后端
- 在 `doctor` 命令中显示当前使用的 GUI 后端信息
- 支持通过环境变量 `BROWSER_CLI_GUI` 手动指定 GUI 后端

### 2. 深度交互能力检测
- 验证 actions.py 的 20 个交互方法完整性
- 验证 parser.py 的 9 个数据提取/过滤方法完整性
- 验证 cli.py 的 25 个命令与 actions/parser 方法的对应关系
- 在 `doctor` 命令中增加功能完整性自检

## Impact
- Affected specs: feature-gap-analysis
- Affected code: controller.py, cli.py (doctor 命令)

## ADDED Requirements

### Requirement: CEF Engine Fallback
The system SHALL detect available GUI backends and use CEF as fallback when the primary backend (WebView2) is unavailable.

#### Scenario: WebView2 available
- **WHEN** system starts and WebView2 runtime is detected
- **THEN** `gui='edgechromium'` is used (or `gui=None` for auto-detect)

#### Scenario: WebView2 unavailable, CEF available
- **WHEN** system starts and WebView2 is not detected but `cefpython3` is importable
- **THEN** `gui='cef'` is used as fallback

#### Scenario: Manual override via env
- **WHEN** `BROWSER_CLI_GUI=cef` is set
- **THEN** `gui='cef'` is used regardless of auto-detection

### Requirement: GUI Backend Detection Utility
The system SHALL provide a `get_available_gui()` function that returns the best available GUI backend string.

#### Scenario: Detect available backends
- **WHEN** `get_available_gui()` is called
- **THEN** it returns the GUI type string for the best available backend

### Requirement: Doctor Command GUI Info
The `doctor` command SHALL display the detected GUI backend and available fallbacks.

#### Scenario: Doctor shows GUI info
- **WHEN** user executes `doctor`
- **THEN** the output includes the current GUI backend and available alternatives

### Requirement: Deep Interaction Coverage
The system SHALL provide CLI commands for all major interaction types.

#### Scenario: All interaction types have CLI
- **WHEN** checking CLI commands
- **THEN** commands exist for: click, fill, type, hover, scroll, press, extract, wait, screenshot, login, search, upload, select, snapshot, cookies, dialogs

### Requirement: Data Extraction and Filtering
The system SHALL provide data extraction (links, tables, text, meta, forms, images) and regex filtering capabilities.

#### Scenario: Extract and filter data
- **WHEN** user extracts page content
- **THEN** they can get links, tables, text, meta tags, forms, images and filter by regex

### Requirement: Multi-Form Filling
The system SHALL support filling multiple forms or form fields in sequence via `fill-steps` command.

#### Scenario: Fill multiple forms
- **WHEN** user executes `fill-steps` with multiple steps
- **THEN** each step is executed sequentially on the same page

## MODIFIED Requirements

### Requirement: BrowserController.run() 
The `run()` method SHALL use `get_available_gui()` to determine the `gui` parameter instead of hardcoded `gui=None`.

### Requirement: MultiWindowManager.run()
The `run()` method SHALL use `get_available_gui()` to determine the `gui` parameter.

### Requirement: WindowPool.run()
The `run()` method SHALL use `get_available_gui()` to determine the `gui` parameter.