<p align='center'><img src='assets/logo.png' width=480 alt='pywebview logo'/></p>

<p align='center'>
  <b>⚠️ 社区定制版 (Community Edition)</b><br>
  此版本基于 pywebview 官方源码进行了二次开发，集成了 <code>browser_cli</code> 浏览器自动化工具。<br>
  官方原版请访问: <a href="https://github.com/r0x0r/pywebview">github.com/r0x0r/pywebview</a>
</p>

---

_pywebview_ 是一个轻量级原生 webview 包装器，可在原生 GUI 窗口中显示 HTML 内容。它将 Web 技术的力量引入桌面应用，隐藏了 GUI 基于浏览器的事实。_pywebview_ 自带内置 HTTP 服务器、Python DOM 支持和窗口管理功能。

_pywebview_ 支持 Windows、macOS、Linux（GTK 或 QT）和 Android。Windows 使用 WinForms/WebView2，macOS 使用 Cocoa，Linux 使用 QT 或 GTK。如果选择冻结应用程序，_pywebview_ 不会捆绑重量级 GUI 工具包或 Web 渲染器，可执行文件保持小巧。

_pywebview_ 由 [Roman Sirokov](https://github.com/r0x0r/) 创建。

---

## 社区定制版特性

本社区定制版在 pywebview 基础上扩展了 **browser_cli** 浏览器自动化工具套件：

### browser_cli — 命令行浏览器自动化

- **25 个 CLI 命令** — goto, extract, fill-form, fill-steps, search, login, screenshot, snapshot, hover, scroll-to, scroll-down, press, upload, record, replay, batch, pdf, multi-window, webui, doctor, browsers, wait-for-timeout, wait-for-url, set-cookies, run
- **多窗口管理** — 同时打开多个独立 WebView 窗口，每个可独立导航
- **深度网页交互** — 点击、悬停、输入、按键、滚动、上传、下拉选择
- **数据提取与过滤** — CSS 选择器提取 + 正则过滤，支持 JSON/CSV/TXT 输出
- **多步表单自动化** — fill-steps 支持按步骤执行 fill/click/wait/type/select/extract/hover/scroll/press/upload/snapshot
- **登录自动化** — 自动填写用户名密码并提交
- **搜索自动化** — 搜索引擎关键词搜索 + 结果提取
- **录制与回放** — record 录制用户操作，replay 回放 JSON 脚本
- **Web 控制面板** — Flask + 多窗口标签页 UI，可视化操控浏览器
- **批量执行** — 从文件读取 URL 列表批量处理
- **系统诊断** — doctor 检测 Python/WebView2/CEF 环境
- **CEF 引擎回退** — WebView2 不可用时自动回退到 CEF 引擎
- **PDF 打印** — 打开浏览器打印对话框，由用户手动另存为 PDF（WebView2 不支持编程化导出）

### 快速开始

```bash
# 安装
pip install -e ./browser_cli

# 导航到页面
python -m browser_cli.cli goto "https://example.com"

# 提取内容
python -m browser_cli.cli extract "h1" --url "https://example.com" --format json

# 多步表单填写
python -m browser_cli.cli fill-steps --url "https://example.com/form" \
  --step "fill:#name:张三" --step "fill:#email:test@test.com" --step "click:button[type=submit]"

# 启动 Web 控制面板
python -m browser_cli.cli webui --max-windows 5

# 系统诊断
python -m browser_cli.cli doctor
```

详见 [browser_cli/README.md](browser_cli/README.md)

---

## 原始 pywebview 安装

``` bash
pip install pywebview
```

_可能需要额外库。详见 [安装指南](https://pywebview.flowrl.com/guide/installation)。_

## Hello world

``` python
import webview
webview.create_window('Hello world', 'https://pywebview.flowrl.com/hello')
webview.start()
```

更多用法示例请参考 [examples](examples/) 目录。

## 致谢

此社区定制版在 pywebview 官方源码基础上开发，感谢 Roman Sirokov 和所有 pywebview 贡献者。
