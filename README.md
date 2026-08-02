#智能体-浏览器自动化工具包

## 第一章 这是什么？——  一个会自己动手的"浏览器助手"

### 1.1 一句话说清

**本项目是一个基于真实浏览器窗口的自动化工具包**：它能像人一样打开浏览器、输入网址、点击按钮、填写表单、翻页滚动、截图保存、提取数据，而且这一切都可以由你写好的"指令"或"脚本"自动完成。

### 1.2 用生活化的方式理解它

想象你雇了一位**"看得见屏幕的机器人秘书"**，它有四样东西：

| 部件 | 对应项目里的东西 | 干什么用 |
| --- | --- | --- |
| 眼睛 | 页面读取与提取功能 | 看清网页上有什么：标题、链接、表格、图片、文字 |
| 手 | 自动化动作功能 | 点击按钮、输入文字、勾选选项、滚动页面、上传文件 |
| 大脑 | CLI 命令 + 剧本系统 | 记住你的指令，按顺序一步步执行，还能判断"等页面加载完再操作" |
| 遥控器 | Web 控制面板 | 打开一个网页界面，远程指挥浏览器干活，还能看每步的结果 |

关键区别在于：**这个机器人用的是"真浏览器窗口"**——你在屏幕上能亲眼看到它在做什么，就像有人坐在电脑前替你操作网页一样。网页无法分辨这是真人还是程序，因此能处理的网站范围远大于普通的"爬虫"（爬虫只拿 HTML 源码，遇到 JavaScript 动态加载的内容就抓瞎）。

### 1.3 它最适合干什么

- **重复性劳动**：每天填同一个表单、查同一批数据、登录同一批网站。
- **动态网页处理**：需要等待异步加载、点击展开、滚动加载的"现代网页"。
- **批量任务**：几十上百个 URL 逐个打开、提取、截图。
- **可视化操作**：需要亲眼确认每一步结果的场景（如打开直播间、盯盘监控）。

### 1.4 三种使用方式（由浅入深）

1. **一条命令**：在命令行敲一句指令，比如"打开这个网址""提取这个标题"。
2. **一串命令**：把多个操作写进一个 YAML 剧本文件，一次执行到底。
3. **网页遥控**：启动 Web 控制面板，在浏览器页面里指挥多窗口同时干活。

---

## 第二章 项目构成

本项目分为两层：

| 层次 | 内容 | 说明 |
| --- | --- | --- |
| 底层 | pywebview 社区定制版（`webview/`、`interop/`、`vendor/`） | 跨平台桌面浏览器引擎封装：Windows 用 Edge WebView2，macOS 用 WKWebView，Linux 用 GTK3/WebKit2 或 CEF |
| 应用层 | browser_cli 工具包（`browser_cli/`） | 面向日常使用的自动化工具：CLI 命令、动作库、提取器、多窗口管理、剧本执行、Web 控制面板 |

browser_cli 内部模块划分：

```
browser_cli/
├── cli.py          # 25 个 CLI 命令入口
├── controller.py   # BrowserController / MultiWindowManager / WindowPool 三个核心类
├── patches.py      # 多窗口 NavigationCompleted 事件补偿补丁
├── actions.py      # 20 个自动化动作方法（fill 含防覆盖/防隐藏逻辑）
├── parser.py       # 6 个数据提取方法
├── webui.py        # Flask Web 控制面板（15 个 API 端点）
├── templates/      # 控制面板前端页面
└── examples/       # YAML 剧本示例
```

---

## 第三章 功能总览：25 个 CLI 命令

所有命令通过 `python -m browser_cli.cli <命令>` 调用，按用途分为 8 类：

### 3.1 导航与提取

| 命令 | 功能 | 示例 |
| --- | --- | --- |
| `goto` | 导航到指定 URL | `goto "https://example.com"` |
| `extract` | CSS 选择器提取内容 | `extract "h1" --url "..." --format json` |
| `snapshot` | 输出页面 DOM 文本快照（标题/URL/可见文本/表单信息） | `snapshot --url "https://example.com"` |

