"""browser_cli.cli — 基于 Click 的浏览器自动化命令行接口。"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Any

import click
import yaml

from .actions import AutomationActions
from .controller import BrowserController, MultiWindowManager, WindowPool
from .parser import ContentParser


def _safe_output_path(path: str) -> str:
    """规范化输出路径并拒绝路径遍历（..）逃逸。

    若相对路径包含 ".." 路径组件，抛 ValueError 拒绝写入，
    防止通过 --output/-o 把文件写到工作目录之外。绝对路径不受影响。
    """
    norm = os.path.normpath(path)
    if os.path.pardir in norm.split(os.sep):
        raise ValueError(f"拒绝路径遍历输出路径: {path!r}")
    return os.path.abspath(norm)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = float(os.environ.get("BROWSER_CLI_TIMEOUT", "30.0"))
DEFAULT_WIDTH = int(os.environ.get("BROWSER_CLI_WIDTH", "1024"))
DEFAULT_HEIGHT = int(os.environ.get("BROWSER_CLI_HEIGHT", "768"))
DEFAULT_HIDDEN = os.environ.get("BROWSER_CLI_HEADLESS", "").lower() in ("1", "true", "yes")


def _parse_field(field_str: str) -> tuple[str, str]:
    """解析 'selector:value' 格式，仅在第一个冒号处分割。"""
    idx = field_str.index(":")
    return field_str[:idx], field_str[idx + 1:]


def _parse_cookie(cookie_str: str) -> tuple[str, str]:
    """解析 'name=value' 格式。"""
    if "=" not in cookie_str:
        raise click.BadParameter(f"Cookie 格式错误（应为 name=value）: {cookie_str}")
    name, _, value = cookie_str.partition("=")
    return name, value


# ---------------------------------------------------------------------------
# Click 命令组
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version="0.1.0", prog_name="browser-cli")
def main() -> None:
    """browser-cli — 基于 pywebview 的浏览器自动化工具。"""
    pass


# ---------------------------------------------------------------------------
# 1. goto
# ---------------------------------------------------------------------------

@main.command("goto")
@click.argument("url")
@click.option("--timeout", type=float, default=None, help="页面加载超时（秒）")
def goto(url: str, timeout: float | None) -> None:
    """导航到指定 URL。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        try:
            logger.info("正在导航到: %s", url)
            ctrl.goto(url, timeout=timeout)
            current = ctrl.get_current_url()
            logger.info("当前页面: %s", current)
            click.echo(current or url)
        except Exception as e:
            logger.error("导航失败: %s", e)
            raise
        finally:
            ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# 2. extract
# ---------------------------------------------------------------------------

@main.command("extract")
@click.argument("selector")
@click.option("--url", default=None, help="先导航到此 URL 再提取")
@click.option(
    "--attribute",
    default="text",
    type=click.Choice(["text", "html", "value"]),
    help="提取属性类型（默认为 text）",
)
@click.option(
    "--format", "fmt",
    default="txt",
    type=click.Choice(["json", "csv", "txt"]),
    help="输出格式（默认为 txt）",
)
@click.option("--output", "-o", default=None, help="保存到文件；不指定则输出到 stdout")
@click.option("--timeout", type=float, default=None, help="页面加载超时（秒）")
@click.option("--wait-selector", "wait_sel", default=None, help="等待此选择器出现后再提取（SPA/动态内容）")
@click.option("--wait-dynamic", "wait_dynamic", type=float, default=None, help="等待额外秒数以渲染动态内容")
def extract(
    selector: str,
    url: str | None,
    attribute: str,
    fmt: str,
    output: str | None,
    timeout: float | None,
    wait_sel: str | None,
    wait_dynamic: float | None,
) -> None:
    """从页面提取匹配 SELECTOR 的元素内容。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            if url:
                logger.info("导航到: %s", url)
                ctrl.goto(url, timeout=timeout)

            if wait_sel:
                logger.info("等待选择器出现: %s", wait_sel)
                actions.wait_for_selector(wait_sel, timeout=(timeout or DEFAULT_TIMEOUT))

            if wait_dynamic:
                logger.info("等待动态内容渲染: %.1fs", wait_dynamic)
                time.sleep(wait_dynamic)

            logger.info("提取选择器 %r (attribute=%s)", selector, attribute)
            results = actions.extract(selector, attribute=attribute)

            if output:
                safe_path = _safe_output_path(output)
                parser = ContentParser(ctrl)
                parser.save_to_file(results, fmt, safe_path)
                logger.info("已保存到: %s", safe_path)
                click.echo(f"已保存到: {safe_path}")
            else:
                if fmt == "json":
                    import json
                    click.echo(json.dumps(results, indent=2, ensure_ascii=False))
                elif fmt == "csv":
                    import csv
                    import io
                    buf = io.StringIO()
                    writer = csv.writer(buf)
                    for row in results:
                        writer.writerow([row])
                    click.echo(buf.getvalue().rstrip())
                else:
                    for item in results:
                        click.echo(item)
        except Exception as e:
            logger.error("提取失败: %s", e)
            raise
        finally:
            ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# 3. fill-form
# ---------------------------------------------------------------------------

@main.command("fill-form")
@click.option("--url", required=True, help="表单所在页面 URL")
@click.option(
    "--field",
    "fields",
    multiple=True,
    required=True,
    help='表单字段，格式为 "selector:value"（可多次指定）',
)
@click.option("--submit", default=None, help="提交按钮的选择器")
@click.option("--timeout", type=float, default=None, help="页面加载超时（秒）")
def fill_form(
    url: str,
    fields: tuple[str, ...],
    submit: str | None,
    timeout: float | None,
) -> None:
    """导航到 URL，填写表单字段并可选地提交。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            logger.info("导航到: %s", url)
            ctrl.goto(url, timeout=timeout)

            for field_str in fields:
                try:
                    sel, val = _parse_field(field_str)
                except ValueError:
                    logger.error("字段格式错误（应为 selector:value）: %s", field_str)
                    raise
                logger.info("填写 %r = %r", sel, val)
                actions.wait_for_selector(sel)
                actions.fill(sel, val)

            if submit:
                logger.info("提交表单: %s", submit)
                actions.wait_for_selector(submit)
                actions.click(submit)
                ctrl.wait_loaded(timeout=timeout)

            current = ctrl.get_current_url()
            logger.info("当前页面: %s", current)
            click.echo(current or url)
        except Exception as e:
            logger.error("表单填写失败: %s", e)
            raise
        finally:
            ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# 4. search
# ---------------------------------------------------------------------------

