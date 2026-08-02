# 浏览器自动化 CLI 工具 Spec

## Why
基于 pywebview 库构建一个命令行浏览器自动化工具，无需真实浏览器即可完成页面跳转、内容抓取、表单填写、登录注入等操作，适用于自动化测试、数据采集、RPA 等场景。

## What Changes
- 新建 `browser_cli/` 项目目录，包含完整的 CLI 工具源码
- 实现 `BrowserController` 核心控制器，封装 pywebview 窗口生命周期
- 实现 `AutomationActions` 高级自动化动作模块（goto、fill、click、extract、search、login 等）
- 实现 `ContentParser` 结构化数据提取模块
- 实现 CLI 命令行接口，支持单命令和 YAML 剧本两种模式
- 提供示例剧本文件和 README 使用文档

## Impact
- Affected specs: 无（新项目，独立于 pywebview 源码目录）
- Affected code: `browser_cli/` 目录下所有文件（全新创建）

## ADDED Requirements

### Requirement: BrowserController 核心控制器
系统 SHALL 提供一个 `BrowserController` 类，封装 pywebview 窗口的创建、配置、生命周期管理和安全退出。

#### Scenario: 创建隐藏窗口
- **WHEN** 调用 `BrowserController.__init__(hidden=True)`
- **THEN** 系统创建 pywebview 窗口，配置为隐藏模式、忽略 SSL 错误、隐私模式，并等待窗口就绪

#### Scenario: 同步执行 JavaScript
- **WHEN** 调用 `controller.exec_js(script)`
- **THEN** 系统在 WebView 中执行 JS 并同步返回 JSON 可序列化的结果

#### Scenario: 等待页面加载
- **WHEN** 调用 `controller.wait_loaded(timeout=10)`
- **THEN** 系统阻塞等待直到 `events.loaded` 事件触发或超时抛出异常

### Requirement: 页面跳转与加载
系统 SHALL 支持加载 URL、本地 HTML，并等待页面加载完成。

#### Scenario: 加载 URL
- **WHEN** 调用 `controller.goto("https://example.com")`
- **THEN** 系统导航到目标 URL 并等待页面加载完成

#### Scenario: 加载本地 HTML
- **WHEN** 调用 `controller.load_html("<h1>Hello</h1>")`
- **THEN** 系统加载 HTML 内容并等待渲染完成

### Requirement: 元素定位与操作
系统 SHALL 支持通过 CSS 选择器定位元素，执行点击、输入、清空等操作。

#### Scenario: 点击元素
- **WHEN** 调用 `controller.click("#submit-btn")`
- **THEN** 系统定位元素并触发 click 事件

#### Scenario: 填写输入框
- **WHEN** 调用 `controller.fill("#username", "admin")`
- **THEN** 系统设置元素 value，触发 input 和 change 事件以兼容前端框架

#### Scenario: 逐字符输入
- **WHEN** 调用 `controller.type_text("#search", "hello", delay=0.1)`
- **THEN** 系统逐字符输入并触发 keydown/keyup/input 事件

### Requirement: 内容提取
系统 SHALL 支持通过 CSS 选择器提取元素的文本、属性、HTML 等结构化数据。

#### Scenario: 提取文本
- **WHEN** 调用 `controller.extract("h1", attribute="text")`
- **THEN** 系统返回匹配元素的文本内容列表

#### Scenario: 提取 HTML
- **WHEN** 调用 `controller.extract("div.content", attribute="html")`
- **THEN** 系统返回匹配元素的 innerHTML 列表

#### Scenario: 提取全页 DOM 树
- **WHEN** 调用 `controller.get_dom_json()`
- **THEN** 系统返回序列化为 JSON 的页面 DOM 结构

### Requirement: Cookie 管理
系统 SHALL 支持获取和设置 Cookie。

#### Scenario: 设置 Cookie
- **WHEN** 调用 `controller.set_cookies({"sessionid": "abc123"})`
- **THEN** 系统通过 JS 注入 Cookie 到当前页面

#### Scenario: 获取 Cookie
- **WHEN** 调用 `controller.get_cookies()`
- **THEN** 系统返回当前页面的所有 Cookie

### Requirement: 对话框拦截
系统 SHALL 支持拦截原生 alert/confirm/prompt 对话框，并自动回复。

#### Scenario: 拦截并捕获 alert
- **WHEN** 调用 `controller.override_dialogs()` 后页面触发 `alert("Hello")`
- **THEN** 系统捕获对话框消息，不弹出原生对话框

#### Scenario: 自动回复 confirm
- **WHEN** 调用 `controller.override_dialogs(auto_confirm=True)` 后页面触发 `confirm("确定?")`
- **THEN** 系统自动返回 true，并记录对话框消息

### Requirement: 等待元素
系统 SHALL 支持等待指定 CSS 选择器匹配的元素出现。

#### Scenario: 等待元素出现
- **WHEN** 调用 `controller.wait_for_selector(".dashboard", timeout=10)`
- **THEN** 系统轮询直到元素出现或超时抛出异常

### Requirement: 高级场景封装
系统 SHALL 提供登录和搜索两个高级场景的封装方法。

#### Scenario: 自动登录
- **WHEN** 调用 `controller.login("https://example.com/login", "user", "pass", "#login-btn")`
- **THEN** 系统导航到登录页，填写用户名和密码，点击登录按钮

#### Scenario: 自动搜索
- **WHEN** 调用 `controller.search("https://google.com", "pywebview", "input[name='q']", "input[type='submit']")`
- **THEN** 系统导航到搜索页，输入关键词，触发搜索，等待结果加载

### Requirement: CLI 命令行接口
系统 SHALL 提供命令行接口，支持单命令执行和 YAML 剧本执行。

#### Scenario: 单命令执行
- **WHEN** 执行 `browser-cli goto "https://example.com"`
- **THEN** 系统启动控制器，导航到目标 URL，输出结果后退出

#### Scenario: 剧本执行
- **WHEN** 执行 `browser-cli run --playbook scenario.yaml`
- **THEN** 系统按顺序执行剧本中的每个动作，输出执行日志

### Requirement: 截图
系统 SHALL 支持对当前页面进行截图并保存为图片文件。

#### Scenario: 截图保存
- **WHEN** 调用 `controller.screenshot("output.png")`
- **THEN** 系统通过 JS 注入 html2canvas 或使用平台原生方法截取页面图像并保存

### Requirement: 资源清理
系统 SHALL 在退出时安全清理资源，关闭所有窗口。

#### Scenario: 正常退出
- **WHEN** 调用 `controller.close()`
- **THEN** 系统销毁所有窗口，清理 Cookie 和缓存，释放资源