### 3.2 表单与交互

| 命令 | 功能 | 示例 |
| --- | --- | --- |
| `fill-form` | 一次填写多个表单字段 | `fill-form --url "..." --field "input[name=q]:关键词"` |
| `fill-steps` | 分步执行（fill/click/wait/type/select/extract） | `fill-steps --url "..." --step "fill:#name:张三"` |
| `hover` | 鼠标悬停，触发 mouseenter/mouseover | `hover "a" --url "..."` |
| `scroll-to` | 滚动到指定元素 | `scroll-to "footer" --url "..."` |
| `scroll-down` | 向下滚动指定像素 | `scroll-down 500 --url "..."` |
| `press` | 模拟按键（Enter/Tab/Escape/ArrowDown 等） | `press "Enter" --url "..."` |
| `upload` | 触发文件上传对话框（打开系统文件选择框） | `upload "input[type=file]" ./file.pdf --url "..."` |

### 3.3 搜索与登录

| 命令 | 功能 | 示例 |
| --- | --- | --- |
| `search` | 打开搜索引擎，输入关键词搜索并提取结果 | `search --url "https://bing.com" --query "pywebview" --input "input[name=q]"` |
| `login` | 导航到登录页，自动填用户名密码并提交，可选提取登录后内容 | `login --url "..." --username "user" --password "pass"` |

### 3.4 截图与导出

| 命令 | 功能 | 示例 |
| --- | --- | --- |
| `screenshot` | 页面或指定元素截图 | `screenshot --url "..." -o page.png --selector ".main"` |
| `pdf` | 打开浏览器打印对话框，手动另存为 PDF | `pdf output.pdf --url "..."` |

### 3.5 录制与回放

| 命令 | 功能 | 示例 |
| --- | --- | --- |
| `record` | 交互式录制你的操作，保存为 JSON 脚本 | `record --url "..." -o script.json` |
| `replay` | 回放录制的脚本，可调速 | `replay script.json --speed 1.5` |

### 3.6 等待与同步

| 命令 | 功能 | 示例 |
| --- | --- | --- |
| `wait-for-timeout` | 等待指定毫秒数 | `wait-for-timeout 3000` |
| `wait-for-url` | 等待 URL 匹配 glob 模式（如 `**/success`） | `wait-for-url "**/success" --url "..."` |

### 3.7 多窗口与批量

| 命令 | 功能 | 示例 |
| --- | --- | --- |
| `multi-window` | 同时打开多个浏览器窗口，保持一段时间 | `multi-window --urls "url1,url2" --stay-open 30` |
| `batch` | 批量处理文件中的 URL 列表（每行一个） | `batch urls.txt --extract "h1" -o result.json` |
| `webui` | 启动 Web 控制面板 | `webui --port 5000 --max-windows 5` |

### 3.8 环境与诊断

| 命令 | 功能 | 示例 |
| --- | --- | --- |
| `doctor` | 系统环境诊断：检查 Python、pywebview、WebView2 等依赖 | `doctor` |
| `browsers` | 列出系统已安装的浏览器 | `browsers` |
| `set-cookies` | 设置 Cookie（解析 `name=value` 格式） | `set-cookies --cookie "name=value" --url "..."` |
| `run` | 执行 YAML 自动化剧本 | `run --playbook scenario.yaml` |

---

## 第四章 自动化动作能力（20 个动作方法）

`actions.py` 提供浏览器内所有"动手"操作，是各命令与剧本的公共执行层：

| 类别 | 方法 | 说明 |
| --- | --- | --- |
| 基础交互 | `click` / `hover` / `press_key` | 点击、悬停、按键 |
| 输入 | `fill` / `type_text` | 填写/逐字输入文本 |
| 表单 | `submit_form` / `select_option` / `upload_file` | 提交表单、选择下拉项、上传文件 |
| 提取 | `extract` / `get_dom_json` | 按选择器提取 / 导出 DOM 结构 |
| 数据 | `set_cookies` / `get_cookies` | 设置/读取 Cookie |
| 对话框 | `override_dialogs` / `get_dialog_messages` | 接管 alert/confirm/prompt 并记录消息 |
| 截图 | `screenshot` / `screenshot_element` | 整页/元素截图 |
| 脚本 | `exec_js_async` | 执行任意 JavaScript 并取回结果 |
| 滚动 | `scroll_to_selector` / `scroll_by` | 滚动到元素 / 按像素滚动 |
| 生命周期 | `close` | 关闭窗口 |

