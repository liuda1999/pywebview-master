"""pywebview 多窗口兼容补丁（Windows edgechromium / WebView2）。

背景
----
pywebview 6.2.1 + pythonnet 在 Windows 上创建多个 WebView2 窗口时，
WebView2 控件的 NavigationCompleted 事件不会派发（单窗口正常）。这导致
loaded / _pywebviewready 事件永不触发，evaluate_js / get_current_url 等
所有跨线程 API 在等待 20 秒后抛 WebViewException('Main window failed to
start')，控制面板的窗口列表、切换、导航全部不可用。

补偿方式
--------
hook 每个窗口的 on_webview_ready（该事件在多窗口下正常派发），在 WebView2
初始化成功后手动触发一次导航完成流程（inject_pywebview -> loaded/ready 置位），
让后续 API 调用恢复正常。仅对多窗口场景启用，单窗口保持 pywebview 原行为。

排查证据：D:\Blue Abyss\testcases\repro_2win_hook.py / repro_2win_comp.py
"""
import logging

logger = logging.getLogger(__name__)

_PATCHED = False


def ensure_multi_window_navigation_patch(enabled: bool = True) -> None:
    """为多窗口场景安装 NavigationCompleted 补偿补丁（幂等）。

    :param enabled: False 时不安装（单窗口场景不需要补偿）。
    """
    global _PATCHED
    if _PATCHED or not enabled:
        return
    _PATCHED = True
    try:
        from webview.platforms import edgechromium as _ec

        _orig_ready = _ec.EdgeChrome.on_webview_ready

        def _patched_ready(self, sender, args):
            _orig_ready(self, sender, args)
            try:
                if args.IsSuccess and getattr(self, "webview", None) is not None:
                    cwv = self.webview.CoreWebView2
                    if cwv is not None:
                        self.on_navigation_completed(cwv, None)
            except Exception:
                logger.exception("multi-window navigation compensation failed")

        _ec.EdgeChrome.on_webview_ready = _patched_ready
    except Exception:
        logger.warning(
            "multi-window navigation compensation unavailable "
            "(edgechromium not present)",
            exc_info=True,
        )
