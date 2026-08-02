# browser-cli 常见问题与排障经验

> 本文档沉淀真实环境中踩过的坑与排查方法论，重点是**动态渲染网页**
> （SPA、异步初始化、反自动化页面）相关的三类问题。
>
> 凡是遇到「元素存在但不可见」「填了值界面却看不到」「窗口创建了但用户
> 看不见」这类症状，先读第 2 节的五步定位法，再对照第 1 节已知问题。

---

## 1. 已知问题与解决方案

### 1.1 窗口创建成功但用户看不到（IsWindowVisible = False）

**症状**

- 服务/API 全部正常，WebView2 渲染进程存在，页面加载、提取、填写全通
- 桌面上就是看不到窗口；`IsWindowVisible()` 返回 False

**根因**

- 进程被以 `STARTUPINFO.wShowWindow = SW_HIDE` 的启动标志拉起时，
  WinForms 窗口首次 `Show()` 会继承该隐藏标志（`ShowWindow(SW_SHOWDEFAULT)`）
- .NET 侧 `Visible=True`，但 Win32 层 `IsWindowVisible=False`，两者脱节

**定位方法**

1. 用 `EnumDesktopWindows` + `GetWindowText` + `IsWindowVisible` 枚举窗口
   （注意：`FindWindow` / `EnumWindows` 只搜调用线程所在桌面，在隔离环境
   会漏报；显式打开 `WinSta0\Default` 桌面枚举才可靠）
2. 进程内对窗口句柄调 `ShowWindow(hwnd, SW_SHOW)`，若 visible 变为 True
   即确认是启动标志抑制

**解决方案**

- 使用 `scripts/run_visible.py` 包装启动命令（自动轮询解除隐藏）：

  ```bash
  python scripts/run_visible.py webui --port 8125 --max-windows 1
  ```

- 或在自己的启动代码里：窗口创建后对句柄调 `ShowWindow(hwnd, 5)`。

### 1.2 fill 填入的值被页面清空（SPA 异步初始化覆盖）

**症状**

- `fill` 返回成功，立即 `extract` 验证 value 正确
- 几秒后 value 被清空/重置，界面上看不到输入内容

**根因**

- 页面 `load` 事件之后仍有异步初始化（React 挂载、输入框重绘等），
  会把刚填入的值覆盖掉；`goto` 的「loaded + 1 秒」等待不足以覆盖全部初始化

**定位方法**

- fill 后隔 2~5 秒再次 `extract`，若值已丢失即为本问题
- 观察页面初始化结束前 DOM 是否被重建（`document.readyState` 之外还要
  看元素是否被替换：记录元素的引用是否仍然有效）

**解决方案**

- `actions.fill` 已内置「填入后轮询验证 + 自动重填」
  （`retries=6, retry_delay=0.7`）：值被覆盖则每 0.7 秒重填一次，
  直到页面稳定后值保留；所有调用方（fill-form / fill-steps / 剧本 /
  webui API）自动受益
- 观察点：fill 耗时 = 首次写入 + 验证轮询时长，正常应为秒级

### 1.3 搜索框/表单不可见（display:none 反自动化，如百度 virtual-form）

**症状**

- 页面主体正常（新闻、热搜、导航都在），但搜索框/表单区域不可见
- DOM 查询有元素，`getBoundingClientRect()` 返回 0x0
- computed style 显示 `display:none`（通常在 form 或某个上层容器上）

**根因**

- 网站针对嵌入式 WebView/特殊 UA 环境渲染「无表单版本」：
  百度首页会给 WebView2 返回 `form.fm.virtual-form`，用 CSS
  `display:none` 隐藏整个搜索表单，页面其余部分正常
- DOM 值无论怎么填都在隐藏容器里，界面上永远看不到

**定位方法**

- 用 exec_js 检查目标元素祖先链上所有节点的 `display`（见 3.2 脚本）：
  找到 `display:none` 的祖先即根因

**解决方案**

- `actions.fill` 已内置「恢复隐藏祖先」逻辑：填值前遍历祖先链
  （深度 8），把 `display:none` 的节点强制置为 `block`