### 4.1 fill 的两大实战强化（本项目的招牌能力）

普通自动化工具填表时，遇到"值被清空""元素看不见"就失败。本项目针对真实网站的两大坑做了内置处理：

- **防覆盖**：SPA 网站（如 Vue/React 应用）在页面初始化时会异步重写输入框的值，填完就被清空。`fill` 填写后自动验证值是否保留，被覆盖则自动重填（默认重试 6 次）。
- **防隐藏**：部分网站的搜索框/表单外层容器被 `display:none` 隐藏（如百度首页的 virtual-form 虚拟表单），普通点击根本点不到。`fill` 会自动检测并临时恢复隐藏的祖先容器，填完再还原。

### 4.2 对话框接管

网站弹出的 alert/confirm/prompt 会阻塞自动化流程。动作层可预先接管这些对话框，自动确认并记录弹出的消息内容，让流程不中断。

---

## 第五章 数据提取能力（6 个提取方法）

`parser.py` 提供结构化数据提取：

| 方法 | 提取内容 |
| --- | --- |
| `get_links` | 页面所有链接（含文本与 href） |
| `get_tables` | 表格数据（转为结构化行/列） |
| `get_all_text` | 页面全部可见文本 |
| `get_meta_tags` | meta 标签（关键词、描述等） |
| `get_forms` | 表单结构（字段、类型、默认值） |
| `get_images` | 图片列表（URL 与 alt 文本） |

配合 `extract` 命令的 **`--wait-selector` / `--wait-dynamic`** 参数，可以等待动态内容出现后再提取（如搜索结果、异步加载的列表），解决"提取时内容还没加载出来"的经典问题。

---

## 第六章 多窗口管理

`controller.py` 提供三个核心类，支持同时管理多个独立浏览器窗口：

| 类 | 职责 |
| --- | --- |
| `BrowserController` | 单窗口控制器：导航、执行 JS、等待加载、提取 URL |
| `MultiWindowManager` | 多窗口总管：批量打开 URL、对指定窗口执行操作、关闭/查询全部窗口 |
| `WindowPool` | 窗口池：预建 N 个窗口槽位，按需激活切换、查询空闲槽位 |

**多窗口能力**：每个窗口拥有独立的会话与页面状态，可同时打开多个直播间、多个后台系统，互不干扰。配合 `webui` 控制面板可直观地切换、查看、操作每个窗口。

**可靠性保障**：pywebview 6.2.1 存在多窗口下 `NavigationCompleted` 事件不派发的已知问题（窗口列表会一直显示"加载中"、切换卡死）。项目内置 `patches.py` 自动补偿该事件，保证多窗口场景稳定可用。

---

## 第七章 剧本系统（YAML 剧本 + 录制回放）

### 7.1 YAML 剧本（`run` 命令）

把一系列操作写成人类可读的 YAML 文件，一次执行：

```yaml
name: "表单提交与提取演示"
steps:
  - action: goto
    url: "https://httpbin.org/forms/post"
  - action: wait
    selector: "form"
    timeout: 10
  - action: fill
    selector: 'input[name="custname"]'
    value: "张三"
  - action: click
    selector: 'input[name="size"][value="medium"]'
  - action: submit
    ...
  - action: extract
    selector: ".result"
```

支持的步骤动作：`goto` / `wait` / `fill` / `click` / `type` / `select` / `extract` / `screenshot` 等。示例见 `browser_cli/examples/scenario.yaml`。

### 7.2 录制与回放（`record` / `replay`）

不想手写剧本？启动 `record` 后你在浏览器里的真实操作会被录制为 JSON 脚本，之后用 `replay` 原速或加速回放，实现"操作一次，永久复用"。

