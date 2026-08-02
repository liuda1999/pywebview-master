# 修复五大功能缺陷 Spec

## Why
browser-cli 存在五个核心功能缺陷：不支持多窗口、动态内容抓取、多步表单填写、直接登录、搜索结果提取。需要逐一修复。

## What Changes
- **修复1**: 支持 `--concurrent` 模式多窗口管理
- **修复2**: extract 命令增加 `--wait-dynamic` 和 `--wait-selector` 支持动态/SPA 内容
- **修复3**: CLI 增加 `fill-steps` 命令支持多步表单（多个窗口/分页填写）
- **修复4**: CLI 增加 `login` 命令直接登录网站
- **修复5**: search 命令增加 `--extract-result` 选项提取搜索结果

## Impact
- Affected specs: browser-automation-cli, web-ui
- Affected code: `browser_cli/cli.py`, `browser_cli/controller.py`, `browser_cli/actions.py`

## ADDED Requirements

### Requirement: 多窗口管理
系统 SHALL 支持在单个 session 中打开和管理多个 WebView 窗口。

#### Scenario: 打开多个窗口
- **WHEN** 执行 `browser-cli multi-window --windows 3 --urls "url1,url2,url3"`
- **THEN** 系统同时创建3个窗口，分别导航到对应 URL

### Requirement: 动态内容抓取
系统 SHALL 支持等待动态内容加载完成后抓取。

#### Scenario: 等待动态元素后抓取
- **WHEN** 执行 `browser-cli extract ".result" --url "https://spa.example.com" --wait-selector ".loaded" --wait-dynamic 5`
- **THEN** 系统导航后等待 `.loaded` 元素出现，再等待 5秒（动态渲染），然后提取 `.result`

### Requirement: 多步表单填写
系统 SHALL 支持在同页面内执行多步表单操作。

#### Scenario: 多步表单
- **WHEN** 执行 `browser-cli fill-steps --url "..." --step "fill:#name:张三" --step "fill:#age:25" --step "click:#next" --step "fill:#city:北京" --step "click:#submit"`
- **THEN** 系统按顺序执行每步操作，支持 fill/click/wait/type/extract 等动作

### Requirement: 登录命令
系统 SHALL 提供 `login` CLI 命令，支持直接登录网站并返回登录后页面内容。

#### Scenario: 直接登录
- **WHEN** 执行 `browser-cli login --url "https://example.com/login" --username "admin" --password "123456" --extract ".dashboard"`
- **THEN** 系统完成登录流程并提取登录后页面内容

### Requirement: 搜索结果提取
系统 SHALL 在 search 命令完成后提取搜索结果。

#### Scenario: 搜索并提取结果
- **WHEN** 执行 `browser-cli search --url "https://google.com" --query "pywebview" --input "input[name='q']" --extract-result ".g" --format json`
- **THEN** 系统搜索完成后等待结果加载，然后提取搜索结果