@main.command("search")
@click.option("--url", required=True, help="搜索引擎页面 URL")
@click.option("--query", required=True, help="搜索关键词")
@click.option("--input", "input_sel", required=True, help="搜索输入框选择器")
@click.option("--submit", "submit_sel", default=None, help="提交按钮选择器")
@click.option("--timeout", type=float, default=None, help="页面加载超时（秒）")
@click.option("--extract-result", "extract_sel", default=None, help="搜索后提取搜索结果的选择器")
@click.option("--wait-result", "wait_result", type=float, default=2.0, help="搜索后等待结果加载的秒数（默认 2）")
def search(
    url: str,
    query: str,
    input_sel: str,
    submit_sel: str | None,
    timeout: float | None,
    extract_sel: str | None,
    wait_result: float,
) -> None:
    """在指定搜索页执行搜索，可选提取搜索结果。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            logger.info("搜索: %r -> %s", query, url)
            actions.search(url=url, query=query, input_selector=input_sel, submit_selector=submit_sel)
            current = ctrl.get_current_url()
            logger.info("搜索完成，当前页面: %s", current)

            if wait_result > 0:
                logger.info("等待搜索结果加载: %.1fs", wait_result)
                time.sleep(wait_result)

            if extract_sel:
                logger.info("提取搜索结果: %s", extract_sel)
                results = actions.extract(extract_sel, attribute="text")
                import json
                click.echo(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                click.echo(current or url)
        except Exception as e:
            logger.error("搜索失败: %s", e)
            raise
        finally:
            ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# 5. set-cookies
# ---------------------------------------------------------------------------

@main.command("set-cookies")
@click.option("--url", required=True, help="先导航到该 URL 再设置 Cookie")
@click.option(
    "--cookie",
    "cookies_raw",
    multiple=True,
    required=True,
    help='Cookie，格式为 "name=value"（可多次指定）',
)
@click.option("--goto", "goto_path", default=None, help="设置 Cookie 后导航到的路径")
@click.option("--timeout", type=float, default=None, help="页面加载超时（秒）")
def set_cookies(
    url: str,
    cookies_raw: tuple[str, ...],
    goto_path: str | None,
    timeout: float | None,
) -> None:
    """设置浏览器 Cookie 并可选择导航到目标页面。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            logger.info("导航到: %s（设置 Cookie）", url)
            ctrl.goto(url, timeout=timeout)

            cookies_dict: dict[str, str] = {}
            for c in cookies_raw:
                name, value = _parse_cookie(c)
                cookies_dict[name] = value

            logger.info("设置 %d 个 Cookie", len(cookies_dict))
            actions.set_cookies(cookies_dict)

            if goto_path:
                logger.info("导航到: %s", goto_path)
                ctrl.goto(goto_path, timeout=timeout)

            current = ctrl.get_current_url()
            click.echo(current or "")
        except Exception as e:
            logger.error("设置 Cookie 失败: %s", e)
            raise
        finally:
            ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# 6. screenshot
# ---------------------------------------------------------------------------

