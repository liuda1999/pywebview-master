"""webui — Flask-based web control panel for the browser automation tool."""

from __future__ import annotations

import base64
import logging
import os
import tempfile
import time

from flask import Flask, current_app, jsonify, render_template, request

from .actions import AutomationActions
from .controller import WindowPool
from .parser import ContentParser

logger = logging.getLogger(__name__)


def create_app(pool: WindowPool, token: str | None = None):
    """Create and configure the Flask application.

    The WindowPool instance is stored in app.config so that all routes
    can access it via current_app.config['pool'].

    token: 可选访问令牌。非空时所有请求必须携带
    X-Browser-CLI-Token 请求头（或 ?token= 查询参数）且值匹配，
    用于防止本地端口被其他页面/进程直接驱动（CSRF / DNS rebinding 防护）。
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )
    app.config["pool"] = pool
    app.config["token"] = token or ""

    @app.before_request
    def _check_auth():
        """令牌 + Host 校验：仅允许携带令牌访问本机回环地址。"""
        expected = app.config.get("token") or ""
        if expected:
            provided = request.headers.get("X-Browser-CLI-Token", "")
            if not provided:
                provided = request.args.get("token", "")
            if provided != expected:
                return jsonify({"error": "unauthorized: invalid or missing token"}), 403
        host = (request.host or "").split(":")[0].strip().lower()
        if host not in ("127.0.0.1", "localhost", "::1"):
            return jsonify({"error": "forbidden host"}), 403

    # ==================================================================
    # 页面渲染
    # ==================================================================
    @app.route("/")
    def index():
        return render_template("index.html", token=app.config.get("token") or "")

    # ==================================================================
    # 窗口管理 API
    # ==================================================================

    @app.route("/api/windows", methods=["GET"])
    def api_windows():
        """获取所有窗口槽位信息（标签页列表）。"""
        try:
            pool: WindowPool = current_app.config["pool"]
            slots = pool.get_all_slots()
            return jsonify({"ok": True, "windows": slots, "active_index": pool.active_index})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/windows/switch", methods=["POST"])
    def api_switch_window():
        """切换活跃窗口。"""
        data = request.get_json(silent=True) or {}
        index = data.get("index", 0)
        try:
            pool: WindowPool = current_app.config["pool"]
            pool.switch_to(int(index))
            return jsonify({"ok": True, "active_index": pool.active_index})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ==================================================================
    # 导航
    # ==================================================================

    @app.route("/api/goto", methods=["POST"])
    def api_goto():
        data = request.get_json(silent=True) or {}
        url = data.get("url", "").strip()
        window_index = data.get("window_index")
        if not url:
            return jsonify({"ok": False, "error": "url is required"}), 400
        try:
            pool: WindowPool = current_app.config["pool"]
            pool.goto(url, window_index=window_index)
            current_url = pool.get_current_url(window_index=window_index)
            return jsonify({"ok": True, "url": current_url})
        except Exception as e:
            logger.error("goto 失败: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500

    # ==================================================================
    # 状态
    # ==================================================================

    @app.route("/api/status", methods=["GET"])
    def api_status():
        try:
            pool: WindowPool = current_app.config["pool"]
            url = pool.get_current_url()
            title = pool.exec_js("document.title") or ""
            return jsonify({"url": url, "title": title, "active_index": pool.active_index})
        except Exception as e:
            return jsonify({"url": "", "title": "", "active_index": 0})

    # ==================================================================
    # 提取
    # ==================================================================

    @app.route("/api/extract", methods=["POST"])
    def api_extract():
        data = request.get_json(silent=True) or {}
        selector = data.get("selector", "").strip()
        attribute = data.get("attribute", "text")
        wait_selector = data.get("wait_selector", "").strip()
        wait_dynamic = data.get("wait_dynamic", 0)
        window_index = data.get("window_index")
        if not selector:
            return jsonify({"ok": False, "error": "selector is required"}), 400
        try:
            pool: WindowPool = current_app.config["pool"]
            actions = AutomationActions(_pool_adapter(pool, window_index))

            if wait_selector:
                actions.wait_for_selector(wait_selector)
            if wait_dynamic:
                time.sleep(float(wait_dynamic))

            results = actions.extract(selector, attribute=attribute)
            return jsonify({"ok": True, "results": results, "result": results})
        except Exception as e:
            logger.error("extract 失败: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500

    # ==================================================================
    # JS 执行
    # ==================================================================

    @app.route("/api/exec_js", methods=["POST"])
    def api_exec_js():
        data = request.get_json(silent=True) or {}
        script = data.get("script") or data.get("code", "")
        window_index = data.get("window_index")
        if not script:
            return jsonify({"ok": False, "error": "script is required"}), 400
        try:
            pool: WindowPool = current_app.config["pool"]
            result = pool.exec_js(script, window_index=window_index)
            return jsonify({"ok": True, "result": result})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ==================================================================
    # 截图
    # ==================================================================

    @app.route("/api/screenshot", methods=["POST"])
    def api_screenshot():
        data = request.get_json(silent=True) or {}
        window_index = data.get("window_index")
        pool: WindowPool = current_app.config["pool"]
        actions = AutomationActions(_pool_adapter(pool, window_index))
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".png", prefix="webui_screenshot_")
            os.close(fd)
            actions.screenshot(tmp_path)
            if os.path.exists(tmp_path) and tmp_path.endswith(".png"):
                with open(tmp_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")
                return jsonify({
                    "ok": True,
                    "image": f"data:image/png;base64,{img_data}",
                    "screenshot": img_data,
                    "result": img_data,
                })
            html_path = tmp_path.rsplit(".", 1)[0] + ".html"
            if os.path.exists(html_path):
                with open(html_path, "r", encoding="utf-8") as f:
                    html = f.read()
                return jsonify({"ok": False, "html": html})
            raise RuntimeError("截图文件未生成")
        except Exception as e:
            logger.error("screenshot 失败: %s", e)
            try:
                html = pool.exec_js("document.documentElement.outerHTML", window_index=window_index)
                return jsonify({"ok": False, "html": html or ""})
            except Exception:
                return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    # ==================================================================
    # 表单填写
    # ==================================================================

    @app.route("/api/fill", methods=["POST"])
    def api_fill():
        data = request.get_json(silent=True) or {}
        selector = data.get("selector", "").strip()
        value = data.get("value", "")
        window_index = data.get("window_index")
        if not selector:
            return jsonify({"ok": False, "error": "selector is required"}), 400
        try:
            pool: WindowPool = current_app.config["pool"]
            actions = AutomationActions(_pool_adapter(pool, window_index))
            actions.wait_for_selector(selector)
            actions.fill(selector, value)
            return jsonify({"ok": True, "message": f"已填写: {selector}"})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/click", methods=["POST"])
    def api_click():
        data = request.get_json(silent=True) or {}
        selector = data.get("selector", "").strip()
        window_index = data.get("window_index")
        if not selector:
            return jsonify({"ok": False, "error": "selector is required"}), 400
        try:
            pool: WindowPool = current_app.config["pool"]
            actions = AutomationActions(_pool_adapter(pool, window_index))
            actions.click(selector)
            return jsonify({"ok": True, "message": f"已点击: {selector}"})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ==================================================================
    # 链接提取
    # ==================================================================

    @app.route("/api/links", methods=["POST"])
    def api_links():
        data = request.get_json(silent=True) or {}
        window_index = data.get("window_index")
        try:
            pool: WindowPool = current_app.config["pool"]
            parser = ContentParser(_pool_adapter(pool, window_index))
            links = parser.get_links()
            return jsonify({"ok": True, "links": links, "result": links})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ==================================================================
    # 登录
    # ==================================================================

    @app.route("/api/login", methods=["POST"])
    def api_login():
        data = request.get_json(silent=True) or {}
        url = data.get("url", "").strip()
        username = data.get("username", "")
        password = data.get("password", "")
        username_selector = data.get("username_selector", 'input[name="username"], #username, input[type="email"]')
        password_selector = data.get("password_selector", 'input[name="password"], #password, input[type="password"]')
        submit_selector = data.get("submit_selector", 'button[type="submit"], input[type="submit"]')
        extract_sel = data.get("extract_selector", "").strip()
        window_index = data.get("window_index")
        if not url or not username or not password:
            return jsonify({"ok": False, "error": "url, username, password are required"}), 400
        try:
            pool: WindowPool = current_app.config["pool"]
            actions = AutomationActions(_pool_adapter(pool, window_index))
            actions.login(
                url=url, username=username, password=password,
                username_selector=username_selector,
                password_selector=password_selector,
                submit_selector=submit_selector,
            )
            current_url = pool.get_current_url(window_index=window_index)
            result = {"ok": True, "url": current_url, "message": "登录完成"}
            if extract_sel:
                result["extract"] = actions.extract(extract_sel, attribute="text")
            return jsonify(result)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ==================================================================
    # 搜索
    # ==================================================================

    @app.route("/api/search", methods=["POST"])
    def api_search():
        data = request.get_json(silent=True) or {}
        url = data.get("url", "").strip()
        query = data.get("query", "")
        input_selector = data.get("input_selector", "")
        submit_selector = data.get("submit_selector") or None
        extract_sel = data.get("extract_selector", "").strip()
        wait_result = float(data.get("wait_result", 2.0))
        window_index = data.get("window_index")
        if not url or not query or not input_selector:
            return jsonify({"ok": False, "error": "url, query, input_selector are required"}), 400
        try:
            pool: WindowPool = current_app.config["pool"]
            actions = AutomationActions(_pool_adapter(pool, window_index))
            actions.search(
                url=url, query=query,
                input_selector=input_selector,
                submit_selector=submit_selector,
            )
            if wait_result > 0:
                time.sleep(wait_result)
            current_url = pool.get_current_url(window_index=window_index)
            result = {"ok": True, "url": current_url, "message": "搜索完成"}
            if extract_sel:
                result["extract"] = actions.extract(extract_sel, attribute="text")
            return jsonify(result)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ==================================================================
    # 多步表单填写
    # ==================================================================

    @app.route("/api/fill-steps", methods=["POST"])
    def api_fill_steps():
        data = request.get_json(silent=True) or {}
        url = data.get("url", "").strip()
        steps = data.get("steps", [])
        window_index = data.get("window_index")
        if not url or not steps:
            return jsonify({"ok": False, "error": "url and steps are required"}), 400
        try:
            pool: WindowPool = current_app.config["pool"]
            adapter = _pool_adapter(pool, window_index)
            actions = AutomationActions(adapter)

            if url:
                pool.goto(url, window_index=window_index)

            results = []
            for step in steps:
                action = step.get("action", "")
                args = step.get("args", [])
                step_result = {"action": action, "args": args}

                if action == "fill":
                    actions.wait_for_selector(args[0])
                    actions.fill(args[0], args[1] if len(args) > 1 else "")
                    step_result["status"] = "ok"
                elif action == "click":
                    actions.wait_for_selector(args[0])
                    actions.click(args[0])
                    pool.wait_loaded(window_index=window_index)
                    step_result["status"] = "ok"
                elif action == "wait":
                    to = float(args[1]) if len(args) > 1 else 10.0
                    actions.wait_for_selector(args[0], timeout=to)
                    step_result["status"] = "ok"
                elif action == "type":
                    text = args[1] if len(args) > 1 else ""
                    delay = float(args[2]) if len(args) > 2 else 0.05
                    actions.wait_for_selector(args[0])
                    actions.type_text(args[0], text, delay=delay)
                    step_result["status"] = "ok"
                elif action == "select":
                    actions.wait_for_selector(args[0])
                    actions.select_option(args[0], args[1] if len(args) > 1 else "")
                    step_result["status"] = "ok"
                elif action == "extract":
                    attr = args[1] if len(args) > 1 else "text"
                    step_result["data"] = actions.extract(args[0], attribute=attr)
                    step_result["status"] = "ok"
                else:
                    step_result["status"] = "unknown_action"

                results.append(step_result)

            return jsonify({"ok": True, "results": results, "url": pool.get_current_url(window_index=window_index)})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ==================================================================
    # 停止
    # ==================================================================

    @app.route("/api/stop", methods=["POST"])
    def api_stop():
        try:
            pool: WindowPool = current_app.config["pool"]
            pool.close_all()
            return jsonify({"ok": True, "message": "已停止"})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    return app


# ======================================================================
# 适配器：将 WindowPool 伪装成 BrowserController 供 AutomationActions 使用
# ======================================================================

class _PoolAdapter:
    """将 WindowPool + window_index 适配为 BrowserController 兼容接口，
    使 AutomationActions / ContentParser 无需修改即可在多窗口环境下工作。"""

    def __init__(self, pool: WindowPool, window_index: int | None = None) -> None:
        self._pool = pool
        self._window_index = window_index

    def exec_js(self, script: str, timeout: float | None = None) -> object:
        return self._pool.exec_js(script, window_index=self._window_index, timeout=timeout)

    def run_js(self, script: str) -> None:
        self._pool.run_js(script, window_index=self._window_index)

    def goto(self, url: str, timeout: float | None = None) -> None:
        self._pool.goto(url, window_index=self._window_index, timeout=timeout)

    def wait_loaded(self, timeout: float | None = None) -> None:
        self._pool.wait_loaded(window_index=self._window_index, timeout=timeout)

    def get_current_url(self) -> str | None:
        return self._pool.get_current_url(window_index=self._window_index)

    def close(self) -> None:
        pass  # 不关闭单个窗口，由 WindowPool 统一管理


def _pool_adapter(pool: WindowPool, window_index: int | None = None) -> _PoolAdapter:
    return _PoolAdapter(pool, window_index)


# Alias for backward compatibility
create_webui_app = create_app