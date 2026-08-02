# 浏览器自动化 Web 控制面板 Spec

## Why
目前 browser-cli 仅有命令行接口，用户无法直观看到浏览器窗口和页面渲染效果。需要一个基于 Web 的控制面板，让用户可以在浏览器中看到 WebView 窗口、通过 Web 页面操控自动化操作、实时查看结果。

## What Changes
- 新增 `browser_cli/webui.py` — 基于 Flask 的 Web 控制面板
- 修改 `BrowserController` 支持 `hidden=False` 显示浏览器窗口
- 新增 CLI 命令 `browser-cli webui` 启动 Web 控制面板
- 新增 `browser_cli/templates/` 目录存放前端页面模板
- Web UI 提供：地址栏导航、操作按钮、剧本执行、结果展示

## Impact
- Affected specs: browser-automation-cli
- Affected code: `browser_cli/webui.py`（新增）, `browser_cli/cli.py`（新增 webui 命令）, `browser_cli/controller.py`（支持 visible 模式）

## ADDED Requirements

### Requirement: Web 控制面板启动
系统 SHALL 提供 `browser-cli webui` 命令，启动一个本地 Web 服务器，在浏览器中打开控制面板页面。

#### Scenario: 启动 Web UI
- **WHEN** 执行 `browser-cli webui`
- **THEN** 系统启动 WebView 窗口（可见模式），启动 Flask 服务器，自动打开浏览器访问控制面板

### Requirement: Web 控制面板页面
系统 SHALL 提供一个 Web 页面，包含地址栏、操作按钮和结果展示区。

#### Scenario: 导航操作
- **WHEN** 用户在地址栏输入 URL 并点击"导航"
- **THEN** WebView 窗口导航到目标 URL，页面更新显示当前 URL

#### Scenario: 提取内容
- **WHEN** 用户输入 CSS 选择器并点击"提取"
- **THEN** 系统返回匹配元素的文本内容并展示在结果区

#### Scenario: 执行 JS
- **WHEN** 用户输入 JS 代码并点击"执行"
- **THEN** 系统在 WebView 中执行 JS 并返回结果

#### Scenario: 截图
- **WHEN** 用户点击"截图"按钮
- **THEN** 系统截取当前页面并以图片形式展示在结果区

### Requirement: 实时状态同步
系统 SHALL 通过 WebSocket 或轮询实时同步 WebView 的当前 URL 到控制面板。

#### Scenario: URL 同步
- **WHEN** WebView 中页面发生跳转
- **THEN** 控制面板的地址栏自动更新为当前 URL