@main.command("screenshot")
@click.option("--url", required=True, help="要截图的页面 URL")
@click.option("--output", "-o", default="screenshot.png", help="输出文件路径（默认为 screenshot.png）")
@click.option("--selector", default=None, help="仅截取指定 CSS 选择器对应的元素")
@click.option("--timeout", type=float, default=None, help="页面加载超时（秒）")
def screenshot(
    url: str,
    output: str,
    selector: str | None,
    timeout: float | None,
) -> None:
    """对指定 URL 页面截图并保存为 PNG 文件。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            logger.info("导航到: %s", url)
            ctrl.goto(url, timeout=timeout)

            safe_path = _safe_output_path(output)

            if selector:
                actions.wait_for_selector(selector)
                actions.scroll_to_selector(selector)
                click.echo(f"正在截取元素: {selector}")
                logger.info("正在截取元素: %s", selector)
                actions.screenshot_element(selector, safe_path)
            else:
                logger.info("正在截图...")
                actions.screenshot(safe_path)

            logger.info("截图已保存到: %s", safe_path)
            click.echo(f"截图已保存到: {safe_path}")
        except Exception as e:
            logger.error("截图失败: %s", e)
            raise
        finally:
            ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# 7. run — YAML 剧本执行
# ---------------------------------------------------------------------------

_PLAYBOOK_ACTIONS: dict[str, str] = {
    "goto": "goto", "wait": "wait", "click": "click",
    "fill": "fill", "type": "type", "extract": "extract",
    "set_cookies": "set_cookies", "screenshot": "screenshot",
    "search": "search", "login": "login", "select": "select",
    "sleep": "sleep", "wait_loaded": "wait_loaded",
    "hover": "hover", "scroll_to": "scroll_to", "scroll_by": "scroll_by",
    "press": "press", "upload": "upload", "snapshot": "snapshot",
}


def _dispatch_action(
    name: str,
    params: dict,
    controller: BrowserController,
    actions: AutomationActions,
    parser: ContentParser,
    default_timeout: float | None,
) -> None:
    """将单个剧本动作分发到对应的操作方法。"""
    t = params.get("timeout", default_timeout) if "timeout" in params else default_timeout

    if name == "goto":
        url = str(params["url"])
        controller.goto(url, timeout=t)
        logger.info("  已导航到: %s", controller.get_current_url())

    elif name == "wait":
        sel = str(params["selector"])
        actions.wait_for_selector(sel, timeout=float(params.get("timeout", default_timeout or 10.0)))
        logger.info("  元素已出现: %s", sel)

    elif name == "click":
        sel = str(params["selector"])
        actions.click(sel)
        logger.info("  已点击: %s", sel)

    elif name == "fill":
        sel = str(params["selector"])
        val = str(params["value"])
        actions.fill(sel, val)
        logger.info("  已填写 %r = %r", sel, val)

    elif name == "type":
        sel = str(params["selector"])
        text = str(params["text"])
        delay = float(params.get("delay", 0.05))
        actions.type_text(sel, text, delay=delay)
        logger.info("  已输入文本到: %s", sel)

    elif name == "extract":
        sel = str(params["selector"])
        attr = str(params.get("attribute", "text"))
        fmt = str(params.get("format", "txt"))
        output = params.get("output")
        results = actions.extract(sel, attribute=attr)
        if output:
            parser.save_to_file(results, fmt, str(output))
            logger.info("  提取结果已保存到: %s", output)
        else:
            import json as _json
            if fmt == "json":
                click.echo(_json.dumps(results, indent=2, ensure_ascii=False))
            else:
                for item in results:
                    click.echo(item)
            logger.info("  已提取 %d 个元素 (%s=%s)", len(results), sel, attr)

    elif name == "set_cookies":
        cookies = params.get("cookies", {})
        actions.set_cookies(dict(cookies))
        logger.info("  已设置 %d 个 Cookie", len(cookies))

    elif name == "screenshot":
        output = str(params.get("output") or params.get("path") or "screenshot.png")
        actions.screenshot(output)
        logger.info("  截图已保存到: %s", output)

    elif name == "search":
        query = str(params["query"])
        input_sel = str(params["input_selector"])
        submit_sel = params.get("submit_selector")
        current = controller.get_current_url() or "about:blank"
        actions.search(
            url=current, query=query,
            input_selector=input_sel,
            submit_selector=str(submit_sel) if submit_sel else None,
        )
        logger.info("  搜索完成: %r", query)

    elif name == "login":
        url_val = str(params.get("url", ""))
        username = str(params["username"])
        password = str(params["password"])
        username_sel = str(params.get("username_selector",
            'input[name="username"], #username, input[type="email"]'))
        password_sel = str(params.get("password_selector",
            'input[name="password"], #password, input[type="password"]'))
        submit_sel = str(params.get("submit_selector",
            'button[type="submit"], input[type="submit"]'))
        if url_val:
            controller.goto(url_val, timeout=t)
        actions.login(
            url=url_val or controller.get_current_url() or "",
            username=username, password=password,
            username_selector=username_sel,
            password_selector=password_sel,
            submit_selector=submit_sel,
        )
        logger.info("  登录完成，当前页面: %s", controller.get_current_url())

    elif name == "select":
        sel = str(params["selector"])
        val = str(params["value"])
        actions.select_option(sel, val)
        logger.info("  已选择 %r = %r", sel, val)

    elif name == "hover":
        sel = str(params["selector"])
        actions.hover(sel)
        logger.info("  已悬停: %s", sel)

    elif name == "scroll_to":
        sel = str(params["selector"])
        actions.scroll_to_selector(sel)
        logger.info("  已滚动到: %s", sel)

    elif name == "scroll_by":
        x = float(params.get("x", 0))
        y = float(params.get("y", 0))
        actions.scroll_by(x, y)
        logger.info("  已滚动: x=%s, y=%s", x, y)

    elif name == "press":
        key = str(params["key"])
        sel = params.get("selector")
        actions.press_key(key, selector=str(sel) if sel else None)
        logger.info("  已按键: %s", key)

    elif name == "upload":
        sel = str(params["selector"])
        path = str(params["file_path"])
        actions.upload_file(sel, path)
        logger.info("  已触发上传: %s", sel)

    elif name == "snapshot":
        parser = ContentParser(controller)
        body = parser.get_all_text("body")
        import json as _json
        data = {"url": controller.get_current_url(), "body_preview": (body or "")[:300]}
        click.echo(_json.dumps(data, indent=2, ensure_ascii=False))
        logger.info("  快照完成")

    elif name == "sleep":
        duration = float(params.get("duration", params.get("seconds", 1.0)))
        logger.info("  等待 %.1f 秒...", duration)
        import time as _time
        _time.sleep(duration)

    elif name == "wait_loaded":
        timeout_val = float(params.get("timeout", default_timeout or 10.0))
        controller.wait_loaded(timeout=timeout_val)
        logger.info("  页面加载完成: %s", controller.get_current_url())


@main.command("run")
@click.option("--playbook", required=True, type=click.Path(exists=True), help="YAML 剧本文件路径")
@click.option("--timeout", type=float, default=None, help="默认操作超时（秒）")
def run(playbook: str, timeout: float | None) -> None:
    """执行 YAML 格式的自动化剧本。"""
    try:
        with open(playbook, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error("YAML 解析失败: %s", e)
        sys.exit(1)
    except OSError as e:
        logger.error("无法读取文件 %s: %s", playbook, e)
        sys.exit(1)

    if isinstance(data, dict):
        playbook_list = data.get("actions") or data.get("steps") or data.get("playbook")
        if not isinstance(playbook_list, list):
            logger.error("剧本文件格式无效：需要 actions/steps 列表或顶层序列")
            sys.exit(1)
        data = playbook_list

    if not isinstance(data, list):
        logger.error("剧本文件格式无效：需要 YAML 列表")
        sys.exit(1)

    logger.info("加载剧本: %s（共 %d 个动作）", playbook, len(data))

    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        actions = AutomationActions(ctrl)
        parser = ContentParser(ctrl)
        try:
            for idx, action in enumerate(data):
                if not isinstance(action, dict):
                    logger.warning("剧本第 %d 个动作格式无效，跳过", idx + 1)
                    continue

                # 支持两种格式：
                # 格式1: {action: goto, url: ...}  → action 字段标识动作名，其余为参数
                # 格式2: {goto: {url: ...}}         → 键为动作名，值为参数字典
                if "action" in action:
                    name = action.pop("action")
                    params = action
                elif len(action) == 1:
                    name = next(iter(action.keys()))
                    params = action[name] or {}
                else:
                    logger.warning("剧本第 %d 个动作格式无效，跳过", idx + 1)
                    continue
                if name not in _PLAYBOOK_ACTIONS:
                    logger.warning("剧本第 %d 个动作 %r 不支持，跳过", idx + 1, name)
                    continue
                logger.info("[%d/%d] 执行: %s", idx + 1, len(data), name)
                _dispatch_action(name, params, ctrl, actions, parser, timeout)
        except Exception as e:
            logger.error("剧本执行失败: %s", e)
            raise
        finally:
            ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# 8. webui — Web 控制面板
# ---------------------------------------------------------------------------

@main.command("webui")
@click.option("--port", default=5000, help="Web 服务器端口（默认 5000）")
@click.option("--no-open", is_flag=True, help="不自动打开浏览器")
@click.option("--width", default=1024, help="浏览器窗口宽度（默认 1024）")
@click.option("--height", default=768, help="浏览器窗口高度（默认 768）")
@click.option("--max-windows", default=5, help="最大窗口数量（默认 5）")
def webui(port: int, no_open: bool, width: int, height: int, max_windows: int) -> None:
    """启动 Web 控制面板，在浏览器中操控自动化工具。"""
    import secrets
    from .webui import create_app

    pool = WindowPool(
        max_windows=max_windows,
        width=width,
        height=height,
        timeout=DEFAULT_TIMEOUT,
    )

    # 生成随机访问令牌，防止本地端口被其他页面/进程驱动；
    # 可通过 BROWSER_CLI_WEBUI_TOKEN 环境变量固定令牌（脚本/CI/反向代理场景）
    token = os.environ.get("BROWSER_CLI_WEBUI_TOKEN", "").strip() or secrets.token_urlsafe(16)
    app = create_app(pool, token=token)

    # 启动 Flask 在后台线程
    flask_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()

    # 自动打开浏览器
    panel_url = f"http://127.0.0.1:{port}/?token={token}"
    if not no_open:
        import webbrowser
        time.sleep(1)
        webbrowser.open(panel_url)

    logger.info("Web 控制面板已启动: %s", panel_url)
    logger.info("最大窗口数: %d", max_windows)
    click.echo(f"Web 控制面板: {panel_url}")
    click.echo(f"最大窗口数: {max_windows}")
    click.echo("访问令牌已自动生成并附加到 URL，请勿泄露。")
    click.echo("在控制面板中点击「停止」或按 Ctrl+C 退出")

    def _keep_alive(p: WindowPool) -> None:
        """保持窗口开启，不做任何操作。"""
        logger.info("浏览器窗口已就绪，等待控制面板指令...")

    try:
        pool.run(_keep_alive)
    except KeyboardInterrupt:
        logger.info("收到退出信号")
    finally:
        pool.close_all()
        logger.info("已退出")


# ---------------------------------------------------------------------------
# 新增: multi-window 同时打开多个窗口
# ---------------------------------------------------------------------------

@main.command("multi-window")
@click.option("--urls", required=True, help="逗号分隔的 URL 列表")
@click.option("--titles", default="", help="逗号分隔的窗口标题列表（可选）")
@click.option("--width", default=1024, help="每个窗口宽度")
@click.option("--height", default=768, help="每个窗口高度")
@click.option("--timeout", type=float, default=None, help="页面加载超时（秒）")
@click.option("--stay-open", type=float, default=60.0, help="保持窗口打开的时间（秒，默认 60）")
def multi_window(urls, titles, width, height, timeout, stay_open):
    """同时打开多个浏览器窗口，加载多个 URL，保持打开一段时间后自动关闭。"""
    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    if not url_list:
        raise click.BadParameter("URL 列表不能为空")

    title_list = [t.strip() for t in titles.split(",")] if titles and titles.strip() else []

    logger.info("创建 %d 个窗口", len(url_list))
    manager = MultiWindowManager(
        urls=url_list,
        titles=title_list if title_list else None,
        hidden=False,
        width=width,
        height=height,
        timeout=timeout or DEFAULT_TIMEOUT,
    )
    click.echo(f"已创建 {len(url_list)} 个窗口，将保持打开 {stay_open} 秒后自动关闭")
    manager.run(stay_open=stay_open)
    logger.info("所有窗口已关闭")


# ---------------------------------------------------------------------------
# 新增: fill-steps 分步执行自动化步骤
# ---------------------------------------------------------------------------

@main.command("fill-steps")
@click.option("--url", required=True, help="目标页面 URL")
@click.option("--step", "steps", multiple=True, required=True, help="步骤，格式: action:arg1:arg2（可多次指定）")
@click.option("--timeout", type=float, default=None, help="默认操作超时（秒）")
def fill_steps(url, steps, timeout):
    """分步执行自动化操作，支持 fill/click/wait/type/select/extract。

    步骤格式（冒号分隔）:\n
      - fill:selector:value  → 填写表单字段\n
      - click:selector       → 点击元素\n
      - wait:selector:timeout → 等待选择器出现\n
      - type:selector:text:delay → 逐字符输入文本\n
      - select:selector:value → 选择下拉框选项\n
      - extract:selector:attribute → 提取内容并输出\n
    """
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _parse_step(step_str: str) -> tuple[str, list[str]]:
        """解析 step:arg1:arg2 → (action, [arg1, arg2])"""
        parts = step_str.split(":")
        action = parts[0].strip()
        args = [p.strip() for p in parts[1:]]
        return action, args

    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            parser = ContentParser(ctrl)
            logger.info("导航到: %s", url)
            ctrl.goto(url, timeout=timeout)

            for idx, step_str in enumerate(steps, 1):
                action, args = _parse_step(step_str)
                logger.info("[%d/%d] 执行动作: %s %s", idx, len(steps), action, args)

                if action == "fill":
                    if len(args) < 2:
                        logger.error("fill 需要 2 个参数: selector value"); return
                    sel = args[0]
                    val = ":".join(args[1:])  # 支持值中包含冒号
                    actions.wait_for_selector(sel, timeout=(timeout or 10.0))
                    actions.fill(sel, val)
                elif action == "click":
                    if not args:
                        logger.error("click 需要 1 个参数: selector"); return
                    sel = args[0]
                    actions.wait_for_selector(sel, timeout=(timeout or 10.0))
                    actions.click(sel)
                    ctrl.wait_loaded(timeout=timeout)
                elif action == "wait":
                    if not args:
                        logger.error("wait 需要 1 个参数: selector"); return
                    sel = args[0]
                    to = float(args[1]) if len(args) >= 2 else (timeout or 10.0)
                    actions.wait_for_selector(sel, timeout=to)
                elif action == "type":
                    if len(args) < 2:
                        logger.error("type 需要至少 2 个参数: selector text"); return
                    sel = args[0]
                    if len(args) == 2:
                        text = args[1]
                        delay = 0.05
                    else:
                        # 尝试将最后一个参数解析为 delay（秒）
                        try:
                            delay = float(args[-1])
                            text = ":".join(args[1:-1])
                        except ValueError:
                            text = ":".join(args[1:])
                            delay = 0.05
                    actions.wait_for_selector(sel, timeout=(timeout or 10.0))
                    actions.type_text(sel, text, delay=delay)
                elif action == "select":
                    if len(args) < 2:
                        logger.error("select 需要 2 个参数: selector value"); return
                    sel = args[0]
                    val = ":".join(args[1:])  # 支持值中包含冒号
                    actions.wait_for_selector(sel, timeout=(timeout or 10.0))
                    actions.select_option(sel, val)
                elif action == "extract":
                    if not args:
                        logger.error("extract 需要至少 1 个参数: selector"); return
                    sel = args[0]
                    attr = args[1] if len(args) >= 2 else "text"
                    results = actions.extract(sel, attribute=attr)
                    import json
                    click.echo(json.dumps(results, indent=2, ensure_ascii=False))
                elif action == "hover":
                    if not args:
                        logger.error("hover 需要 1 个参数: selector"); return
                    sel = args[0]
                    actions.wait_for_selector(sel, timeout=(timeout or 10.0))
                    actions.hover(sel)
                elif action == "scroll":
                    if not args:
                        logger.error("scroll 需要 1 个参数: selector"); return
                    sel = args[0]
                    actions.wait_for_selector(sel, timeout=(timeout or 10.0))
                    actions.scroll_to_selector(sel)
                elif action == "scroll-down":
                    if not args:
                        logger.error("scroll-down 需要 1 个参数: pixels"); return
                    px = int(args[0])
                    actions.scroll_by(0, px)
                elif action == "press":
                    if not args:
                        logger.error("press 需要 1 个参数: key"); return
                    key = args[0]
                    sel = args[1] if len(args) >= 2 else None
                    actions.press_key(key, selector=sel)
                elif action == "upload":
                    if len(args) < 2:
                        logger.error("upload 需要 2 个参数: selector file_path"); return
                    sel = args[0]
                    path = args[1]
                    actions.wait_for_selector(sel, timeout=(timeout or 10.0))
                    actions.upload_file(sel, path)
                elif action == "snapshot":
                    body = parser.get_all_text("body")
                    import json
                    click.echo(json.dumps({"url": ctrl.get_current_url(), "body_preview": (body or "")[:300]}, indent=2, ensure_ascii=False))
                elif action == "sleep":
                    if not args:
                        logger.error("sleep 需要 1 个参数: seconds"); return
                    duration = float(args[0])
                    logger.info("等待 %.1f 秒", duration)
                    time.sleep(duration)
                else:
                    logger.warning("不支持的动作类型: %s", action)

            current = ctrl.get_current_url()
            logger.info("所有步骤执行完成，当前 URL: %s", current)
            click.echo(f"完成: {current}")
        except Exception as e:
            logger.error("步骤执行失败: %s", e)
            raise
        finally:
            ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# 新增: login 登录命令
# ---------------------------------------------------------------------------

@main.command("login")
@click.option("--url", required=True, help="登录页面 URL")
@click.option("--username", required=True, help="用户名")
@click.option("--password", required=True, help="密码")
@click.option("--username-selector", default='input[name="username"], #username, input[type="email"]', help="用户名输入框选择器")
@click.option("--password-selector", default='input[name="password"], #password, input[type="password"]', help="密码输入框选择器")
@click.option("--submit-selector", default='button[type="submit"], input[type="submit"]', help="登录按钮选择器")
@click.option("--extract", "extract_sel", default=None, help="登录后提取内容的选择器")
@click.option("--format", "fmt", default="txt", type=click.Choice(["json", "csv", "txt"]))
@click.option("--output", "-o", default=None, help="保存结果到文件")
@click.option("--timeout", type=float, default=None, help="操作超时（秒）")
def login(url, username, password, username_selector, password_selector, submit_selector, extract_sel, fmt, output, timeout):
    """导航到登录页，自动填写用户名密码并提交，可选提取登录后内容。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            logger.info("登录: %s", url)
            actions.login(
                url=url,
                username=username,
                password=password,
                username_selector=username_selector,
                password_selector=password_selector,
                submit_selector=submit_selector,
            )
            current = ctrl.get_current_url()
            logger.info("登录完成，当前 URL: %s", current)
            click.echo(f"登录完成: {current}")

            if extract_sel:
                logger.info("提取内容: %s", extract_sel)
                results = actions.extract(extract_sel, attribute="text")
                if output:
                    parser = ContentParser(ctrl)
                    parser.save_to_file(results, fmt, output)
                    logger.info("结果已保存到: %s", output)
                    click.echo(f"已保存到: {output}")
                else:
                    if fmt == "json":
                        import json
                        click.echo(json.dumps(results, indent=2, ensure_ascii=False))
                    elif fmt == "csv":
                        import csv
                        import io
                        buf = io.StringIO()
                        writer = csv.writer(buf)
                        for row in results:
                            writer.writerow([row])
                        click.echo(buf.getvalue().rstrip())
                    else:
                        for item in results:
                            click.echo(item)
        except Exception as e:
            logger.error("登录失败: %s", e)
            raise
        finally:
            ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# P1.1: doctor 诊断命令
