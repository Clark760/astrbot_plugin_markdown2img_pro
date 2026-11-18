# AstrBot Markdown / HTML 转图片插件

一个用于 AstrBot 的插件，允许 LLM 将复杂的 Markdown 或 HTML 内容转换为图片发送，提升消息的可读性。

## 功能特性

- ✅ **Markdown 转图片**：将包含代码块、表格、数学公式等复杂格式的 Markdown 内容转换为清晰图片
- ✅ **HTML 转图片**：通过 `ml` 命令让 LLM 生成 `<ml>...</ml>` HTML 并渲染为图片
- ✅ **LaTeX 数学公式支持**：通过 MathJax 完美渲染数学公式
- ✅ **自动浏览器安装**：插件自动安装和配置 Playwright Chromium 浏览器
- ✅ **指令触发注入**：仅在用户消息以 `md` 或 `/md` 开头时注入图片渲染提示
- ✅ **指令触发注入**：用户消息以 `ml` 或 `/ml` 开头时注入 HTML 图片渲染提示
- ✅ **全局标签转换**：任意回复中的 `<md>...</md>` 或 `<ml>...</ml>` 都会转换为图片发送
- ✅ **高清渲染**：支持 2 倍缩放，生成高质量图片
- ✅ **自适应宽度**：支持固定宽度或自适应宽度渲染

## 安装方法

### 前置要求

- Python 3.8+
- AstrBot 框架

### 安装步骤

1. 将插件文件夹放置到 AstrBot 的 `plugins` 目录下
2. 重启 AstrBot 服务
3. 插件会自动安装所需依赖（`mistune` 和 `playwright`）

## 使用方法

### 基本用法

只有当用户消息以 `md` 或 `/md` 开头时，插件才会向 LLM 注入 Markdown 转图片提示。例如：

```
/md 请用表格总结 Python 和 JavaScript 的区别
```

注入后，LLM 会将需要渲染成图片的 Markdown 内容包裹在 `<md>` 标签中。后续即使没有再次发送 `md` 指令，只要回复中出现 `<md>...</md>` 标签，插件也会自动转换为图片发送：

```
<md>
# 这是一个标题

这是一个列表:
- 列表项 1
- 列表项 2

这是一个代码块:
```python
def hello_world():
    print("Hello, World!")
```
</md>
```

插件会自动识别并渲染成图片发送。

聊天上下文中保留的是 LLM 原始输出的 `<md>...</md>` Markdown 文本，发送阶段才会替换成图片，便于非多模态模型在后续对话中继续理解内容。

### HTML 转图片

使用 `ml` 或 `/ml` 命令让 LLM 生成 HTML 图片：

```
/ml 请生成一张展示本周计划的精美卡片
```

模型会把 HTML 文档或片段放入 `<ml>` 标签中：

```html
<ml>
<style>
  .card { padding: 24px; background: #f5f7fb; color: #223; }
</style>
<div class="card">
  <h1>本周计划</h1>
  <p>完成项目开发与测试。</p>
</div>
</ml>
```

为保证安全和稳定，HTML 渲染时不会执行 JavaScript，也不会加载外部样式、字体或图片。

### 支持的 Markdown 语法

- ✅ 标题（#、##、###）
- ✅ 列表（有序、无序）
- ✅ 代码块（语法高亮）
- ✅ 表格
- ✅ 数学公式（LaTeX）
- ✅ 粗体、斜体、删除线
- ✅ 引用块
- ✅ 水平分割线

### 数学公式示例

```
<md>
行内公式：$a^2 + b^2 = c^2$

独立公式：
$$
\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$
</md>
```

## 配置说明

### 插件配置

插件的配置文件位于 `metadata.yaml`：

```yaml
name: astrbot_plugin_markdown2img
desc: 允许 LLM 将 Markdown 或 HTML 文本转换为图片发送。
version: v1.1.0
author: tosaki
repo: https://github.com/t0saki/astrbot_plugin_markdown2img
```

### 依赖包

- `mistune`: Markdown 解析器
- `playwright`: 浏览器自动化工具（用于渲染）

## 技术实现

### 渲染流程

1. **解析 Markdown**：使用 `mistune` 将 Markdown 转换为 HTML
2. **数学公式处理**：通过 MathJax 渲染 LaTeX 公式
3. **浏览器渲染**：使用 Playwright Chromium 浏览器截图
4. **图片生成**：生成 PNG 格式的高清图片

### 图片缓存

生成的图片存储在插件数据目录下的 `md2img_cache/` 中，使用 UUID 文件名。插件启动时检查缓存，随后每小时检查一次，删除修改时间超过 24 小时的 UUID 格式 PNG 文件。

## 备注

首次安装依赖较多，会在后台异步安装依赖，请在控制台中跟踪进度。
