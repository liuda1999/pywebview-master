# 功能差距分析 - 验证清单

## P0 - 基础操作补全

- [x] P0.1: hover 命令可正常执行，元素触发 mouseenter/mouseover 事件
- [x] P0.2: scroll-to 命令可滚动到指定元素，scroll-down 命令可按像素滚动
- [x] P0.3: press 命令可模拟按键（Enter、Tab、Escape 等）并触发对应事件
- [x] P0.4: wait-for-timeout 命令可等待指定毫秒数
- [x] P0.5: wait-for-url 命令可轮询等待 URL 匹配 glob 模式
- [x] P0.6: snapshot 命令可输出页面可见文本和关键 DOM 结构
- [x] P0.7: upload 命令可设置文件输入框并通过 JS 触发 change 事件
- [x] P0.8: fill-steps 命令支持 hover、scroll、press、upload、snapshot 操作类型

## P1 - 环境与诊断

- [x] P1.1: doctor 命令可检测 Python 版本、pywebview 依赖、WebView2 可用性并给出修复建议
- [x] P1.2: browsers 命令可列出系统已安装的 Edge/Chrome/Firefox 浏览器及版本

## P2 - 截图增强

- [x] P2.1: screenshot --selector 可截取指定元素的截图

## P3 - 录制与回放

- [x] P3.1: record 命令可启动浏览器并录制用户操作到 JSON 文件
- [x] P3.2: replay 命令可回放 JSON 操作序列，支持 --speed 调节速度

## P4 - 批量执行与 CI/CD

- [x] P4.1: batch 命令可从文件逐行读取 URL 或命令并批量执行
- [x] P4.2: BROWSER_CLI_TIMEOUT 等环境变量可覆盖默认配置

## P5 - 导出 PDF

- [x] P5.1: pdf 命令可通过浏览器打印 API 导出 PDF 文件