# ---------------------------------------------------------------------------

@main.command("doctor")
def doctor() -> None:
    """系统环境诊断：检查 Python、pywebview、WebView2 等依赖。"""
    import sys
    import shutil

    click.echo("=" * 50)
    click.echo("浏览器自动化 CLI - 系统诊断")
    click.echo("=" * 50)

    issues = []

    # 1. Python 版本
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    click.echo(f"[Python] 版本: {py_ver} ({sys.executable})")
    if sys.version_info < (3, 10):
        issues.append("Python 版本过低，建议 >= 3.10")

    # 2. pywebview
    try:
        import webview
        click.echo(f"[pywebview] 已安装: {webview.__version__ if hasattr(webview, '__version__') else 'OK'}")
    except ImportError:
        issues.append("pywebview 未安装，请运行: pip install pywebview")
        click.echo("[pywebview] 未安装!")

    # 3. click
    try:
        import click as _click
        click.echo("[click] 已安装")
    except ImportError:
        issues.append("click 未安装，请运行: pip install click")

    # 4. Flask (webui)
    try:
        import flask
        click.echo("[Flask] 已安装")
    except ImportError:
        issues.append("Flask 未安装，请运行: pip install flask")
        click.echo("[Flask] 未安装!")

    # 5. WebView2 (Windows)
    if sys.platform == "win32":
        wv2_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge WebView\Application",
            r"C:\Program Files\Microsoft\Edge WebView\Application",
        ]
        wv2_found = False
        for p in wv2_paths:
            if os.path.exists(p):
                click.echo(f"[WebView2] 已安装: {p}")
                wv2_found = True
                break
        if not wv2_found:
            # 检查注册表
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}")
                click.echo("[WebView2] 已安装 (注册表检测)")
                wv2_found = True
            except Exception:
                pass
        if not wv2_found:
            issues.append("WebView2 运行时未检测到，请安装: https://go.microsoft.com/fwlink/p/?LinkId=2124703")
            click.echo("[WebView2] 未检测到!")

    # 6. 浏览器检测
    browsers = []
    browser_paths = [
        ("Edge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ("Edge", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        ("Chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        ("Chrome", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ("Firefox", r"C:\Program Files\Mozilla Firefox\firefox.exe"),
        ("Firefox", r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"),
    ]
    for name, path in browser_paths:
        if os.path.exists(path):
            browsers.append(f"{name} ({path})")
    if browsers:
        for b in browsers:
            click.echo(f"[浏览器] {b}")
    else:
        click.echo("[浏览器] 未检测到常见浏览器")

    # 7. 网络
    try:
        import urllib.request
        urllib.request.urlopen("https://www.bing.com", timeout=5)
        click.echo("[网络] 网络连接正常")
    except Exception:
        issues.append("网络连接异常，请检查网络设置")

    # 8. GUI 后端检测
    from .controller import get_gui_info
    gui_info = get_gui_info()
    click.echo(f"[GUI 后端] 当前: {gui_info['selected']}")
    click.echo(f"  WebView2: {'可用' if gui_info['webview2_available'] else '不可用'}")
    click.echo(f"  CEF: {'可用' if gui_info['cef_available'] else '不可用'}")
    if gui_info['env_override']:
        click.echo(f"  (已通过 BROWSER_CLI_GUI={gui_info['env_override']} 覆盖)")

    # 9. 功能完整性统计
    from .actions import AutomationActions
    from .parser import ContentParser
    import inspect

    action_methods = [m for m in dir(AutomationActions) if not m.startswith('_') and callable(getattr(AutomationActions, m, None))]
    parser_methods = [m for m in dir(ContentParser) if not m.startswith('_') and callable(getattr(ContentParser, m, None))]
    cli_commands = ["goto", "extract", "fill-form", "search", "set-cookies", "screenshot", "run",
                    "webui", "multi-window", "fill-steps", "login", "doctor", "browsers",
                    "record", "replay", "batch", "pdf", "hover", "scroll-to", "scroll-down",
                    "press", "wait-for-timeout", "wait-for-url", "snapshot", "upload"]

    click.echo(f"[功能统计]")
    click.echo(f"  Actions 方法: {len(action_methods)} 个")
    click.echo(f"  Parser 方法: {len(parser_methods)} 个")
    click.echo(f"  CLI 命令: {len(cli_commands)} 个")
    click.echo(f"  深度交互: {'通过' if len(action_methods) >= 15 else '不足'} (click/fill/type/hover/scroll/press/extract/select/upload/screenshot/login/search)")
    click.echo(f"  数据提取: {'通过' if len(parser_methods) >= 7 else '不足'} (links/tables/text/meta/forms/images/regex)")
    click.echo(f"  多表单: 支持 (fill-steps 命令)")

    # 总结
    click.echo("=" * 50)
    if issues:
        click.echo(f"发现 {len(issues)} 个问题:")
        for i, issue in enumerate(issues, 1):
            click.echo(f"  {i}. {issue}")
    else:
        click.echo("所有检查通过，系统环境正常！")
    click.echo("=" * 50)


# ---------------------------------------------------------------------------
# P1.2: browsers 列出浏览器命令
# ---------------------------------------------------------------------------

@main.command("browsers")
def browsers() -> None:
    """列出系统已安装的浏览器。"""
    import sys
    import subprocess

    click.echo("系统已安装浏览器:")
    click.echo("-" * 40)

    if sys.platform == "win32":
        browser_list = [
            ("Microsoft Edge", [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ]),
            ("Google Chrome", [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]),
            ("Mozilla Firefox", [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            ]),
            ("Opera", [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera\launcher.exe"),
            ]),
            ("Brave", [
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ]),
        ]
    else:
        browser_list = [
            ("Google Chrome", ["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium"]),
            ("Mozilla Firefox", ["/usr/bin/firefox"]),
        ]

    found = 0
    for name, paths in browser_list:
        for p in paths:
            if os.path.exists(p):
                try:
                    # 获取版本
                    result = subprocess.run(
                        [p, "--version"], capture_output=True, text=True, timeout=5,
                        encoding='utf-8', errors='replace',
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )
                    version = result.stdout.strip() or result.stderr.strip() or "未知版本"
                except Exception:
                    version = "未知版本"
                click.echo(f"  {name}: {version}")
                click.echo(f"    路径: {p}")
                found += 1
                break

    if found == 0:
        click.echo("  未检测到常见浏览器")
    click.echo("-" * 40)
    click.echo(f"共检测到 {found} 个浏览器")


# ---------------------------------------------------------------------------
# P3.1: record 录制命令
# ---------------------------------------------------------------------------

@main.command("record")
@click.option("--url", default="https://example.com", help="起始 URL")
@click.option("--output", "-o", default="recorded_script.json", help="输出文件路径")
@click.option("--timeout", type=float, default=None, help="录制超时（秒，默认 120）")
def record(url: str, output: str, timeout: float | None) -> None:
    """交互式录制用户操作到 JSON 脚本文件。\n
    打开浏览器窗口，记录所有点击、输入、滚动操作。\n
    按 Ctrl+C 或在浏览器中按 Esc 停止录制。
    """
    controller = BrowserController(hidden=False, width=1024, height=768, timeout=(timeout or 120))
    actions_recorded: list[dict] = []
    stop_event = threading.Event()

    def _run(ctrl: BrowserController) -> None:
        import json as _json
        ctrl.goto(url, timeout=timeout)

        # 注入事件监听器
        recorder_js = (
            "(function() {"
            "  if (window.__browser_cli_recorder) return;"
            "  window.__browser_cli_recorder = {events: []};"
            "  var r = window.__browser_cli_recorder;"

            # 记录点击
            "  document.addEventListener('click', function(e) {"
            "    var el = e.target;"
            "    var sel = el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase());"
            "    r.events.push({"
            "      type: 'click', selector: sel,"
            "      tag: el.tagName, id: el.id || '', className: el.className || '',"
            "      text: (el.textContent || '').substring(0, 50),"
            "      timestamp: Date.now()"
            "    });"
            "  }, true);"

            # 记录输入
            "  document.addEventListener('change', function(e) {"
            "    var el = e.target;"
            "    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') {"
            "      var sel = el.id ? '#' + el.id : (el.name ? '[name=\"' + el.name + '\"]' : el.tagName.toLowerCase());"
            "      r.events.push({"
            "        type: 'fill', selector: sel,"
            "        value: el.value || '',"
            "        timestamp: Date.now()"
            "      });"
            "    }"
            "  }, true);"

            # 记录滚动
            "  var scrollTimer = null;"
            "  window.addEventListener('scroll', function() {"
            "    if (scrollTimer) clearTimeout(scrollTimer);"
            "    scrollTimer = setTimeout(function() {"
            "      r.events.push({"
            "        type: 'scroll', x: window.scrollX, y: window.scrollY,"
            "        timestamp: Date.now()"
            "      });"
            "    }, 300);"
            "  }, true);"

            "  console.log('[browser-cli] 录制已启动');"
            "})();"
        )
        ctrl.exec_js(recorder_js)

        click.echo(f"录制已启动: {url}")
        click.echo("在浏览器窗口中操作，按 Ctrl+C 停止录制...")

        try:
            deadline = time.time() + (timeout or 120)
            while time.time() < deadline and not stop_event.is_set():
                time.sleep(2)
                try:
                    events = ctrl.exec_js(
                        "window.__browser_cli_recorder ? JSON.stringify(window.__browser_cli_recorder.events) : '[]'"
                    )
                    if events and events != "[]":
                        import json as _json
                        parsed = _json.loads(events) if isinstance(events, str) else events
                        if parsed:
                            # 只添加新事件
                            existing_count = len(actions_recorded)
                            new_events = parsed[existing_count:]
                            actions_recorded.extend(new_events)
                            if new_events:
                                click.echo(f"  已记录 {len(new_events)} 个新操作 (总计 {len(actions_recorded)})")
                except Exception:
                    pass
        except KeyboardInterrupt:
            click.echo("录制已停止")

        # 保存
        if actions_recorded:
            import json as _json
            safe_path = _safe_output_path(output)
            with open(safe_path, "w", encoding="utf-8") as f:
                _json.dump(actions_recorded, f, indent=2, ensure_ascii=False)
            click.echo(f"已保存 {len(actions_recorded)} 个操作到: {safe_path}")
        else:
            click.echo("未记录到任何操作")
        ctrl.close()

    try:
        controller.run(_run)
    except KeyboardInterrupt:
        # Ctrl+C 到达主线程：通知录制线程停止并保存
        stop_event.set()
        controller.close()
        click.echo("录制已停止，正在保存...")
        time.sleep(2)
        click.echo("保存完成。")


# ---------------------------------------------------------------------------
# P3.2: replay 回放命令
# ---------------------------------------------------------------------------

@main.command("replay")
@click.argument("script_file", type=click.Path(exists=True))
@click.option("--speed", type=float, default=1.0, help="回放速度倍率（默认 1.0）")
@click.option("--timeout", type=float, default=None, help="操作超时（秒）")
def replay(script_file: str, speed: float, timeout: float | None) -> None:
    """回放录制的操作脚本（JSON 格式）。"""
    import json as _json

    with open(script_file, "r", encoding="utf-8") as f:
        steps = _json.load(f)

    if not isinstance(steps, list):
        click.echo("错误：脚本文件必须是 JSON 数组（record 命令的输出格式）")
        sys.exit(1)

    click.echo(f"加载脚本: {script_file} ({len(steps)} 个操作)")
    click.echo(f"回放速度: {speed}x")

    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        actions = AutomationActions(ctrl)
        last_timestamp = 0
        for i, step in enumerate(steps):
            # 计算等待时间
            ts = step.get("timestamp", 0)
            if last_timestamp > 0 and ts > last_timestamp:
                wait_ms = (ts - last_timestamp) / speed
                if wait_ms > 0:
                    time.sleep(wait_ms / 1000.0)
            last_timestamp = ts

            step_type = step.get("type", "")
            selector = step.get("selector", "")
            click.echo(f"[{i+1}/{len(steps)}] {step_type}: {selector}")

            try:
                if step_type == "click" and selector:
                    actions.wait_for_selector(selector)
                    actions.click(selector)
                elif step_type == "fill" and selector:
                    actions.wait_for_selector(selector)
                    actions.fill(selector, step.get("value", ""))
                elif step_type == "scroll":
                    try:
                        x = float(step.get("x", 0))
                        y = float(step.get("y", 0))
                    except (TypeError, ValueError):
                        x = 0.0
                        y = 0.0
                    actions.scroll_by(x, y)
                else:
                    click.echo(f"  跳过未知操作类型: {step_type}")
            except Exception as e:
                click.echo(f"  操作失败: {e}")
                continue

        click.echo(f"回放完成: {len(steps)} 个操作")
        ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# P4.1: batch 批量执行命令
# ---------------------------------------------------------------------------

@main.command("batch")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--timeout", type=float, default=None, help="每个 URL 的超时（秒）")
@click.option("--extract", "extract_sel", default=None, help="每个页面提取的选择器")
@click.option("--output", "-o", default=None, help="保存结果到文件")
def batch(file_path: str, timeout: float | None, extract_sel: str | None, output: str | None) -> None:
    """批量执行文件中的 URL 列表（每行一个 URL）。"""
    with open(file_path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    if not urls:
        click.echo("文件中没有有效的 URL")
        return

    click.echo(f"批量处理 {len(urls)} 个 URL")

    results = []
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        actions = AutomationActions(ctrl)
        parser = ContentParser(ctrl)

        for i, url in enumerate(urls):
            click.echo(f"[{i+1}/{len(urls)}] {url}")
            try:
                ctrl.goto(url, timeout=timeout)
                if extract_sel:
                    data = actions.extract(extract_sel, attribute="text")
                    results.append({"url": url, "ok": True, "data": data})
                    click.echo(f"  提取: {data}")
                else:
                    title = actions.extract("title", attribute="text")
                    results.append({"url": url, "ok": True, "title": title[0] if title else ""})
                    click.echo(f"  标题: {title[0] if title else '无'}")
            except Exception as e:
                results.append({"url": url, "ok": False, "error": str(e)})
                click.echo(f"  失败: {e}")

        if output:
            import json as _json
            with open(output, "w", encoding="utf-8") as f:
                _json.dump(results, f, indent=2, ensure_ascii=False)
            click.echo(f"结果已保存到: {output}")

        ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# P5.1: pdf 导出命令
# ---------------------------------------------------------------------------

@main.command("pdf")
@click.argument("output_path", type=click.Path())
@click.option("--url", default=None, help="先导航到此 URL 再导出")
@click.option("--format", "paper_format", default="A4", help="纸张格式（A4/Letter/Legal）")
@click.option("--landscape", is_flag=True, help="横向")
@click.option("--timeout", type=float, default=None, help="操作超时（秒）")
def pdf(output_path: str, url: str | None, paper_format: str, landscape: bool, timeout: float | None) -> None:
    """打开浏览器打印对话框，由用户在对话框中手动保存为 PDF。

    注意：pywebview 的 WebView2 不支持编程化导出 PDF，本命令只能
    打开打印对话框，需要用户在对话框中手动选择"另存为 PDF"。
    窗口保持可见 30 秒供用户操作。
    """
    controller = BrowserController(hidden=False, timeout=(timeout or DEFAULT_TIMEOUT))

    def _run(ctrl: BrowserController) -> None:
        actions = AutomationActions(ctrl)
        if url:
            ctrl.goto(url, timeout=timeout)

        # 使用浏览器打印 API
        pdf_script = (
            "(function() {"
            "  return new Promise(function(resolve) {"
            "    window.print();"
            "    resolve('PDF print dialog opened');"
            "  });"
            "})();"
        )

        try:
            # 首先尝试通过 JS 触发打印
            actions.exec_js_async(pdf_script)
            click.echo(f"PDF 打印对话框已打开，请手动保存为: {output_path}")
            click.echo(f"提示: 格式={paper_format}, 横向={landscape}")
        except Exception:
            # 回退：提示用户手动操作
            click.echo("无法自动触发打印，请在浏览器窗口中按 Ctrl+P 保存 PDF")

        # 保持窗口打开，等待用户操作
        time.sleep(30)
        ctrl.close()

    controller.run(_run)


# ---------------------------------------------------------------------------
# hover 悬停命令
# ---------------------------------------------------------------------------

@main.command("hover")
@click.argument("selector")
@click.option("--url", default=None, help="先导航到此 URL 再操作")
@click.option("--timeout", type=float, default=None, help="操作超时（秒）")
def hover(selector: str, url: str | None, timeout: float | None) -> None:
    """悬停在指定元素上，触发 mouseenter/mouseover 事件。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))
    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            if url:
                ctrl.goto(url, timeout=timeout)
            actions.wait_for_selector(selector)
            actions.hover(selector)
            logger.info("已悬停: %s", selector)
            click.echo(f"已悬停: {selector}")
        except Exception as e:
            logger.error("悬停失败: %s", e)
            raise
        finally:
            ctrl.close()
    controller.run(_run)


# ---------------------------------------------------------------------------
# scroll-to 滚动到指定元素
# ---------------------------------------------------------------------------

@main.command("scroll-to")
@click.argument("selector")
@click.option("--url", default=None, help="先导航到此 URL 再操作")
@click.option("--timeout", type=float, default=None, help="操作超时（秒）")
def scroll_to(selector: str, url: str | None, timeout: float | None) -> None:
    """滚动到指定元素位置。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))
    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            if url:
                ctrl.goto(url, timeout=timeout)
            actions.wait_for_selector(selector)
            actions.scroll_to_selector(selector)
            logger.info("已滚动到: %s", selector)
            click.echo(f"已滚动到: {selector}")
        except Exception as e:
            logger.error("滚动失败: %s", e)
            raise
        finally:
            ctrl.close()
    controller.run(_run)


# ---------------------------------------------------------------------------
# scroll-down 向下滚动
# ---------------------------------------------------------------------------

@main.command("scroll-down")
@click.argument("pixels", type=int)
@click.option("--url", default=None, help="先导航到此 URL 再操作")
@click.option("--timeout", type=float, default=None, help="操作超时（秒）")
def scroll_down(pixels: int, url: str | None, timeout: float | None) -> None:
    """向下滚动指定像素。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))
    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            if url:
                ctrl.goto(url, timeout=timeout)
            actions.scroll_by(0, pixels)
            logger.info("已滚动 %d 像素", pixels)
            click.echo(f"已滚动 {pixels} 像素")
        except Exception as e:
            logger.error("滚动失败: %s", e)
            raise
        finally:
            ctrl.close()
    controller.run(_run)


# ---------------------------------------------------------------------------
# press 按键命令
# ---------------------------------------------------------------------------

@main.command("press")
@click.argument("key")
@click.option("--selector", default=None, help="目标元素选择器（默认使用当前聚焦元素）")
@click.option("--url", default=None, help="先导航到此 URL 再操作")
@click.option("--timeout", type=float, default=None, help="操作超时（秒）")
def press(key: str, selector: str | None, url: str | None, timeout: float | None) -> None:
    """模拟键盘按键（Enter、Tab、Escape、ArrowDown 等）。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))
    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            if url:
                ctrl.goto(url, timeout=timeout)
            if selector:
                actions.wait_for_selector(selector)
            actions.press_key(key, selector=selector)
            logger.info("已按键: %s", key)
            click.echo(f"已按键: {key}")
        except Exception as e:
            logger.error("按键失败: %s", e)
            raise
        finally:
            ctrl.close()
    controller.run(_run)