- 注意：该逻辑只对表单/容器场景安全；如需操作 tab 面板等故意隐藏的
  内容，请自行控制

---

### 1.4 多窗口（--max-windows N）下窗口列表/切换/导航全部卡死

症状：控制面板窗口列表只显示 1 个窗口；exec_js / 切换 / 导航请求挂起
20 秒后报 'Main window failed to start'；启动到"窗口已就绪"要 15 秒。

根因：pywebview 6.2.1 + pythonnet 在 Windows 上创建多个 WebView2 控件时，
WebView2 控件的 NavigationCompleted 事件不会派发（单窗口正常）。导致
loaded / _pywebviewready 事件永不触发，evaluate_js / get_current_url 等
跨线程 API 在等待 20 秒后抛 WebViewException('Main window failed to start')。

另：Windows 上多个进程可同时监听同一端口（SO_REUSEADDR），残留的旧
webui 进程会让控制台请求被随机路由到旧实例，造成窗口列表不更新、切换后
active_index "回跳"到 0。

解决：
1. 先清理残留进程，确保只有一个 webui 实例在监听：
   taskkill /F /IM python.exe /FI "WINDOWTITLE eq GDI+ Window (python.exe)*"
2. 多窗口补偿补丁已内置：browser_cli/patches.py 在 WindowPool 多窗口
   （max_windows > 1）时自动 hook on_webview_ready，在 WebView2 初始化
   成功后手动触发导航完成流程，loaded/ready 正常置位，所有 API 恢复。
   单窗口场景不启用补丁，保持 pywebview 原行为。

验证：3 窗口启动 1 秒内就绪，/api/windows 立即返回 3 个窗口，exec_js /
切换秒回，goto 真实页面 3 秒内加载完成。

复现脚本：testcases/repro_2win_hook.py（事件派发诊断）、
repro_2win_comp.py（补偿方案验证）。

## 2. 动态渲染网页快速定位方法论（五步法）

核心思想：**DOM 值、可见性、祖先链、初始化时序、真实渲染画面**是五个
独立维度，任何一个都可能单独出问题。按顺序排查，每步都有确定答案。

### 第 1 步：DOM 值 vs 界面显示分离检查

先确认「值在不在」与「看不看得见」是否分离：

```js
// 输入框状态探测（value / 属性 / 框架键 / 焦点 / 尺寸）
(function(){
  var el = document.querySelector('#kw');
  if (!el) return 'NO EL';
  var rk = Object.keys(el).filter(function(k){return k.indexOf('__reactProps')===0||k.indexOf('__reactFiber')===0});
  var r = el.getBoundingClientRect();
  return JSON.stringify({
    value: el.value,
    attrValue: el.getAttribute('value'),
    reactKeys: rk,
    rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
    focused: document.activeElement === el
  });
})();
```

判定：

- value 正确 + rect 正常尺寸 -> 界面必然显示（非受控 input 的 UI 直接
  反映 value），用户还看不到 -> 检查用户是否在看别的窗口（第 5 步）
- value 正确 + rect 0x0 -> 元素被隐藏 -> 走第 3 步查祖先链
- value 被清空 -> 走第 4 步查初始化时序

### 第 2 步：区分受控组件与非受控组件

- `__reactProps` / `__reactFiber` / `__vue__` 键存在 -> React/Vue 受控
  组件，必须用**原生 value setter**（`Object.getOwnPropertyDescriptor(
  HTMLInputElement.prototype, 'value').set`）才能让框架感知
- 普通 input -> 直接 `el.value = x` 即可，`actions.fill` 两种情况都已处理

### 第 3 步：祖先链 display 检查（隐藏容器）

```js
(function(){
  var el = document.querySelector('#kw');
  var chain = [];
  while (el && chain.length < 8) {
    var cs = getComputedStyle(el);
    var r = el.getBoundingClientRect();
    chain.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
      ' d=' + cs.display + ' rect=' + Math.round(r.width) + 'x' + Math.round(r.height));
    el = el.parentElement;
  }
  return JSON.stringify(chain);
})();
```

