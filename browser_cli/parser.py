"""ContentParser — 结构化数据提取器，从浏览器页面中提取链接、表格、表单等数据。"""

from __future__ import annotations

import csv
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 内联 JS 工具函数（减少 exec_js 往返次数）
# ---------------------------------------------------------------------------

_JS_TO_JSON = """
function __py_to_json__(value) {
    if (value === undefined) return null;
    if (value === null) return null;
    try { return JSON.parse(JSON.stringify(value)); } catch(_) { return null; }
}
"""


class ContentParser:
    """从 BrowserController 实例中提取结构化数据。"""

    def __init__(self, controller: Any) -> None:
        self._controller = controller

    # ------------------------------------------------------------------
    # 1. 链接
    # ------------------------------------------------------------------

    def get_links(self) -> list[dict]:
        """提取页面所有链接，返回 [{'href', 'text', 'title', 'target'}, ...]."""
        script = (
            _JS_TO_JSON
            + """
            (function() {
                var links = document.querySelectorAll('a');
                var result = [];
                for (var i = 0; i < links.length; i++) {
                    var a = links[i];
                    result.push({
                        href: a.href || '',
                        text: (a.textContent || '').trim(),
                        title: a.title || '',
                        target: a.target || ''
                    });
                }
                return __py_to_json__(result);
            })()
            """
        )
        try:
            raw = self._controller.exec_js(script)
            return raw if isinstance(raw, list) else []
        except Exception as exc:
            logger.error("get_links 失败: %s", exc)
            return []

    # ------------------------------------------------------------------
    # 2. 表格
    # ------------------------------------------------------------------

    def get_tables(self, selector: str = 'table') -> list[list[list[str]]]:
        """提取匹配 CSS 选择器的所有表格。每个表格为 list[list[str]]。"""
        # 将选择器安全地嵌入 JS 字符串
        escaped_selector = selector.replace("\\", "\\\\").replace("'", "\\'")
        script = (
            _JS_TO_JSON
            + f"""
            (function() {{
                var tables = document.querySelectorAll('{escaped_selector}');
                var result = [];
                for (var t = 0; t < tables.length; t++) {{
                    var table = tables[t];
                    var tableData = [];
                    var rows = table.querySelectorAll('tr');
                    for (var r = 0; r < rows.length; r++) {{
                        var row = rows[r];
                        var rowData = [];
                        var cells = row.querySelectorAll('th, td');
                        for (var c = 0; c < cells.length; c++) {{
                            rowData.push((cells[c].textContent || '').trim());
                        }}
                        tableData.push(rowData);
                    }}
                    result.push(tableData);
                }}
                return __py_to_json__(result);
            }})()
            """
        )
        try:
            raw = self._controller.exec_js(script)
            return raw if isinstance(raw, list) else []
        except Exception as exc:
            logger.error("get_tables 失败: %s", exc)
            return []

    # ------------------------------------------------------------------
    # 3. 可见文本
    # ------------------------------------------------------------------

    def get_all_text(self, selector: str = 'body') -> str:
        """获取匹配元素的可见文本，规范化空白字符。"""
        escaped_selector = selector.replace("\\", "\\\\").replace("'", "\\'")
        script = f"""
            (function() {{
                var el = document.querySelector('{escaped_selector}');
                if (!el) return '';
                var text = el.innerText || el.textContent || '';
                return text.replace(/\\s+/g, ' ').trim();
            }})()
        """
        try:
            raw = self._controller.exec_js(script)
            return str(raw) if raw else ''
        except Exception as exc:
            logger.error("get_all_text 失败: %s", exc)
            return ''

    # ------------------------------------------------------------------
    # 4. Meta 标签
    # ------------------------------------------------------------------

    def get_meta_tags(self) -> dict[str, str]:
        """提取所有 meta 标签，返回 {name 或 property: content, ...}。"""
        script = (
            _JS_TO_JSON
            + """
            (function() {
                var metas = document.querySelectorAll('meta');
                var result = {};
                for (var i = 0; i < metas.length; i++) {
                    var m = metas[i];
                    var key = m.getAttribute('name') || m.getAttribute('property') || m.getAttribute('http-equiv');
                    var content = m.getAttribute('content');
                    if (key && content) {
                        result[key] = content;
                    }
                }
                return __py_to_json__(result);
            })()
            """
        )
        try:
            raw = self._controller.exec_js(script)
            return raw if isinstance(raw, dict) else {}
        except Exception as exc:
            logger.error("get_meta_tags 失败: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # 5. 正则过滤（列表）
    # ------------------------------------------------------------------

    @staticmethod
    def filter_by_regex(items: list[str], pattern: str) -> list[str]:
        """在字符串列表中按正则模式过滤，返回匹配项。"""
        try:
            compiled = re.compile(pattern)
            return [item for item in items if compiled.search(item)]
        except re.error as exc:
            logger.error("filter_by_regex 正则错误: %s", exc)
            return []

    # ------------------------------------------------------------------
    # 6. 正则过滤（DOM 元素属性）
    # ------------------------------------------------------------------

    def filter_elements_by_regex(
        self, selector: str, attribute: str, pattern: str
    ) -> list[str]:
        """查找匹配 selector 的元素，提取 attribute 属性值，按正则过滤后返回。"""
        escaped_selector = selector.replace("\\", "\\\\").replace("'", "\\'")
        escaped_attribute = attribute.replace("\\", "\\\\").replace("'", "\\'")
        script = (
            _JS_TO_JSON
            + f"""
            (function() {{
                var els = document.querySelectorAll('{escaped_selector}');
                var values = [];
                for (var i = 0; i < els.length; i++) {{
                    var v = els[i].getAttribute('{escaped_attribute}');
                    if (v !== null && v !== undefined) {{
                        values.push(v);
                    }}
                }}
                return __py_to_json__(values);
            }})()
            """
        )
        try:
            raw = self._controller.exec_js(script)
            if not isinstance(raw, list):
                return []
            compiled = re.compile(pattern)
            return [str(v) for v in raw if compiled.search(str(v))]
        except re.error as exc:
            logger.error("filter_elements_by_regex 正则错误: %s", exc)
            return []
        except Exception as exc:
            logger.error("filter_elements_by_regex 失败: %s", exc)
            return []

    # ------------------------------------------------------------------
    # 7. 导出文件
    # ------------------------------------------------------------------

    @staticmethod
    def save_to_file(data: Any, format: str, path: str) -> str:
        """将数据保存到文件。format: 'json' | 'csv' | 'txt'。返回文件路径。"""
        if not path:
            raise ValueError("path 不能为空")

        fmt = format.lower().strip()

        if fmt == 'json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return path

        elif fmt == 'csv':
            with open(path, 'w', encoding='utf-8', newline='') as f:
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    # list of dicts
                    fieldnames = list({k for row in data for k in row})
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    # list of lists
                    writer = csv.writer(f)
                    writer.writerows(data)
                else:
                    # 兜底：单行写入
                    writer = csv.writer(f)
                    if isinstance(data, list):
                        writer.writerows([[item] for item in data])
                    else:
                        writer.writerow([data])
            return path

        elif fmt == 'txt':
            with open(path, 'w', encoding='utf-8') as f:
                if isinstance(data, list):
                    for item in data:
                        f.write(str(item) + '\n')
                else:
                    f.write(str(data) + '\n')
            return path

        else:
            raise ValueError(f"不支持的格式: {format!r}，请使用 'json'、'csv' 或 'txt'")

    # ------------------------------------------------------------------
    # 8. 表单
    # ------------------------------------------------------------------

    def get_forms(self) -> list[dict]:
        """提取页面所有表单，返回 [{'action', 'method', 'id', 'inputs': [...]}, ...]."""
        script = (
            _JS_TO_JSON
            + """
            (function() {
                var forms = document.querySelectorAll('form');
                var result = [];
                for (var i = 0; i < forms.length; i++) {
                    var f = forms[i];
                    var inputs = f.querySelectorAll('input, textarea, select, button');
                    var inputList = [];
                    for (var j = 0; j < inputs.length; j++) {
                        var inp = inputs[j];
                        var name = inp.getAttribute('name') || inp.id || '';
                        var type = inp.getAttribute('type') || inp.tagName.toLowerCase();
                        inputList.push({name: name, type: type});
                    }
                    result.push({
                        action: f.action || '',
                        method: (f.method || 'GET').toUpperCase(),
                        id: f.id || '',
                        inputs: inputList
                    });
                }
                return __py_to_json__(result);
            })()
            """
        )
        try:
            raw = self._controller.exec_js(script)
            return raw if isinstance(raw, list) else []
        except Exception as exc:
            logger.error("get_forms 失败: %s", exc)
            return []

    # ------------------------------------------------------------------
    # 9. 图片
    # ------------------------------------------------------------------

    def get_images(self) -> list[dict]:
        """提取页面所有图片，返回 [{'src', 'alt'}, ...]."""
        script = (
            _JS_TO_JSON
            + """
            (function() {
                var imgs = document.querySelectorAll('img');
                var result = [];
                for (var i = 0; i < imgs.length; i++) {
                    var img = imgs[i];
                    result.push({
                        src: img.src || '',
                        alt: img.alt || ''
                    });
                }
                return __py_to_json__(result);
            })()
            """
        )
        try:
            raw = self._controller.exec_js(script)
            return raw if isinstance(raw, list) else []
        except Exception as exc:
            logger.error("get_images 失败: %s", exc)
            return []