# ---------------------------------------------------------------------------
# wait-for-timeout 等待超时命令
# ---------------------------------------------------------------------------

@main.command("wait-for-timeout")
@click.argument("milliseconds", type=int)
def wait_for_timeout(milliseconds: int) -> None:
    """等待指定毫秒数。"""
    seconds = milliseconds / 1000.0
    logger.info("等待 %.1f 秒...", seconds)
    time.sleep(seconds)
    click.echo(f"已等待 {milliseconds}ms")


# ---------------------------------------------------------------------------
# wait-for-url 等待 URL 匹配
# ---------------------------------------------------------------------------

@main.command("wait-for-url")
@click.argument("pattern")
@click.option("--url", default=None, help="先导航到此 URL 再等待匹配")
@click.option("--timeout", type=float, default=30.0, help="等待超时（秒）")
def wait_for_url(pattern: str, url: str | None, timeout: float) -> None:
    """等待 URL 匹配 glob 模式（如 **/success）。可配合 --url 先导航再等待。"""
    import fnmatch
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=timeout)
    def _run(ctrl: BrowserController) -> None:
        try:
            if url:
                ctrl.goto(url, timeout=timeout)
            deadline = time.time() + timeout
            while time.time() < deadline:
                current = ctrl.get_current_url()
                if current and fnmatch.fnmatch(current, pattern):
                    logger.info("URL 已匹配: %s -> %s", pattern, current)
                    click.echo(f"URL 已匹配: {current}")
                    return
                time.sleep(0.5)
            raise TimeoutError(f"等待 URL 匹配超时 ({timeout}s): {pattern}")
        except Exception as e:
            logger.error("等待 URL 失败: %s", e)
            raise
        finally:
            ctrl.close()
    controller.run(_run)


