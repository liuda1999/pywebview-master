# browser-cli

> 基于 [pywebview](https://github.com/r0x0r/pywebview) 社区定制版的浏览器自动化 CLI 工具。  
> 无需 Selenium / Playwright，利用系统原生 WebView 完成页面导航、表单填写、数据提取、搜索、登录、截图、录制回放等自动化任务。

---

## 1. 项目简介

`browser-cli` 是 pywebview 社区定制版的核心组件，提供 25 个命令行工具，让你在终端中驱动真实的浏览器内核（Windows: Edge WebView2，macOS: WKWebView，Linux: GTK WebKit / CEF）执行自动化任务。

**核心能力：**

| 类别 | 功能 |
|------|------|
| 页面导航 | goto — 打开任意 URL 并等待加载完成 |
| 数据提取 | extract — CSS 选择器提取，支持 JSON/CSV/TXT 输出 |
| 数据过滤 | parser 支持正则过滤链接、表格、文本、Meta、表单、图片 |
| 表单自动化 | fill-form — 填写多个字段；fill-steps — 分步执行复杂操作 |
| 搜索操作 | search — 导航到搜索页，输入关键词并提交，支持结果提取 |
| 登录操作 | login — 自动填写用户名密码并提交，可选提取登录后内容 |
| 交互操作 | hover、scroll-to、scroll-down、press — 鼠标悬停、滚动、键盘按键 |
| 文件上传 | upload — 触发文件输入框 |
| 截图 | screenshot — 全页截图/元素截图，保存为 PNG |
| 快照 | snapshot — 输出页面 DOM 文本快照 |
| 录制回放 | record — 交互式录制；replay — 回放 JSON 脚本 |
| 多窗口 | multi-window — 同时打开多个独立窗口 |
| 批量执行 | batch — 从文件读取 URL 列表批量处理 |
| PDF 导出 | pdf — 通过浏览器打印 API 导出 PDF |
| Web 控制面板 | webui — Flask + 多窗口标签页可视化操控 |
| Cookie 管理 | set-cookies — 设置 Cookie |
| 系统诊断 | doctor — 检测 Python/WebView2/CEF/网络环境 |
| 浏览器列表 | browsers — 列出系统已安装浏览器 |
| YAML 剧本 | run — 通过 YAML 文件批量执行自动化步骤 |
| 环境配置 | BROWSER_CLI_* 环境变量覆盖默认配置 |
| CEF 回退 | WebView2 不可用时自动回退到 CEF 引擎 |

---

## 2. 安装

### 环境要求

- Python >= 3.10
- Windows: Edge WebView2 Runtime（Windows 10/11 自带）
- macOS: 系统自带 WKWebView
- Linux: GTK3 + WebKit2 或 CEF

### 安装步骤

```bash
# 在 pywebview 社区定制版根目录执行
pip install -e ./browser_cli
```

### 系统诊断

```bash
python -m browser_cli.cli doctor
```

---

## 3. 全部 CLI 命令

### 3.1 导航与提取

| 命令 | 说明 | 示例 |
|------|------|------|
| `goto` | 导航到 URL | `goto "https://example.com"` |
| `extract` | CSS 选择器提取 | `extract "h1" --url "..." --format json` |
| `snapshot` | DOM 文本快照 | `snapshot --url "https://example.com"` |

### 3.2 表单与交互

| 命令 | 说明 | 示例 |
|------|------|------|
| `fill-form` | 填写多个表单字段 | `fill-form --url "..." --field "input[name=q]:关键词"` |
| `fill-steps` | 分步执行自动化 | `fill-steps --url "..." --step "fill:#name:张三" --step "click:button"` |
| `hover` | 鼠标悬停 | `hover "a" --url "https://example.com"` |
| `scroll-to` | 滚动到元素 | `scroll-to "footer" --url "..."` |
| `scroll-down` | 向下滚动像素 | `scroll-down 500 --url "..."` |
| `press` | 按键操作 | `press "Enter" --url "..."` |
| `upload` | 打开文件选择对话框（需手动选文件） | `upload "input[type=file]" ./file.pdf --url "..."` |

### 3.3 搜索与登录

| 命令 | 说明 | 示例 |
|------|------|------|
| `search` | 搜索并提取结果 | `search --url "https://bing.com" --query "pywebview" --input "input[name=q]"` |
| `login` | 自动登录 | `login --url "..." --username "user" --password "pass"` |

### 3.4 截图与导出

| 命令 | 说明 | 示例 |
|------|------|------|
| `screenshot` | 页面/元素截图 | `screenshot --url "..." -o page.png --selector ".main"` |
| `pdf` | 打开打印对话框（手动另存为 PDF） | `pdf output.pdf --url "..."` |

### 3.5 录制与回放

| 命令 | 说明 | 示例 |
|------|------|------|
| `record` | 录制交互操作 | `record --url "..." -o script.json` |
| `replay` | 回放脚本 | `replay script.json --speed 1.5` |

### 3.6 等待与同步

| 命令 | 说明 | 示例 |
|------|------|------|
| `wait-for-timeout` | 等待毫秒数 | `wait-for-timeout 3000` |
| `wait-for-url` | 等待 URL 匹配 | `wait-for-url "**/success" --url "https://example.com"` |

### 3.7 多窗口与批量

| 命令 | 说明 | 示例 |
|------|------|------|
| `multi-window` | 同时打开多个窗口 | `multi-window --urls "url1,url2" --stay-open 30` |
| `batch` | 批量处理 URL 列表 | `batch urls.txt --extract "h1" -o result.json` |
| `webui` | Web 控制面板 | `webui --port 5000 --max-windows 5` |

### 3.8 环境与诊断

| 命令 | 说明 | 示例 |
|------|------|------|
| `doctor` | 系统环境诊断 | `doctor` |
| `browsers` | 列出浏览器 | `browsers` |
| `set-cookies` | 设置 Cookie | `set-cookies --cookie "name=value" --url "..."` |
| `run` | 执行 YAML 剧本 | `run --playbook scenario.yaml` |

---

## 4. 使用示例

### 4.1 基础提取

```bash
# 提取页面标题
python -m browser_cli.cli extract "title" --url "https://example.com"

# JSON 格式输出
python -m browser_cli.cli extract "h1,p" --url "https://example.com" --format json

# 动态内容等待
python -m browser_cli.cli extract ".result" --url "https://spa-site.com" --wait-selector ".result" --wait-dynamic 3
```

### 4.2 表单自动化

```bash
# 单次多字段填写
python -m browser_cli.cli fill-form --url "https://example.com/form" \
  --field "input[name=name]:张三" --field "input[name=email]:test@test.com"

# 多步操作
python -m browser_cli.cli fill-steps --url "https://example.com/form" \
  --step "fill:#name:张三" \
  --step "fill:#email:test@test.com" \
  --step "select:#country:CN" \
  --step "click:button[type=submit]" \
  --step "extract:.success-message"
```

### 4.3 搜索自动化

```bash
python -m browser_cli.cli search --url "https://www.bing.com" \
  --query "pywebview github" --input "input[name=q]" \
  --extract-result "#b_results h2" --wait-result 3
```

### 4.4 批量处理

```bash
# 创建 URL 列表
echo https://example.com > urls.txt
echo https://httpbin.org/get >> urls.txt

# 批量提取
python -m browser_cli.cli batch urls.txt --extract "h1" -o results.json
```

### 4.5 Web 控制面板

```bash
# 启动 Web UI（默认 5 个窗口）
python -m browser_cli.cli webui

# 自定义端口和窗口数
python -m browser_cli.cli webui --port 8000 --max-windows 10
```

---

## 5. 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BROWSER_CLI_TIMEOUT` | 30 | 默认操作超时（秒） |
| `BROWSER_CLI_WIDTH` | 1024 | 默认窗口宽度 |
| `BROWSER_CLI_HEIGHT` | 768 | 默认窗口高度 |
| `BROWSER_CLI_HEADLESS` | 0 | 设为 1 启用无头模式（默认隐藏窗口） |
| `BROWSER_CLI_GUI` | auto | 手动指定 GUI 后端 (cef/edgechromium) |
| `BROWSER_CLI_IGNORE_SSL` | 1 | 设为 0 关闭 SSL 证书校验忽略（恢复证书校验） |
| `BROWSER_CLI_WEBUI_TOKEN` | 随机 | webui 访问令牌；设置后使用固定令牌，未设置时自动生成随机令牌 |

---

## 6. 行为与安全说明

- **退出码**：所有命令失败时退出码为 1（此前为 0，静默失败）。
  record/replay/batch 在部分步骤失败时仍会继续并正常退出。
- **无头模式**：`BROWSER_CLI_HEADLESS=1` 时所有命令默认隐藏窗口；
  `record`、`pdf`、`upload` 需要交互，强制使用可见窗口。
- **SSL 校验**：默认忽略证书错误（便于访问自签名/内网站点），
  如需严格校验请设 `BROWSER_CLI_IGNORE_SSL=0`。
- **webui 访问控制**：控制面板绑定 127.0.0.1 并携带随机访问令牌，
  拒绝非回环 Host 请求；令牌附加在自动打开的 URL 中，请勿泄露。
- **输出路径**：`--output/-o` 拒绝包含 `..` 的相对路径（防路径遍历）。
- **已知限制**：`pdf` 与 `upload` 受 WebView2 安全限制无法编程化完成，
  只能打开系统对话框由用户手动操作；`file://` 协议 URL 可用于本地调试。

---

## 7. GUI 后端

检测顺序：`BROWSER_CLI_GUI` 环境变量 → WebView2 → CEF → pywebview 自动

- **Windows**: 优先使用 Edge WebView2，不可用时回退到 CEF
- **macOS**: 使用系统 WKWebView
- **Linux**: GTK WebKit 或 CEF

---

## 8. 与 Selenium / Playwright 的区别

| 特性 | browser-cli | Selenium / Playwright |
|------|-------------|----------------------|
| 浏览器驱动 | 系统原生 WebView | 需额外下载 WebDriver |
| 安装复杂度 | `pip install` + 系统 WebView | 需搭配浏览器 & Driver |
| 包体积 | 轻量 | 较重 |
| 多标签页 | 支持（多窗口） | 支持 |
| 设备仿真 | 不支持 | 支持 |
| 网络拦截 | 不支持 | 支持 |
| 并行执行 | 单进程 | 多进程 |
| 适用场景 | 桌面自动化、数据采集、表单填写 | 完整 E2E 测试 |

---

## 9. 项目结构

```
pywebview-master/            # 项目根目录
├── browser_cli/
│   ├── cli.py          # 25 个 CLI 命令入口
│   ├── controller.py   # BrowserController / MultiWindowManager / WindowPool
│   ├── patches.py      # 多窗口 NavigationCompleted 事件补偿补丁（见 TROUBLESHOOTING 1.4）
│   ├── actions.py      # 23 个自动化动作方法（fill 含防覆盖/防隐藏逻辑）
│   ├── parser.py       # 9 个数据提取/过滤方法
│   ├── webui.py        # Flask Web 控制面板 API
│   ├── templates/
│   │   └── index.html  # Web 控制面板前端
│   ├── examples/
│   │   └── scenario.yaml  # YAML 剧本示例
│   └── TROUBLESHOOTING.md  # 常见问题与排障经验（动态渲染网页定位法）
└── scripts/
    └── run_visible.py  # 强制窗口可见启动器（SW_HIDE 启动环境用）
```

## 10. 常见问题与排障经验

遇到“窗口看不见 / 表单不显示 / 填了值却看不到”类问题，先读
[TROUBLESHOOTING.md](TROUBLESHOOTING.md)，其中沉淀了真实环境踩坑与定位方法：

| 症状 | 根因 | 解决 |
| --- | --- | --- |
| 窗口创建了但桌面不可见 | 启动环境 SW_HIDE 继承 | `python scripts/run_visible.py <命令>` 包装启动 |
| fill 返回成功但值被清空 | SPA 异步初始化覆盖 | `actions.fill` 内置验证+重填（retries=6） |
| 搜索框/表单不可见 | 网站隐藏表单（如百度 virtual-form） | `actions.fill` 内置恢复隐藏祖先容器 |
| 元素在 DOM 但 rect 为 0 | 祖先链 display:none | 按 TROUBLESHOOTING 第 2 节五步定位 |

## 11. 许可

BSD Licensed — 基于 pywebview 社区定制版