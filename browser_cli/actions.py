"""AutomationActions — 基于 BrowserController 的高级自动化操作封装。"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any

from .controller import BrowserController

logger = logging.getLogger(__name__)


class AutomationActions:
    """封装常用的浏览器自动化操作，基于 BrowserController 实例。"""

    def __init__(self, controller: BrowserController) -> None:
        self._controller = controller
        self._dialog_messages: list[dict] = []

    # ------------------------------------------------------------------
    # 1. click
    # ------------------------------------------------------------------
    def click(self, selector: str) -> None:
        """查找 CSS 选择器匹配的元素，滚动到可见区域并点击。"""
        script = (
            "(function() {"
            "  var el = document.querySelector(" + json.dumps(selector) + ");"
            "  if (!el) {"
            "    throw new Error('Element not found: ' + " + json.dumps(selector) + ");"
            "  }"
            "  el.scrollIntoView({behavior: 'instant', block: 'center'});"
            "  el.click();"
            "  return true;"
            "})();"
        )
        self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 2. fill
    # ------------------------------------------------------------------
    def fill(self, selector: str, value: str, retries: int = 6, retry_delay: float = 0.7) -> None:
        """设置元素值并触发 input / change 事件（兼容 React / Vue）。

        SPA 页面（如百度首页）在 load 事件之后仍会异步初始化并重绘输入框，
        刚填入的值可能被清空。因此填入后轮询验证，值不符则重填，直到页面
        稳定或重试次数用尽。
        """
        script = (
            "(function() {"
            "  var el = document.querySelector(" + json.dumps(selector) + ");"
            "  if (!el) {"
            "    throw new Error('Element not found: ' + " + json.dumps(selector) + ");"
            "  }"
            "  var node = el;"
            "  var depth = 0;"
            "  while (node && depth < 8) {"
            "    var cs = getComputedStyle(node);"
            "    if (cs.display === 'none') {"
            "      node.style.display = 'block';"
            "    }"
            "    node = node.parentElement;"
            "    depth++;"
            "  }"
            "  var proto = Object.getPrototypeOf(el);"
            "  var descriptor = Object.getOwnPropertyDescriptor(proto, 'value');"
            "  if (descriptor && descriptor.set) {"
            "    descriptor.set.call(el, " + json.dumps(value) + ");"
            "  } else {"
            "    el.value = " + json.dumps(value) + ";"
            "  }"
            "  el.dispatchEvent(new Event('input', {bubbles: true}));"
            "  el.dispatchEvent(new Event('change', {bubbles: true}));"
            "  return true;"
            "})();"
        )
        verify_script = (
            "(function() {"
            "  var el = document.querySelector(" + json.dumps(selector) + ");"
            "  return el ? el.value : null;"
            "})();"
        )
        self._controller.exec_js(script)
        for attempt in range(retries):
            current = self._controller.exec_js(verify_script)
            if current == value:
                return
            time.sleep(retry_delay)
            self._controller.exec_js(script)
        logger.warning("fill 值被页面覆盖，重试 %d 次后仍未稳定: %s", retries, selector)

    # ------------------------------------------------------------------
    # 3. type_text
    # ------------------------------------------------------------------
    def type_text(self, selector: str, text: str, delay: float = 0.05) -> None:
        """逐字符输入文本，每个字符触发 keydown / keyup / input 事件。"""
        # 先聚焦并清空元素
        focus_script = (
            "(function() {"
            "  var el = document.querySelector(" + json.dumps(selector) + ");"
            "  if (!el) {"
            "    throw new Error('Element not found: ' + " + json.dumps(selector) + ");"
            "  }"
            "  el.focus();"
            "  el.value = '';"
            "  el.dispatchEvent(new Event('input', {bubbles: true}));"
            "  return true;"
            "})();"
        )
        self._controller.exec_js(focus_script)

        for char in text:
            char_script = (
                "(function() {"
                "  var el = document.querySelector(" + json.dumps(selector) + ");"
                "  if (!el) return;"
                "  el.dispatchEvent(new KeyboardEvent('keydown', {"
                "    key: " + json.dumps(char) + ", bubbles: true, cancelable: true"
                "  }));"
                "  el.value += " + json.dumps(char) + ";"
                "  el.dispatchEvent(new Event('input', {bubbles: true}));"
                "  el.dispatchEvent(new KeyboardEvent('keyup', {"
                "    key: " + json.dumps(char) + ", bubbles: true, cancelable: true"
                "  }));"
                "})();"
            )
            self._controller.run_js(char_script)
            time.sleep(delay)

        # 最终触发 change 事件
        change_script = (
            "(function() {"
            "  var el = document.querySelector(" + json.dumps(selector) + ");"
            "  if (el) { el.dispatchEvent(new Event('change', {bubbles: true})); }"
            "})();"
        )
        self._controller.run_js(change_script)

    # ------------------------------------------------------------------
    # 4. extract
    # ------------------------------------------------------------------
    def extract(self, selector: str, attribute: str = "text") -> list[str]:
        """提取匹配元素的数据。

        attribute 取值：
          - 'text'   → textContent
          - 'html'   → innerHTML
          - 'value'  → .value 属性
          - 其它     → getAttribute(name)
        """
        script = (
            "(function() {"
            "  var els = document.querySelectorAll(" + json.dumps(selector) + ");"
            "  var results = [];"
            "  var attr = " + json.dumps(attribute) + ";"
            "  for (var i = 0; i < els.length; i++) {"
            "    var el = els[i];"
            "    if (attr === 'text') {"
            "      results.push(el.textContent || '');"
            "    } else if (attr === 'html') {"
            "      results.push(el.innerHTML || '');"
            "    } else if (attr === 'value') {"
            "      results.push(el.value !== undefined ? el.value : '');"
            "    } else {"
            "      results.push(el.getAttribute(attr) || '');"
            "    }"
            "  }"
            "  return results;"
            "})();"
        )
        return self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 5. wait_for_selector
    # ------------------------------------------------------------------
    def wait_for_selector(
        self, selector: str, timeout: float = 10.0, interval: float = 0.5
    ) -> None:
        """轮询等待直到匹配选择器的元素出现，超时抛出 TimeoutError。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            check_script = (
                "(function() {"
                "  return !!document.querySelector(" + json.dumps(selector) + ");"
                "})();"
            )
            try:
                if self._controller.exec_js(check_script, timeout=min(5.0, timeout)):
                    return
            except Exception:
                pass  # JS 执行失败（如页面导航中），继续重试
            time.sleep(interval)
        raise TimeoutError(
            "等待选择器超时 (" + str(timeout) + "s): " + selector
        )

    # ------------------------------------------------------------------
    # 6. set_cookies
    # ------------------------------------------------------------------
    def set_cookies(self, cookies_dict: dict[str, str]) -> None:
        """通过 JS document.cookie 设置 cookies。"""
        for name, value in cookies_dict.items():
            script = (
                "(function() {"
                "  document.cookie = "
                + json.dumps(name) + " + '=' + " + json.dumps(value) + " + '; path=/';"
                "  return true;"
                "})();"
            )
            self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 7. get_cookies
    # ------------------------------------------------------------------
    def get_cookies(self) -> dict[str, str]:
        """通过 JS document.cookie 获取所有 cookies，解析为字典。"""
        script = "(function() { return document.cookie; })();"
        cookie_str: str = self._controller.exec_js(script)
        if not cookie_str:
            return {}

        result: dict[str, str] = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                key, _, value = item.partition("=")
                result[key.strip()] = value.strip()
        return result

    # ------------------------------------------------------------------
    # 8. override_dialogs
    # ------------------------------------------------------------------
    def override_dialogs(self, auto_confirm: bool = True) -> None:
        """覆盖 window.alert / confirm / prompt，捕获消息并自动响应。

        消息存储在 self._dialog_messages 中，通过 get_dialog_messages() 刷新获取。
        """
        self._dialog_messages = []
        confirm_response = "true" if auto_confirm else "false"
        script = (
            "(function() {"
            "  window._dialogMessages = [];"
            "  window.alert = function(msg) {"
            "    window._dialogMessages.push({"
            "      type: 'alert', message: String(msg)"
            "    });"
            "  };"
            "  window.confirm = function(msg) {"
            "    window._dialogMessages.push({"
            "      type: 'confirm', message: String(msg)"
            "    });"
            "    return " + confirm_response + ";"
            "  };"
            "  window.prompt = function(msg, defaultText) {"
            "    window._dialogMessages.push({"
            "      type: 'prompt', message: String(msg),"
            "      defaultText: defaultText || ''"
            "    });"
            "    return defaultText || '';"
            "  };"
            "  return true;"
            "})();"
        )
        self._controller.exec_js(script)

    def get_dialog_messages(self) -> list[dict]:
        """返回自上次 override_dialogs 调用以来捕获的对话框消息。"""
        script = "(function() { return window._dialogMessages || []; })();"
        msgs = self._controller.exec_js(script)
        if isinstance(msgs, list):
            self._dialog_messages = msgs
        return self._dialog_messages

    # ------------------------------------------------------------------
    # 9. screenshot
    # ------------------------------------------------------------------
    def screenshot(self, path: str) -> None:
        """使用 html2canvas 截图并保存为 PNG 文件。

        优先尝试从 CDN 加载 html2canvas，若失败则使用内置 DOM 导出作为 HTML 文件。
        """
        # 注入 html2canvas
        for cdn_url in [
            'https://unpkg.com/html2canvas@1.4.1/dist/html2canvas.min.js',
            'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js',
        ]:
            inject_script = (
                "(async function() {"
                "  if (typeof html2canvas !== 'undefined') return 'already';"
                "  return new Promise(function(resolve, reject) {"
                "    var s = document.createElement('script');"
                "    s.src = " + json.dumps(cdn_url) + ";"
                "    s.onload = function() { resolve('ok'); };"
                "    s.onerror = function() { resolve('fail'); };"
                "    document.head.appendChild(s);"
                "  });"
                "})();"
            )
            result = self._controller.exec_js(inject_script)
            if result == 'already' or result == 'ok':
                break

        # 检查 html2canvas 是否可用
        has_lib = self._controller.exec_js('typeof html2canvas')
        if has_lib != 'function':
            # 后备方案：导出 HTML 源码
            html = self._controller.exec_js('document.documentElement.outerHTML')
            html_path = path.rsplit('.', 1)[0] + '.html'
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write('<meta charset="utf-8">\n' + (html or ''))
            logger.warning('html2canvas 不可用，已保存 HTML 源码到: %s', html_path)
            return

        # 截图并获取 base64 data URL
        capture_script = (
            "(async function() {"
            "  var canvas = await html2canvas(document.body, {"
            "    allowTaint: true,"
            "    useCORS: true,"
            "    logging: false,"
            "  });"
            "  return canvas.toDataURL('image/png');"
            "})();"
        )
        data_url = self._controller.exec_js(capture_script)

        if not data_url or not isinstance(data_url, str) or "," not in data_url:
            raise RuntimeError("截图失败：未获取到有效图像数据")

        base64_data = data_url.split(",", 1)[1]
        with open(path, "wb") as f:
            f.write(base64.b64decode(base64_data))

    # ------------------------------------------------------------------
    # 9b. screenshot_element
    # ------------------------------------------------------------------
    def screenshot_element(self, selector: str, path: str) -> str:
        """截取指定元素的截图（通过 JS 获取元素位置，裁剪全页截图）。"""
        self.wait_for_selector(selector)
        # 获取元素位置和尺寸
        rect_script = (
            "(function() {"
            "  var el = document.querySelector(" + json.dumps(selector) + ");"
            "  if (!el) return null;"
            "  var r = el.getBoundingClientRect();"
            "  return JSON.stringify({x: r.x, y: r.y, w: r.width, h: r.height});"
            "})();"
        )
        rect_json = self._controller.exec_js(rect_script)
        if not rect_json:
            raise ValueError(f"无法获取元素位置: {selector}")
        import json as _json
        rect = _json.loads(rect_json) if isinstance(rect_json, str) else rect_json

        # 先截全页
        tmp_path = path + ".tmp.png"
        self.screenshot(tmp_path)

        # 用 PIL 裁剪
        try:
            from PIL import Image
            img = Image.open(tmp_path)
            # 缩放因子：pywebview 截图可能和实际像素不同
            scale_x = img.width / (rect["x"] + rect["w"] + 10)
            scale_y = img.height / (rect["y"] + rect["h"] + 10)
            # 简化：直接用实际像素
            cropped = img.crop((
                int(rect["x"]), int(rect["y"]),
                int(rect["x"] + rect["w"]), int(rect["y"] + rect["h"])
            ))
            cropped.save(path)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return path
        except ImportError:
            # 无 PIL，回退到全页截图
            if os.path.exists(tmp_path):
                os.rename(tmp_path, path)
            return path

    # ------------------------------------------------------------------
    # 9c. exec_js_async
    # ------------------------------------------------------------------
    def exec_js_async(self, script: str) -> None:
        """异步执行 JS，不等待返回值。"""
        self._controller.run_js(script)

    # ------------------------------------------------------------------
    # 10. login
    # ------------------------------------------------------------------
    def login(
        self,
        url: str,
        username: str,
        password: str,
        username_selector: str = (
            'input[name="username"], #username, input[type="email"]'
        ),
        password_selector: str = (
            'input[name="password"], #password, input[type="password"]'
        ),
        submit_selector: str = 'button[type="submit"], input[type="submit"]',
    ) -> None:
        """导航到登录页，填写凭据，点击提交，等待页面导航完成。"""
        self._controller.goto(url)

        self.wait_for_selector(username_selector)
        self.fill(username_selector, username)

        self.wait_for_selector(password_selector)
        self.fill(password_selector, password)

        self.wait_for_selector(submit_selector)
        self.click(submit_selector)

        self._controller.wait_loaded()

    # ------------------------------------------------------------------
    # 11. search
    # ------------------------------------------------------------------
    def search(
        self,
        url: str,
        query: str,
        input_selector: str,
        submit_selector: str | None = None,
    ) -> None:
        """导航到搜索页面，输入查询关键词并提交。

        若未提供 submit_selector，则模拟 Enter 键并尝试触发表单 submit 事件。
        """
        self._controller.goto(url)

        self.wait_for_selector(input_selector)
        self.fill(input_selector, query)

        if submit_selector:
            self.wait_for_selector(submit_selector)
            self.click(submit_selector)
        else:
            script = (
                "(function() {"
                "  var el = document.querySelector(" + json.dumps(input_selector) + ");"
                "  if (!el) return;"
                "  el.dispatchEvent(new KeyboardEvent('keydown', {"
                "    key: 'Enter', code: 'Enter', keyCode: 13, which: 13,"
                "    bubbles: true, cancelable: true"
                "  }));"
                "  el.dispatchEvent(new KeyboardEvent('keyup', {"
                "    key: 'Enter', code: 'Enter', keyCode: 13, which: 13,"
                "    bubbles: true, cancelable: true"
                "  }));"
                "  var form = el.closest('form');"
                "  if (form) {"
                "    form.dispatchEvent(new Event('submit', {"
                "      bubbles: true, cancelable: true"
                "    }));"
                "  }"
                "})();"
            )
            self._controller.exec_js(script)

        self._controller.wait_loaded()

    # ------------------------------------------------------------------
    # 12. get_dom_json
    # ------------------------------------------------------------------
    def get_dom_json(self) -> dict:
        """获取完整 DOM 树的 JSON 序列化表示。"""
        script = (
            "(function() {"
            "  function serializeNode(node) {"
            "    if (node.nodeType === 3) {"
            "      return {type: 'text', content: node.textContent || ''};"
            "    }"
            "    if (node.nodeType === 1) {"
            "      var obj = {"
            "        type: 'element',"
            "        tag: node.tagName.toLowerCase(),"
            "        attributes: {},"
            "        children: []"
            "      };"
            "      for (var i = 0; i < node.attributes.length; i++) {"
            "        var a = node.attributes[i];"
            "        obj.attributes[a.name] = a.value;"
            "      }"
            "      for (var i = 0; i < node.childNodes.length; i++) {"
            "        obj.children.push(serializeNode(node.childNodes[i]));"
            "      }"
            "      return obj;"
            "    }"
            "    return {type: 'other', nodeType: node.nodeType};"
            "  }"
            "  return serializeNode(document.documentElement);"
            "})();"
        )
        return self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 13. submit_form
    # ------------------------------------------------------------------
    def submit_form(self, form_selector: str) -> None:
        """通过 JS form.submit() 提交表单。"""
        script = (
            "(function() {"
            "  var form = document.querySelector(" + json.dumps(form_selector) + ");"
            "  if (!form) {"
            "    throw new Error('Form not found: ' + " + json.dumps(form_selector) + ");"
            "  }"
            "  form.submit();"
            "  return true;"
            "})();"
        )
        self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 14. select_option
    # ------------------------------------------------------------------
    def select_option(self, selector: str, value: str) -> None:
        """为 select 元素选择指定值（按 value 或 text 匹配）的选项。"""
        script = (
            "(function() {"
            "  var select = document.querySelector(" + json.dumps(selector) + ");"
            "  if (!select) {"
            "    throw new Error("
            "      'Select element not found: ' + " + json.dumps(selector)
            + "    );"
            "  }"
            "  var options = select.options;"
            "  var found = false;"
            "  for (var i = 0; i < options.length; i++) {"
            "    if (options[i].value === " + json.dumps(value)
            + " || options[i].text === " + json.dumps(value) + ") {"
            "      select.selectedIndex = i;"
            "      found = true;"
            "      break;"
            "    }"
            "  }"
            "  if (!found) {"
            "    throw new Error('Option not found: ' + " + json.dumps(value) + ");"
            "  }"
            "  select.dispatchEvent(new Event('change', {bubbles: true}));"
            "  return true;"
            "})();"
        )
        self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 15. hover
    # ------------------------------------------------------------------
    def hover(self, selector: str) -> None:
        """悬停在匹配元素上，触发 mouseenter/mouseover 事件。"""
        script = (
            "(function() {"
            "  var el = document.querySelector(" + json.dumps(selector) + ");"
            "  if (!el) { throw new Error('Element not found: ' + " + json.dumps(selector) + "); }"
            "  el.scrollIntoView({behavior: 'instant', block: 'center'});"
            "  el.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true, cancelable: true}));"
            "  el.dispatchEvent(new MouseEvent('mouseover', {bubbles: true, cancelable: true}));"
            "  return true;"
            "})();"
        )
        self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 16. scroll_to_selector
    # ------------------------------------------------------------------
    def scroll_to_selector(self, selector: str) -> None:
        """滚动到匹配元素的位置。"""
        script = (
            "(function() {"
            "  var el = document.querySelector(" + json.dumps(selector) + ");"
            "  if (!el) { throw new Error('Element not found: ' + " + json.dumps(selector) + "); }"
            "  el.scrollIntoView({behavior: 'smooth', block: 'center'});"
            "  return true;"
            "})();"
        )
        self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 17. scroll_by
    # ------------------------------------------------------------------
    def scroll_by(self, x: float = 0, y: float = 0) -> None:
        """按像素滚动页面。"""
        script = (
            "(function() {"
            "  window.scrollBy({left: " + json.dumps(float(x)) + ", top: " + json.dumps(float(y)) + ", behavior: 'smooth'});"
            "  return true;"
            "})();"
        )
        self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 18. press_key
    # ------------------------------------------------------------------
    def press_key(self, key: str, selector: str | None = None) -> None:
        """在指定元素或当前聚焦元素上模拟按键。"""
        target = "document.querySelector(" + json.dumps(selector) + ") || document.activeElement" if selector else "document.activeElement"
        script = (
            "(function() {"
            "  var el = " + target + ";"
            "  if (!el) { throw new Error('No active element to press key on'); }"
            "  var _key = " + json.dumps(key) + ";"
            "  var _kc = {Enter:13,Tab:9,Escape:27,Backspace:8,Delete:46,Home:36,End:35,PageUp:33,PageDown:34,ArrowUp:38,ArrowDown:40,ArrowLeft:37,ArrowRight:39,Space:32}[_key] || _key.charCodeAt(0) || 13;"
            "  el.dispatchEvent(new KeyboardEvent('keydown', {"
            "    key: _key, code: _key,"
            "    keyCode: _kc,"
            "    which: _kc,"
            "    bubbles: true, cancelable: true"
            "  }));"
            "  el.dispatchEvent(new KeyboardEvent('keypress', {"
            "    key: _key, code: _key,"
            "    keyCode: _kc,"
            "    which: _kc,"
            "    bubbles: true, cancelable: true"
            "  }));"
            "  el.dispatchEvent(new KeyboardEvent('keyup', {"
            "    key: _key, code: _key,"
            "    keyCode: _kc,"
            "    which: _kc,"
            "    bubbles: true, cancelable: true"
            "  }));"
            "  return true;"
            "})();"
        )
        self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 19. upload_file
    # ------------------------------------------------------------------
    def upload_file(self, selector: str, file_path: str) -> None:
        """尝试触发文件输入框的选择对话框。

        注意：pywebview 的 WebView2 出于安全限制不允许脚本设置
        <input type="file"> 的值，因此本方法只能触发系统文件选择
        对话框，文件路径必须由用户在对话框中手动选择。
        在隐藏窗口模式下对话框不可见，请使用可见窗口运行 upload。
        """
        script = (
            "(function() {"
            "  var el = document.querySelector(" + json.dumps(selector) + ");"
            "  if (!el) { throw new Error('File input not found: ' + " + json.dumps(selector) + "); }"
            "  if (el.type !== 'file') { throw new Error('Element is not a file input'); }"
            "  el.focus();"
            "  el.click();"
            "  return 'File dialog opened. NOTE: the file must be selected manually in the dialog; programmatic upload is not supported by WebView2: ' + " + json.dumps(file_path) + ";"
            "})();"
        )
        self._controller.exec_js(script)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def close(self) -> None:
        """关闭底层 BrowserController。"""
        self._controller.close()

    def __enter__(self) -> AutomationActions:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()