### 7.3 批量执行（`batch`）

把几十个 URL 写进文本文件，一条命令逐个打开、提取、汇总输出到 JSON，适合批量采集类任务。

---

## 第八章 Web 控制面板（webui）

`webui` 命令启动一个 Flask 服务，在浏览器里可视化操控整个自动化工具：

```
python -m browser_cli.cli webui --port 8125 --max-windows 3
```

启动后访问 `http://127.0.0.1:8125`（带 token 校验），面板提供 15 个 API 端点：

| 端点 | 功能 |
| --- | --- |
| `GET /` | 控制面板页面 |
| `GET /api/windows` | 列出所有窗口及状态 |
| `POST /api/windows/switch` | 切换活动窗口 |
| `GET /api/status` | 当前窗口状态（标题/URL） |
| `POST /api/goto` | 导航到 URL |
| `POST /api/extract` | 按选择器提取内容 |
| `POST /api/exec_js` | 执行任意 JavaScript |
| `POST /api/screenshot` | 窗口截图 |
| `POST /api/fill` | 填写表单字段 |
| `POST /api/click` | 点击元素 |
| `POST /api/links` | 提取页面链接 |
| `POST /api/login` | 自动登录 |
| `POST /api/search` | 搜索并提取结果 |
| `POST /api/fill-steps` | 分步执行操作链 |
| `POST /api/stop` | 停止服务 |

所有 API 通过 `X-Browser-CLI-Token` 请求头鉴权，防止局域网内被他人调用。

---

## 第九章 工程可靠性与排障

| 特性 | 说明 |
| --- | --- |
| `patches.py` | 补偿 pywebview 6.2.1 多窗口 NavigationCompleted 事件丢失问题（窗口列表/切换/导航卡死） |
| `scripts/run_visible.py` | 强制窗口可见启动器：解决从 SW_HIDE 启动环境（如某些 IDE/守护进程）继承隐藏属性导致"窗口看不见"的问题 |
| `doctor` 命令 | 一键诊断 Python、pywebview、WebView2 等依赖是否就绪 |
| 路径安全 | 输出路径规范化，拒绝 `..` 路径遍历逃逸 |
| 排障文档 | `browser_cli/TROUBLESHOOTING.md` 沉淀真实环境踩坑：动态渲染定位五步法、SPA 覆盖、隐藏表单、多窗口卡死等 |

---

## 第十章 快速上手

### 环境要求

- Python >= 3.10
- Windows：Edge WebView2 Runtime（Windows 10/11 自带）
- macOS：系统自带 WKWebView
- Linux：GTK3 + WebKit2 或 CEF

### 安装

```bash
pip install -e ./browser_cli
```

### 验证环境

```bash
python -m browser_cli.cli doctor
```

### 5 分钟体验

```bash
# 打开一个网页
python -m browser_cli.cli goto --url "https://example.com"

# 提取标题（JSON 输出）
python -m browser_cli.cli extract "title" --url "https://example.com" --format json

# 自动搜索并提取结果
python -m browser_cli.cli search --url "https://www.bing.com" \
  --query "pywebview github" --input "input[name=q]" \
  --extract-result "#b_results h2" --wait-result 3

# 批量提取多个页面
python -m browser_cli.cli batch urls.txt --extract "h1" -o results.json

# 启动 Web 控制面板
python -m browser_cli.cli webui --port 8000 --max-windows 5
```

---

## 第十一章 典型应用场景

| 场景 | 用法 |
| --- | --- |
| 打开直播间/视频页面 | `goto` 或 webui 面板导航，多窗口可同时开多个直播间 |
| 表单批量填报 | `fill-form` / `fill-steps` / YAML 剧本 |
| 登录后抓数据 | `login` 自动登录，再 `extract` / `snapshot` 提取 |
| 网站内容监控 | `batch` + 定时执行，对比提取结果 |
| 自动化测试辅助 | `record` 录制操作 + `replay` 回放 + 截图留证 |
| 数据采集 | `batch` 批量提取 + `parser` 结构化表格/链接/图片 |