任一祖先 `d=none` 即根因（如百度 `form#form d=none`）。

### 第 4 步：初始化时序（fill 值被覆盖）

- `goto` 返回 != 页面 JS 初始化完成；`readyState=complete` 也不是终点
- 验证手段：fill 后 2~5 秒反复 extract，观察值是否丢失
- 缓解：`actions.fill` 的验证+重填兜底；必要时在 fill 前加
  `wait-for-timeout 2000` 或先等待目标元素稳定

### 第 5 步：真实渲染画面实证（用户视角）

DOM 一切正常但用户说看不到时，必须拿「真实屏幕画面」说话：

- 截取窗口：PowerShell `BitBlt` 截窗口 rect 的屏幕区域（见 3.5），
  保存 PNG 后交给用户确认；注意 **GPU 合成窗口（WebView2）用 BitBlt
  可能截到黑屏**，这是截取方式问题，不代表窗口真的黑
- 桌面窗口盘点：`Get-Process | Where-Object {$_.MainWindowTitle}`，
  排除用户在看别的浏览器窗口（如桌面同时开着 Chrome 的相同站点）
- 窗口可见性验证：`EnumDesktopWindows(WinSta0\Default)` 显式枚举，
  见 1.1

---

## 3. exec_js 诊断脚本速查

以下脚本通过 webui 的 `/api/exec_js` 或 `exec_js` 方法执行。

### 3.1 页面所有可见 input 列表

```js
(function(){
  var els = document.querySelectorAll('input');
  var out = [];
  for (var i = 0; i < els.length; i++) {
    var el = els[i], r = el.getBoundingClientRect();
    if (r.width > 0 || r.height > 0) {
      out.push({id: el.id, name: el.name, cls: (el.className||'').slice(0,30),
        val: el.value.slice(0,20), rect: [Math.round(r.width), Math.round(r.height)]});
    }
  }
  return JSON.stringify(out);
})();
```

### 3.2 CSS 加载状态（样式表是否完整）

```js
(function(){
  var ss = document.styleSheets;
  var rules = 0, failed = [];
  for (var i = 0; i < ss.length; i++) {
    try { var r = ss[i].cssRules; if (r) rules += r.length; }
    catch (e) { failed.push(ss[i].href || '(inline)'); }
  }
  return JSON.stringify({sheetCount: ss.length, totalRules: rules, failedSheets: failed});
})();
```

样式表数量/规则数为 0 或大量 failed -> 资源加载问题（网络/证书/代理），
页面会呈现为无样式的裸 HTML。

### 3.3 页面/框架/UA 状态

```js
JSON.stringify({
  url: location.href,
  ready: document.readyState,
  title: document.title,
  ua: navigator.userAgent,
  viewport: window.innerWidth + 'x' + window.innerHeight,
  docH: document.documentElement.scrollHeight
});
```

### 3.4 窗口截图（PowerShell，真实屏幕像素）

```powershell
# 窗口句柄：Get-Process -Id <pid> | Select MainWindowHandle
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class Cap {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern IntPtr GetDC(IntPtr h);
  [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr h, IntPtr dc);
  [DllImport("gdi32.dll")] public static extern IntPtr CreateCompatibleDC(IntPtr hdc);
  [DllImport("gdi32.dll")] public static extern IntPtr CreateCompatibleBitmap(IntPtr hdc, int w, int h);
  [DllImport("gdi32.dll")] public static extern IntPtr SelectObject(IntPtr hdc, IntPtr obj);
  [DllImport("gdi32.dll")] public static extern bool BitBlt(IntPtr hdc, int x, int y, int w, int h, IntPtr src, int sx, int sy, uint rop);
  [DllImport("gdi32.dll")] public static extern bool DeleteDC(IntPtr h);
  [DllImport("gdi32.dll")] public static extern bool DeleteObject(IntPtr h);
}
public struct R { public int L; public int T; public int Rt; public int B; }
'@
$h = [IntPtr]2689224   # 换成实际 MainWindowHandle
$r = New-Object R; [Cap]::GetWindowRect($h,[ref]$r)|Out-Null
$w = $r.Rt-$r.L; $ht = $r.B-$r.T
$src = [Cap]::GetDC([IntPtr]::Zero); $mem = [Cap]::CreateCompatibleDC($src)
$bmp = [Cap]::CreateCompatibleBitmap($src,$w,$ht)
$old = [Cap]::SelectObject($mem,$bmp)
[Cap]::BitBlt($mem,0,0,$w,$ht,$src,$r.L,$r.T,0x00CC0020)|Out-Null
[Cap]::SelectObject($mem,$old)|Out-Null
$img = [System.Drawing.Image]::FromHbitmap($bmp)
$img.Save('C:\temp\win_shot.png',[System.Drawing.Imaging.ImageFormat]::Png)
```