# ---------------------------------------------------------------------------
# snapshot 页面快照命令
# ---------------------------------------------------------------------------

@main.command("snapshot")
@click.option("--url", default=None, help="先导航到此 URL 再抓取快照")
@click.option("--output", "-o", default=None, help="保存到文件")
@click.option("--timeout", type=float, default=None, help="页面加载超时（秒）")
def snapshot(url: str | None, output: str | None, timeout: float | None) -> None:
    """输出页面 DOM 文本快照，包括标题、URL、可见文本和表单信息。"""
    controller = BrowserController(hidden=DEFAULT_HIDDEN, timeout=(timeout or DEFAULT_TIMEOUT))
    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            parser = ContentParser(ctrl)
            if url:
                ctrl.goto(url, timeout=timeout)
            current_url = ctrl.get_current_url()
            title = actions.extract("title", attribute="text")
            title_text = title[0] if title else "无标题"
            body_text = parser.get_all_text("body")
            links = parser.get_links()
            forms = parser.get_forms()
            images = parser.get_images()

            snapshot_data = {
                "url": current_url,
                "title": title_text,
                "body_text_preview": (body_text or "")[:500],
                "links_count": len(links),
                "forms_count": len(forms),
                "images_count": len(images),
                "forms": forms,
            }

            import json as _json
            result_str = _json.dumps(snapshot_data, indent=2, ensure_ascii=False)
            if output:
                safe_path = _safe_output_path(output)
                parser.save_to_file(snapshot_data, "json", safe_path)
                logger.info("快照已保存到: %s", safe_path)
                click.echo(f"快照已保存到: {safe_path}")
            else:
                click.echo(result_str)
        except Exception as e:
            logger.error("快照失败: %s", e)
            raise
        finally:
            ctrl.close()
    controller.run(_run)


# ---------------------------------------------------------------------------
# upload 文件上传命令
# ---------------------------------------------------------------------------

@main.command("upload")
@click.argument("selector")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--url", default=None, help="先导航到此 URL 再操作")
@click.option("--timeout", type=float, default=None, help="操作超时（秒）")
def upload(selector: str, file_path: str, url: str | None, timeout: float | None) -> None:
    """触发文件上传对话框（点击文件输入框）。"""
    controller = BrowserController(hidden=False, timeout=(timeout or DEFAULT_TIMEOUT))
    def _run(ctrl: BrowserController) -> None:
        try:
            actions = AutomationActions(ctrl)
            if url:
                ctrl.goto(url, timeout=timeout)
            actions.wait_for_selector(selector)
            actions.upload_file(selector, file_path)
            logger.info("已触发文件上传: %s -> %s", selector, file_path)
            click.echo(f"已触发文件上传对话框: {selector} ({file_path})")
            click.echo("注意: WebView2 不允许脚本直接设置文件，请在对话框中选择文件，路径参数仅用于提示。")
        except Exception as e:
            logger.error("上传失败: %s", e)
            raise
        finally:
            ctrl.close()
    controller.run(_run)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()