"""BrowserController — 核心控制器，封装 pywebview 窗口生命周期与 JS 交互。"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Any, Callable

# 解决 .NET 从含中文/网络路径加载 DLL 时抛出 "loadFromRemoteSources" 错误
os.environ.setdefault('COMPLUS_LoadFromRemoteSources', '1')

import webview

logger = logging.getLogger(__name__)


def get_available_gui() -> str | None:
    """检测当前系统可用的最佳 GUI 后端。

    检测顺序：
    1. 环境变量 BROWSER_CLI_GUI（手动指定）
    2. WebView2 (edgechromium) — Windows 默认
    3. CEF (cef) — 保底回退
    4. None — 让 pywebview 自动选择

    返回值可用于 webview.start(gui=...) 的 gui 参数。
    """
    # 1. 环境变量手动指定
    env_gui = os.environ.get("BROWSER_CLI_GUI", "").strip().lower()
    if env_gui:
        logger.info("使用环境变量指定的 GUI 后端: %s", env_gui)
        return env_gui

    # 2. 检测 WebView2 (Windows)
    if _webview2_available():
        logger.info("GUI 后端: edgechromium (WebView2)")
        return None  # None 让 pywebview 自动选 edgechromium

    # 3. 检测 CEF 回退
    if _cef_available():
        logger.info("GUI 后端: cef (CEF 回退)")
        return "cef"

    # 4. 默认
    logger.info("GUI 后端: 自动检测 (None)")
    return None


def _webview2_available() -> bool:
    """检测 WebView2 运行时是否可用。"""
    if sys.platform != "win32":
        return False
    # 检查 WebView2 安装目录
    wv2_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge WebView\Application",
        r"C:\Program Files\Microsoft\Edge WebView\Application",
    ]
    for p in wv2_paths:
        if os.path.exists(p):
            return True
    # 检查注册表
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}")
        winreg.CloseKey(key)
        return True
    except Exception:
        pass
    return False


def _cef_available() -> bool:
    """检测 cefpython3 是否可导入。

    检测顺序：
    1. 系统已安装的 cefpython3
    2. 项目内置的 vendor/cefpython3
    """
    try:
        import cefpython3  # noqa: F401
        return True
    except ImportError:
        pass
    except Exception:
        pass

    # 尝试从项目内置 vendor 目录加载
    try:
        vendor_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vendor")
        if os.path.isdir(os.path.join(vendor_path, "cefpython3")):
            sys.path.insert(0, vendor_path)
            import cefpython3  # noqa: F401
            logger.info("使用内置 CEF 引擎: vendor/cefpython3")
            return True
    except ImportError:
        logger.debug("vendor/cefpython3 未找到")
    except Exception as e:
        logger.debug("vendor/cefpython3 导入失败: %s", e)

    return False


def get_gui_info() -> dict:
    """获取当前 GUI 后端详细信息，供 doctor 命令使用。"""
    info = {
        "selected": None,
        "webview2_available": _webview2_available(),
        "cef_available": _cef_available(),
        "env_override": os.environ.get("BROWSER_CLI_GUI", ""),
    }
    if info["env_override"]:
        info["selected"] = info["env_override"]
    elif info["webview2_available"]:
        info["selected"] = "edgechromium"
    elif info["cef_available"]:
        info["selected"] = "cef"
    else:
        info["selected"] = "auto"
    return info


class BrowserController:
    """封装 pywebview 窗口的创建、配置、JS 执行和生命周期管理。

    pywebview 的 webview.start() 必须在主线程中调用，且会阻塞直到窗口销毁。
    因此本控制器采用 "run 模式"：在构造时创建窗口，调用 run() 启动事件循环，
    func 回调在独立线程中执行自动化操作，操作完成后销毁窗口使 start() 返回。
    """

    def __init__(
        self,
        hidden: bool = True,
        width: int = 1280,
        height: int = 800,
        user_agent: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._hidden = hidden
        self._width = width
        self._height = height
        self._timeout = timeout
        self._user_agent = user_agent
        self._js_result: Any = None
        self._js_event = threading.Event()
        self._js_lock = threading.Lock()
        self._ready = threading.Event()
        self._failed = False
        self._window: webview.Window | None = None

        # 配置全局设置
        # IGNORE_SSL_ERRORS 默认开启（自动化工具常访问自签名/内网站点），
        # 可通过环境变量 BROWSER_CLI_IGNORE_SSL=0 关闭以恢复证书校验。
        webview.settings['ALLOW_DOWNLOADS'] = True
        webview.settings['IGNORE_SSL_ERRORS'] = (
            os.environ.get('BROWSER_CLI_IGNORE_SSL', '1') not in ('0', 'false', 'no')
        )
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False
        webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False

        self._window = webview.create_window(
            title='Browser CLI',
            url='about:blank',
            width=self._width,
            height=self._height,
            hidden=self._hidden,
            resizable=True,
            focus=False,
            confirm_close=False,
            background_color='#FFFFFF',
        )

    def run(self, operation: Callable[[BrowserController], None]) -> None:
        """启动 pywebview 事件循环并执行自动化操作。

        operation 会在 GUI 就绪后的独立线程中被调用。
        操作完成后应调用 self.close() 销毁窗口，使 run() 返回。
        """
        def _on_ready() -> None:
            self._ready.set()
            try:
                # 等待窗口真正就绪
                self._window.events.loaded.wait(timeout=10.0)
            except Exception:
                pass
            try:
                operation(self)
            except SystemExit:
                self.close()
            except Exception as e:
                logger.error("操作执行失败: %s", e)
                self._failed = True
                self.close()

        webview.start(
            func=_on_ready,
            gui=get_available_gui(),
            debug=False,
            private_mode=True,
            http_server=False,
            user_agent=self._user_agent,
        )
        if self._failed:
            sys.exit(1)

    def exec_js(self, script: str, timeout: float | None = None) -> Any:
        """同步执行 JavaScript 并返回结果（线程安全）。

        pywebview 的 evaluate_js 对同步 JS 直接返回结果，对 Promise 通过 callback 返回。
        """
        with self._js_lock:
            self._js_result = None
            self._js_event.clear()

            def _callback(result: Any) -> None:
                self._js_result = result
                self._js_event.set()

            result = self._window.evaluate_js(script, callback=_callback)

            if self._js_event.is_set():
                return self._js_result

            if result is not None:
                return result

            timeout = timeout or self._timeout
            if not self._js_event.wait(timeout=timeout):
                raise TimeoutError(f'JS 执行超时 ({timeout}s)')
            return self._js_result

    def run_js(self, script: str) -> None:
        """异步执行 JavaScript，不等待返回值。"""
        self._window.evaluate_js(script)

    def wait_loaded(self, timeout: float | None = None) -> None:
        """等待页面加载完成（用于点击/提交后的导航等待）。"""
        timeout = timeout or self._timeout
        self._window.events.loaded.clear()
        if self._window.events.loaded.wait(timeout=min(timeout, 10.0)):
            return

        # 回退到 readyState 轮询
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                state = self._window.evaluate_js('document.readyState')
                if state == 'complete':
                    return
            except Exception:
                pass
            time.sleep(0.5)
        logger.warning('页面加载等待超时 (%ss)', timeout)

    def goto(self, url: str, timeout: float | None = None) -> None:
        """导航到指定 URL 并等待 DOM 完全就绪。

        优先等待 webview 的 loaded 事件；若超时则回退到轮询 document.readyState。
        """
        self._window.events.loaded.clear()
        self._window.load_url(url)
        timeout = timeout or self._timeout

        # 阶段 1：等待 loaded 事件（最多 10 秒）
        if self._window.events.loaded.wait(timeout=min(timeout, 10.0)):
            time.sleep(1.0)
            return

        # 阶段 2：回退到轮询 document.readyState
        logger.debug('loaded 事件未触发，回退到 readyState 轮询')
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                state = self._window.evaluate_js('document.readyState')
                if state == 'complete':
                    logger.info('页面已通过 readyState 检测完成')
                    time.sleep(1.0)
                    return
            except Exception:
                pass
            time.sleep(0.5)

        raise TimeoutError(f'页面加载超时 ({timeout}s): {url}')

    def load_html(self, html: str, base_uri: str = '') -> None:
        """加载 HTML 内容并等待渲染完成。"""
        self._window.events.loaded.clear()
        self._window.load_html(html, base_uri)
        self.wait_loaded()

    def get_current_url(self) -> str | None:
        """获取当前页面 URL。"""
        return self._window.get_current_url()

    def close(self) -> None:
        """销毁窗口。"""
        try:
            if self._window:
                self._window.destroy()
        except Exception:
            pass
        self._window = None

    def __enter__(self) -> BrowserController:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class MultiWindowManager:
    """管理多个 pywebview 窗口，支持同时创建和批量操作。

    所有窗口在构造时通过多次调用 webview.create_window() 创建，
    调用 run() 后通过一次 webview.start() 统一启动管理。
    """

    def __init__(
        self,
        urls: list[str],
        titles: list[str] | None = None,
        hidden: bool = False,
        width: int = 1024,
        height: int = 768,
        timeout: float = 30.0,
    ) -> None:
        self._urls = list(urls)
        self._titles = titles or [f"Window {i + 1}" for i in range(len(urls))]
        self._hidden = hidden
        self._width = width
        self._height = height
        self._timeout = timeout
        self._windows: list[webview.Window] = []
        self._ready = threading.Event()

        webview.settings['ALLOW_DOWNLOADS'] = True
        webview.settings['IGNORE_SSL_ERRORS'] = (
            os.environ.get('BROWSER_CLI_IGNORE_SSL', '1') not in ('0', 'false', 'no')
        )
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False
        webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False

        for i, url in enumerate(self._urls):
            title = self._titles[i] if i < len(self._titles) else f"Window {i + 1}"
            w = webview.create_window(
                title=title,
                url="about:blank",
                width=self._width,
                height=self._height,
                hidden=self._hidden,
                resizable=True,
                focus=(i == 0),
                confirm_close=False,
                background_color="#FFFFFF",
            )
            self._windows.append(w)

    def run(self, stay_open: float = 60.0) -> None:
        """启动 pywebview 事件循环，导航所有窗口并保持开启一段时间。

        stay_open 秒后自动关闭所有窗口。
        """

        def _on_ready() -> None:
            self._ready.set()
            try:
                for w in self._windows:
                    w.events.loaded.wait(timeout=5.0)
            except Exception:
                pass
            self.goto_all()
            time.sleep(stay_open)
            self.close_all()

        webview.start(
            func=_on_ready,
            gui=get_available_gui(),
            debug=False,
            private_mode=True,
            http_server=False,
        )

    def goto_all(self) -> None:
        """导航所有窗口到各自的 URL 并等待加载完成。"""
        for i, w in enumerate(self._windows):
            url = self._urls[i]
            w.events.loaded.clear()
            w.load_url(url)
            # 阶段 1：等待 loaded 事件
            if w.events.loaded.wait(timeout=min(self._timeout, 10.0)):
                logger.info("窗口 %d (%s) 已加载: %s", i, w.title, url)
                time.sleep(1.0)
                continue

            # 阶段 2：回退到 readyState 轮询
            logger.debug("窗口 %d loaded 事件未触发，回退到 readyState 轮询", i)
            deadline = time.time() + self._timeout
            loaded = False
            while time.time() < deadline:
                try:
                    state = w.evaluate_js('document.readyState')
                    if state == 'complete':
                        logger.info("窗口 %d (%s) 已通过 readyState 检测完成: %s", i, w.title, url)
                        loaded = True
                        break
                except Exception:
                    pass
                time.sleep(0.5)

            if loaded:
                time.sleep(1.0)
            else:
                logger.warning("窗口 %d (%s) 加载超时: %s", i, w.title, url)

    def exec_js_on(self, window_index: int, script: str) -> Any:
        """在指定窗口执行 JavaScript 并返回结果。"""
        if window_index < 0 or window_index >= len(self._windows):
            raise IndexError(f"窗口索引超出范围: {window_index}")
        return self._windows[window_index].evaluate_js(script)

    def close_window(self, index: int) -> None:
        """关闭指定窗口。"""
        if 0 <= index < len(self._windows):
            try:
                self._windows[index].destroy()
            except Exception:
                pass
            self._windows[index] = None  # type: ignore[assignment]

    def close_all(self) -> None:
        """销毁所有窗口。"""
        for w in self._windows:
            try:
                if w is not None:
                    w.destroy()
            except Exception:
                pass
        self._windows = []

    def get_all_urls(self) -> list[str | None]:
        """获取所有窗口的当前 URL。"""
        result: list[str | None] = []
        for w in self._windows:
            try:
                result.append(w.get_current_url() if w is not None else None)
            except Exception:
                result.append(None)
        return result


class WindowPool:
    """Web 控制面板专用多窗口管理器。

    预创建 N 个窗口，通过 webview.start() 统一启动。
    支持活跃窗口切换，所有操作（导航/提取/填写/点击等）默认作用于当前活跃窗口。
    每个窗口有独立的 URL 和标题，可在 UI 中动态修改。
    """

    def __init__(
        self,
        max_windows: int = 5,
        width: int = 1024,
        height: int = 768,
        timeout: float = 30.0,
    ) -> None:
        # 多窗口时 pywebview/pythonnet 的 NavigationCompleted 事件不派发，
        # 安装补偿补丁（见 patches.py），单窗口不启用。
        from .patches import ensure_multi_window_navigation_patch

        ensure_multi_window_navigation_patch(max_windows > 1)
        self._max_windows = max_windows
        self._width = width
        self._height = height
        self._timeout = timeout
        self._active_index: int = 0
        self._ready = threading.Event()
        self._js_lock = threading.Lock()

        webview.settings['ALLOW_DOWNLOADS'] = True
        webview.settings['IGNORE_SSL_ERRORS'] = (
            os.environ.get('BROWSER_CLI_IGNORE_SSL', '1') not in ('0', 'false', 'no')
        )
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False
        webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False

        # 窗口槽位：[{window, url, title, loaded}]
        self._slots: list[dict[str, Any]] = []
        for i in range(max_windows):
            w = webview.create_window(
                title=f"Window {i + 1}",
                url="about:blank",
                width=self._width,
                height=self._height,
                hidden=False,
                resizable=True,
                focus=(i == 0),
                confirm_close=False,
                background_color="#FFFFFF",
            )
            self._slots.append({
                "window": w,
                "url": "about:blank",
                "title": f"Window {i + 1}",
                "loaded": False,
            })

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def run(self, operation: Callable[["WindowPool"], None]) -> None:
        """启动 pywebview 事件循环。"""

        def _on_ready() -> None:
            self._ready.set()
            # 等待所有窗口初始加载
            for slot in self._slots:
                try:
                    slot["window"].events.loaded.wait(timeout=5.0)
                    slot["loaded"] = True
                except Exception:
                    pass
            operation(self)

        webview.start(
            func=_on_ready,
            gui=get_available_gui(),
            debug=False,
            private_mode=True,
            http_server=False,
        )

    def close_all(self) -> None:
        """销毁所有窗口。"""
        for slot in self._slots:
            try:
                slot["window"].destroy()
            except Exception:
                pass
        self._slots.clear()

    # ------------------------------------------------------------------
    # 窗口管理
    # ------------------------------------------------------------------
    @property
    def active_index(self) -> int:
        return self._active_index

    @property
    def window_count(self) -> int:
        return self._max_windows

    def _active_window(self) -> webview.Window:
        return self._slots[self._active_index]["window"]

    def switch_to(self, index: int) -> None:
        """切换活跃窗口。"""
        if 0 <= index < len(self._slots):
            self._active_index = index

    def get_all_slots(self) -> list[dict]:
        """获取所有窗口槽位信息，供 UI 渲染标签页。"""
        result = []
        for i, slot in enumerate(self._slots):
            try:
                current_url = slot["window"].get_current_url() or slot["url"]
            except Exception:
                current_url = slot["url"]
            result.append({
                "index": i,
                "title": slot["title"],
                "url": current_url,
                "active": i == self._active_index,
                "loaded": slot["loaded"],
            })
        return result

    # ------------------------------------------------------------------
    # 导航
    # ------------------------------------------------------------------
    def goto(self, url: str, window_index: int | None = None,
             timeout: float | None = None) -> None:
        """导航指定窗口到 URL；默认使用当前活跃窗口。"""
        idx = window_index if window_index is not None else self._active_index
        if idx < 0 or idx >= len(self._slots):
            raise IndexError(f"窗口索引超出范围: {idx}")

        slot = self._slots[idx]
        w = slot["window"]
        w.events.loaded.clear()
        w.load_url(url)

        timeout = timeout or self._timeout
        if w.events.loaded.wait(timeout=min(timeout, 10.0)):
            slot["url"] = url
            slot["loaded"] = True
            time.sleep(1.0)
            return

        # 回退到 readyState 轮询
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                state = w.evaluate_js('document.readyState')
                if state == 'complete':
                    slot["url"] = url
                    slot["loaded"] = True
                    time.sleep(1.0)
                    return
            except Exception:
                pass
            time.sleep(0.5)

        raise TimeoutError(f'页面加载超时 ({timeout}s): {url}')

    def get_current_url(self, window_index: int | None = None) -> str | None:
        """获取指定窗口的当前 URL。"""
        idx = window_index if window_index is not None else self._active_index
        return self._slots[idx]["window"].get_current_url()

    # ------------------------------------------------------------------
    # JS 执行（线程安全）
    # ------------------------------------------------------------------
    def exec_js(self, script: str, window_index: int | None = None,
                timeout: float | None = None) -> Any:
        """在指定窗口同步执行 JS 并返回结果。"""
        idx = window_index if window_index is not None else self._active_index
        w = self._slots[idx]["window"]

        with self._js_lock:
            result_event = threading.Event()
            js_result: Any = None

            def _callback(result: Any) -> None:
                nonlocal js_result
                js_result = result
                result_event.set()

            result = w.evaluate_js(script, callback=_callback)
            if result_event.is_set():
                return js_result
            if result is not None:
                return result

            timeout = timeout or self._timeout
            if not result_event.wait(timeout=timeout):
                raise TimeoutError(f'JS 执行超时 ({timeout}s)')
            return js_result

    def run_js(self, script: str, window_index: int | None = None) -> None:
        """异步执行 JS，不等待返回值。"""
        idx = window_index if window_index is not None else self._active_index
        self._slots[idx]["window"].evaluate_js(script)

    def wait_loaded(self, window_index: int | None = None,
                    timeout: float | None = None) -> None:
        """等待指定窗口的页面加载完成。"""
        idx = window_index if window_index is not None else self._active_index
        w = self._slots[idx]["window"]
        timeout = timeout or self._timeout
        w.events.loaded.clear()
        if w.events.loaded.wait(timeout=min(timeout, 10.0)):
            return

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if w.evaluate_js('document.readyState') == 'complete':
                    return
            except Exception:
                pass
            time.sleep(0.5)
        logger.warning("窗口 %d 加载等待超时 (%ss)", idx, timeout)