### 3.5 窗口可见性枚举（PowerShell，显式桌面）

```powershell
# 枚举 WinSta0\Default 桌面全部顶层窗口（含隐藏），输出标题+可见性
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public class DP {
  public delegate bool EnumWinProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern IntPtr OpenDesktop(string n, uint f, bool i, uint a);
  [DllImport("user32.dll")] public static extern bool EnumDesktopWindows(IntPtr d, EnumWinProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
}
'@
$d = [DP]::OpenDesktop('Default',0,$false,0x0100)
$wproc = [DP+EnumWinProc]{ param($h,$l)
  $t = New-Object System.Text.StringBuilder 128
  [DP]::GetWindowText($h,$t,128)|Out-Null
  if ($t.ToString() -ne '') { $t.ToString() + ' | visible=' + [DP]::IsWindowVisible($h) }
  return $true
}
[DP]::EnumDesktopWindows($d,$wproc,[IntPtr]::Zero)|Out-Null
```

---

## 4. 环境特性备忘

| 现象 | 说明 |
|------|------|
| 截图 API 返回 0 字节 PNG | webui 的 screenshot 依赖 html2canvas（JS 注入 CDN 脚本）；CDN 不可用时降级导出 HTML 源码，PNG 为空。需要真实画面时用 3.4 的 BitBlt 方案 |
| BitBlt 截 WebView2 窗口全黑 | GPU 合成窗口从屏幕 DC 直截会得到黑块，不代表窗口真的黑；可改用 PrintWindow(PW_RENDERFULLCONTENT) |
| FindWindow/EnumWindows 找不到窗口 | 这两个 API 只搜调用线程所在桌面；隔离/沙箱环境必须用 EnumDesktopWindows 显式打开 WinSta0\Default |
| 百度首页 form 带 `virtual-form` class | 百度对嵌入式 WebView 渲染无表单版本；`actions.fill` 会自动恢复 form 显示，见 1.3 |
| SPA 输入框被清空 | 页面异步初始化覆盖，`actions.fill` 自动重填，见 1.2 |
| 窗口不可见但服务正常 | 启动标志 SW_HIDE 抑制，用 `scripts/run_visible.py`，见 1.1 |

---

## 5. 一次完整的排查样例（百度首页 fill rest 案例）

问题链（三层叠加，逐层暴露）：

1. webui 启动后桌面看不到窗口
   -> 枚举桌面：窗口在 WinSta0\Default，`IsWindowVisible=False`
   -> 根因：启动标志 SW_HIDE -> 解决：run_visible.py 强制显示

2. 窗口可见后，搜索框里没有输入内容
   -> fill 后立即 extract 返回正确，几秒后被清空
   -> 根因：百度 load 后异步初始化重绘输入框
   -> 解决：fill 加验证+重填

3. 重填后界面仍然看不到搜索框（页面其他内容正常）
   -> 探测 #kw rect = 0x0，祖先链 `form#form d=none`
   -> 根因：百度对 WebView2 返回 virtual-form，表单被 CSS 隐藏
   -> 解决：fill 自动恢复祖先 display

最终：goto 百度 -> fill rest -> 搜索框 547x43 正常显示、值稳定保持。
