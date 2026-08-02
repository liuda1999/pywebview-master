# Tasks

- [x] Task 1: 项目初始化
  - [x] 创建 `browser_cli/` 项目目录结构
  - [x] 编写 `requirements.txt`（依赖：pywebview, click, pyyaml, pillow, beautifulsoup4）
  - [x] 编写 `setup.py` / `pyproject.toml`（入口点 `browser-cli`）

- [x] Task 2: 实现 BrowserController 核心控制器
  - [x] 实现 `browser_cli/controller.py` — `BrowserController` 类
  - [x] 封装窗口创建：`_create_window(hidden=True)` 配置 settings 和 _state
  - [x] 封装同步 JS 执行：`exec_js(script)` 使用 threading.Event 等待回调
  - [x] 封装页面加载等待：`wait_loaded(timeout)` 监听 events.loaded
  - [x] 封装资源清理：`close()` 销毁窗口

- [x] Task 3: 实现 AutomationActions 自动化动作模块
  - [x] 实现 `browser_cli/actions.py` — `AutomationActions` 类
  - [x] 实现 `goto(url)` 和 `load_html(html)`
  - [x] 实现 `click(selector)` 元素点击
  - [x] 实现 `fill(selector, value)` 表单填写（含 input/change 事件触发）
  - [x] 实现 `type_text(selector, text, delay)` 逐字符输入
  - [x] 实现 `extract(selector, attribute)` 内容提取
  - [x] 实现 `wait_for_selector(selector, timeout)` 等待元素
  - [x] 实现 `set_cookies(cookies_dict)` 和 `get_cookies()`
  - [x] 实现 `override_dialogs(auto_confirm)` 对话框拦截
  - [x] 实现 `screenshot(path)` 页面截图
  - [x] 实现 `login(url, username, password, submit_selector)` 登录场景
  - [x] 实现 `search(url, query, input_selector, submit_selector)` 搜索场景
  - [x] 实现 `get_dom_json()` 获取序列化 DOM
  - [x] 实现 `submit_form(form_selector)` 表单提交

- [x] Task 4: 实现 ContentParser 内容解析模块
  - [x] 实现 `browser_cli/parser.py` — `ContentParser` 类
  - [x] 实现 `get_links()` 提取所有链接
  - [x] 实现 `get_tables(selector)` 提取表格数据
  - [x] 实现 `filter_by_regex(elements, pattern)` 正则过滤
  - [x] 实现 `save_to_file(data, format, path)` 保存为 CSV/JSON/TXT

- [x] Task 5: 实现 CLI 命令行接口
  - [x] 实现 `browser_cli/cli.py` — 使用 click 构建命令树
  - [x] 实现 `goto` 子命令
  - [x] 实现 `extract` 子命令
  - [x] 实现 `fill-form` 子命令
  - [x] 实现 `search` 子命令
  - [x] 实现 `set-cookies` 子命令
  - [x] 实现 `screenshot` 子命令
  - [x] 实现 `run` 子命令（YAML 剧本执行）
  - [x] 实现 `PlaybookRunner` 剧本执行器

- [x] Task 6: 编写示例剧本和 README
  - [x] 编写 `examples/scenario.yaml` 示例剧本
  - [x] 编写 `README.md` 使用说明文档

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 2
- Task 4 依赖 Task 2
- Task 5 依赖 Task 3 和 Task 4
- Task 6 依赖 Task 5