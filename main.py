import os
import re
import time
import uuid
from typing import List


from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.message.components import Image, Plain
from astrbot.core.provider.entities import LLMResponse, ProviderRequest
from astrbot.core.star.star_tools import StarTools

# 确保你已经安装了 mistune 和 playwright
import mistune
import asyncio
from playwright.async_api import async_playwright
import uuid

import subprocess
import sys


async def markdown_to_image_playwright(
    md_text: str,
    output_image_path: str,
    scale: int = 2,
    width: int = None
):
    """
    使用 Playwright 将包含 LaTeX 的 Markdown 转换为图片。

    :param md_text: Markdown 格式的字符串。
    :param output_image_path: 图片输出路径。
    :param scale: 渲染的缩放因子。大于 1 的值可以有效提升清晰度和抗锯齿效果。
    :param width: 图片内容的固定宽度（单位：像素）。如果为 None，则宽度自适应内容。
    """
    # 1. 根据是否提供了 width 参数，动态生成 body 的宽度样式
    width_style = ""
    if width:
        # box-sizing: border-box 可确保 padding 包含在设定的 width 内
        width_style = f"width: {width}px; box-sizing: border-box;"

    # 2. 改进的 HTML 模板，为 body 样式增加了一个占位符 {width_style}
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Markdown Render</title>
        <style>
            body {{
                {width_style} /* 宽度样式将在这里注入 */
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
                padding: 25px;
                display: inline-block; /* 让截图尺寸自适应内容 */
                font-size: 16px;

                /* 开启更平滑的字体渲染 */
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
                text-rendering: optimizeLegibility;
            }}
            /* 为代码块添加一些样式 */
            pre {{
                background-color: #f6f8fa;
                border-radius: 6px;
                padding: 16px;
                overflow: auto;
                font-size: 85%;
                line-height: 1.45;
            }}
            code {{
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            }}
            .MathJax_Display {{
                max-width: 100%;
                overflow: visible;
            }}
            .mjx-chtml {{
                max-width: 100%;
            }}
            .mathjax-overflow-fallback {{
                transform-origin: left center;
            }}
        </style>
        <script type="text/javascript" async
            src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-MML-AM_CHTML">
        </script>
        <script type="text/x-mathjax-config">
            MathJax.Hub.Config({{
                tex2jax: {{
                    inlineMath: [['$','$']],
                    displayMath: [['$$','$$']],
                }},
                "HTML-CSS": {{
                    scale: 100,
                    linebreaks: {{ automatic: true, width: "container" }}
                }},
                CommonHTML: {{
                    scale: 100,
                    linebreaks: {{ automatic: true, width: "container" }}
                }},
                SVG: {{ linebreaks: {{ automatic: true, width: "container" }} }}
            }});
        </script>
    </head>
    <body>
        {content}
    </body>
    </html>
    """

    # 3. 将 Markdown 转换为 HTML
    html_content = mistune.html(md_text)

    # 4. 填充 HTML 模板，同时传入内容和宽度样式
    full_html = html_template.format(
        content=html_content, width_style=width_style)

    # 5. 使用 Playwright 进行截图
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            device_scale_factor=scale
        )
        page = await context.new_page()

        await page.set_content(full_html, wait_until="networkidle")

        # 更稳健地等待 MathJax 渲染完成
        try:
            await page.evaluate("MathJax.Hub.Queue(['Typeset', MathJax.Hub])")
            await page.wait_for_function("typeof MathJax.Hub.Queue.running === 'undefined' || MathJax.Hub.Queue.running === 0")
        except Exception as e:
            print(f"等待 MathJax 时出错 (可能是页面加载太快): {e}")

        await page.evaluate("""
            () => {
                const body = document.body;
                const displayMathBlocks = Array.from(
                    document.querySelectorAll('.MathJax_Display')
                );

                for (const block of displayMathBlocks) {
                    const availableWidth = block.clientWidth || body.clientWidth;
                    const mathElement = block.querySelector(
                        '.MathJax, .MathJax_CHTML, .mjx-chtml, svg'
                    ) || block;
                    const overflowWidth = Math.max(
                        block.scrollWidth,
                        mathElement.scrollWidth,
                        mathElement.getBoundingClientRect().width
                    );

                    if (availableWidth > 0 && overflowWidth > availableWidth + 1) {
                        const scale = Math.max(
                            0.55,
                            Math.min(1, availableWidth / overflowWidth)
                        );
                        mathElement.classList.add('mathjax-overflow-fallback');
                        mathElement.style.display = 'inline-block';
                        mathElement.style.zoom = String(scale);
                    }
                }
            }
        """)

        element_handle = await page.query_selector('body')
        if not element_handle:
            raise Exception("无法找到 <body> 元素进行截图。")

        await element_handle.screenshot(path=output_image_path)
        await browser.close()
        print(f"图片已保存到: {output_image_path}")


async def html_to_image_playwright(
    html_text: str,
    output_image_path: str,
    scale: int = 2,
    width: int = None
):
    """使用 Playwright 将 HTML 文档或片段转换为图片。"""
    width_style = (
        f"width: {width}px; box-sizing: border-box;" if width else ""
    )
    render_style = f"""
        <style id="astrbot-markdown2img-render-style">
            html {{ background: white; }}
            body {{
                {width_style}
                margin: 0;
                padding: 25px;
                display: inline-block;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                    Helvetica, Arial, sans-serif;
                -webkit-font-smoothing: antialiased;
                text-rendering: optimizeLegibility;
            }}
        </style>
    """

    # 禁用 JavaScript 后，Playwright 的 page.add_style_tag() 会等待超时。
    # 因此在 set_content() 前直接把渲染样式合并进 HTML。对于完整文档，
    # 将样式放到 </head> 前；对于 HTML 片段，追加到片段末尾。
    # 追加而不是前置可避免把样式放到 <!DOCTYPE html> 之前。
    head_end = re.search(r"</head\s*>", html_text, re.IGNORECASE)
    if head_end:
        html_content = (
            html_text[:head_end.start()]
            + render_style
            + html_text[head_end.start():]
        )
    else:
        html_content = html_text + render_style

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            device_scale_factor=scale,
            java_script_enabled=False
        )
        page = await context.new_page()

        # HTML 来自模型输出，禁止页面访问外部资源或内网地址。
        await page.route("**/*", lambda route: route.abort())
        await page.set_content(html_content, wait_until="domcontentloaded")

        element_handle = await page.query_selector("body")
        if not element_handle:
            await browser.close()
            raise Exception("无法找到 <body> 元素进行截图。")

        await element_handle.screenshot(path=output_image_path)
        await browser.close()
        print(f"图片已保存到: {output_image_path}")


# --- 示例 ---
markdown_string = """
# Playwright 渲染测试

这是一个宽度被设置为 600px 的示例。当文本内容足够长时，它会自动换行以适应设定的宽度。

行内公式 $a^2 + b^2 = c^2$。

独立公式：
$$
\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}
$$

以及一段 C++ 代码:
```cpp
#include <iostream>

int main() {
    // 这是一段注释，用来增加代码块的宽度，以测试在固定宽度下的显示效果。
    std::cout << "Hello, C++! This is a longer line to demonstrate wrapping or scrolling." << std::endl;
    return 0;
}
"""

@register(
    "astrbot_plugin_md2img",
    "tosaki",  # Or your name
    "允许LLM将Markdown或HTML文本转换为图片发送",
    "1.1.0",
)
class MarkdownConverterPlugin(Star):
    CACHE_MAX_AGE_SECONDS = 24 * 60 * 60
    CACHE_CLEANUP_INTERVAL_SECONDS = 60 * 60
    CACHE_IMAGE_PATTERN = re.compile(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\.png"
    )
    MD2IMG_ENABLED_EXTRA_KEY = "md2img_enabled"
    ML2IMG_ENABLED_EXTRA_KEY = "ml2img_enabled"
    MD_COMMAND_PATTERN = re.compile(
        r"^\s*/?md(?:$|[\s:：]|(?![A-Za-z0-9_]))",
        re.IGNORECASE
    )
    MD_BLOCK_FULL_PATTERN = re.compile(r"<md>(.*?)</md>", re.DOTALL | re.IGNORECASE)
    ML_COMMAND_PATTERN = re.compile(
        r"^\s*/?ml(?:$|[\s:：]|(?![A-Za-z0-9_]))",
        re.IGNORECASE
    )
    ML_BLOCK_FULL_PATTERN = re.compile(r"<ml>(.*?)</ml>", re.DOTALL | re.IGNORECASE)
    RENDER_BLOCK_PATTERN = re.compile(
        r"(<md>.*?</md>|<ml>.*?</ml>)",
        re.DOTALL | re.IGNORECASE
    )

    def __init__(self, context: Context):
        super().__init__(context)
        self.DATA_DIR = os.path.normpath(StarTools.get_data_dir())
        # 创建一个专门用于存放生成图片的缓存目录
        self.IMAGE_CACHE_DIR = os.path.join(self.DATA_DIR, "md2img_cache")
        self._cache_cleanup_task: asyncio.Task | None = None

    def _remove_expired_images(self):
        cutoff = time.time() - self.CACHE_MAX_AGE_SECONDS
        try:
            with os.scandir(self.IMAGE_CACHE_DIR) as entries:
                for entry in entries:
                    if not self.CACHE_IMAGE_PATTERN.fullmatch(entry.name):
                        continue
                    try:
                        if (
                            entry.is_file(follow_symlinks=False)
                            and entry.stat(follow_symlinks=False).st_mtime < cutoff
                        ):
                            os.unlink(entry.path)
                    except FileNotFoundError:
                        continue
                    except OSError as exc:
                        logger.warning(f"清理缓存图片 {entry.name} 失败: {exc}")
        except OSError as exc:
            logger.warning(f"扫描图片缓存目录失败: {exc}")

    async def _clean_image_cache(self):
        while True:
            await asyncio.to_thread(self._remove_expired_images)
            await asyncio.sleep(self.CACHE_CLEANUP_INTERVAL_SECONDS)

    def _is_md_command(self, event: AstrMessageEvent) -> bool:
        """判断本轮消息是否显式要求启用 Markdown 转图片。"""
        message_str = getattr(event, "message_str", "") or ""
        return bool(self.MD_COMMAND_PATTERN.match(message_str))

    def _is_ml_command(self, event: AstrMessageEvent) -> bool:
        """判断本轮消息是否显式要求启用 HTML 转图片。"""
        message_str = getattr(event, "message_str", "") or ""
        return bool(self.ML_COMMAND_PATTERN.match(message_str))

    async def initialize(self):
        """初始化插件，确保图片缓存目录和 Playwright 浏览器存在 (异步版本)"""
        try:
            # os.makedirs is synchronous, but it's extremely fast and not a bottleneck.
            # For a simple, one-off operation like this, it's fine to keep it.
            os.makedirs(self.IMAGE_CACHE_DIR, exist_ok=True)
            if self._cache_cleanup_task is None or self._cache_cleanup_task.done():
                self._cache_cleanup_task = asyncio.create_task(self._clean_image_cache())

            logger.info("正在异步检查并安装 Playwright 浏览器依赖...")
            
            # This function starts a subprocess without blocking the event loop.

            # Helper function to run a command and log its output
            async def run_playwright_command(command: list, description: str):
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                # Await the process to complete and capture the output
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    logger.error(
                        f"自动安装 Playwright {description} 失败，返回码: {process.returncode}")
                    if stderr:
                        logger.error(
                            f"错误输出: \n{stderr.decode('utf-8', errors='ignore')}")
                    return False
                else:
                    output = stdout.decode('utf-8', errors='ignore')
                    # Only log if there's meaningful output (e.g., not just "up to date")
                    if "up to date" not in output:
                        logger.info(
                            f"Playwright {description} 安装/更新完成。\n{output}")
                    else:
                        logger.info(f"Playwright {description} 已是最新，无需下载。")
                    return True

            # Command to install chromium browser
            install_browser_cmd = [sys.executable, "-m",
                                   "playwright", "install", "chromium"]
            await run_playwright_command(install_browser_cmd, "Chromium 浏览器")

            # Command to install system dependencies
            install_deps_cmd = [sys.executable,
                                "-m", "playwright", "install-deps"]
            await run_playwright_command(install_deps_cmd, "系统依赖")

            logger.info("Markdown/HTML 转图片插件已初始化")

        except FileNotFoundError:
            # This error happens if 'python -m playwright' cannot be run
            logger.error(
                "无法执行 Playwright 安装命令。请检查 Playwright Python 包是否已正确安装。")
        except Exception as e:
            logger.error(f"插件初始化过程中发生未知错误: {e}")

    async def terminate(self):
        """插件停用时调用"""
        if self._cache_cleanup_task is not None:
            self._cache_cleanup_task.cancel()
            await asyncio.gather(self._cache_cleanup_task, return_exceptions=True)
            self._cache_cleanup_task = None
        logger.info("Markdown/HTML 转图片插件已停止")

    @filter.on_llm_request()
    async def on_llm_req(self, event: AstrMessageEvent, req: ProviderRequest):
        """根据 md/ml 命令向 LLM 注入对应的图片渲染指令。"""
        md2img_enabled = self._is_md_command(event)
        ml2img_enabled = self._is_ml_command(event)
        event.set_extra(self.MD2IMG_ENABLED_EXTRA_KEY, md2img_enabled)
        event.set_extra(self.ML2IMG_ENABLED_EXTRA_KEY, ml2img_enabled)
        if not md2img_enabled and not ml2img_enabled:
            return

        if ml2img_enabled:
            instruction_prompt = """
当你回复本轮请求时，请将适合可视化展示的内容写成 HTML，并渲染成图片发送。

使用规则：
1. 将需要渲染的 HTML 包裹在 `<ml>` 和 `</ml>` 标签中。
2. 标签内直接输出 HTML 代码，不要使用 Markdown 代码围栏。
3. 可以使用 HTML 文档或 HTML 片段，并可通过内联 CSS 或 `<style>` 设置样式。
4. 不要使用 JavaScript、外部样式表、外部字体或网络图片；渲染器不会执行脚本或加载外部资源。
5. 普通对话和解释放在标签外，只把需要生成图片的正式内容放入标签内。
6. 确保标签内 HTML 结构完整，文本清晰，并适合约 600px 宽度展示。

例如：
<ml>
<style>
  .card { font-family: sans-serif; padding: 24px; background: #f5f7fb; }
  .card h1 { color: #2457a7; }
</style>
<div class="card">
  <h1>HTML 渲染示例</h1>
  <p>这段内容会转换为图片。</p>
</div>
</ml>
"""
        else:
            instruction_prompt = """
本轮用户已启用 md 图片模式。回复中如果包含表格、代码块、数学公式、
嵌套或长列表、多级标题、复杂引用，必须将对应的完整 Markdown
正文放在一对 <md> 和 </md> 标签之间。标签本身直接输出，
不要在标签外加代码围栏，也不要在标签外重复同一份正文。

普通段落、寒暄、角色扮演动作、说明、图片生成提示词留在标签外。
仅有普通文本或少量加粗、斜体时，直接用文字回复。
直接回复与通过 send_message_to_user 发送的文字都遵循此格式。
发送前检查复杂内容是否有完整的 <md> 和 </md> 标签。
"""
        # 将指令添加到 system prompt 的末尾
        req.system_prompt = (req.system_prompt or "") + "\n\n" + instruction_prompt.strip()

    @filter.on_llm_response()
    async def on_llm_resp(self, event: AstrMessageEvent, resp: LLMResponse):
        """暂存原始响应，不修改 LLMResponse，保证上下文仍保存原始文本。"""
        raw_text = resp.completion_text or ""
        if self.RENDER_BLOCK_PATTERN.search(raw_text):
            event.set_extra("raw_llm_completion_text", raw_text)

    @filter.on_using_llm_tool()
    async def on_using_llm_tool(self, event: AstrMessageEvent, tool, tool_args: dict | None):
        """处理 send_message_to_user 直发消息中的渲染标签。"""
        if getattr(tool, "name", "") != "send_message_to_user":
            return
        if not isinstance(tool_args, dict):
            return

        messages = tool_args.get("messages")
        if not isinstance(messages, list):
            return

        new_messages = []
        changed = False
        for message in messages:
            if not isinstance(message, dict):
                new_messages.append(message)
                continue

            message_type = str(message.get("type", "")).lower()
            text = str(message.get("text", ""))
            is_plain_message = message_type in ("plain", "text") or (
                not message_type and "text" in message
            )
            if not is_plain_message or not self.RENDER_BLOCK_PATTERN.search(text):
                new_messages.append(message)
                continue

            components = await self._process_text_with_render_blocks(text)
            new_messages.extend(self._components_to_tool_messages(components))
            changed = True

        if changed:
            tool_args["messages"] = new_messages

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        """在最终消息链生成阶段，解析并替换渲染标签。"""
        result = event.get_result()
        if not result or not result.chain:
            return

        chain = result.chain
        new_chain = []
        for item in chain:
            # 我们只处理纯文本部分
            if isinstance(item, Plain) and self.RENDER_BLOCK_PATTERN.search(item.text):
                # 调用核心处理函数
                components = await self._process_text_with_render_blocks(item.text)
                new_chain.extend(components)
            else:
                new_chain.append(item)
        result.chain = new_chain

    async def _process_text_with_render_blocks(self, text: str) -> List:
        """
        处理包含 <md>...</md> 或 <ml>...</ml> 标签的文本。
        将其分割成 Plain 和 Image 组件的列表。
        """
        components = []
        parts = self.RENDER_BLOCK_PATTERN.split(text)

        for part in parts:
            if not part.strip():
                continue

            md_match = self.MD_BLOCK_FULL_PATTERN.fullmatch(part)
            ml_match = self.ML_BLOCK_FULL_PATTERN.fullmatch(part)
            if md_match or ml_match:
                content = (md_match or ml_match).group(1).strip()
                if not content:
                    continue

                # 生成一个唯一的图片文件名
                image_filename = f"{uuid.uuid4()}.png"
                output_path = os.path.join(self.IMAGE_CACHE_DIR, image_filename)

                try:
                    if md_match:
                        await markdown_to_image_playwright(
                            md_text=content,
                            output_image_path=output_path,
                            scale=2,
                            width=600
                        )
                        content_type = "Markdown"
                    else:
                        await html_to_image_playwright(
                            html_text=content,
                            output_image_path=output_path,
                            scale=2,
                            width=600
                        )
                        content_type = "HTML"

                    if os.path.exists(output_path):
                        # 如果图片成功生成，则添加到组件列表中
                        components.append(Image.fromFileSystem(output_path))
                    else:
                        # 如果生成失败，则将原始内容作为纯文本发送
                        logger.error(f"{content_type} 图片生成失败，但文件未找到: {output_path}")
                        components.append(Plain(f"--- {content_type} 渲染失败 ---\n{content}"))
                except Exception as e:
                    content_type = "Markdown" if md_match else "HTML"
                    logger.error(f"调用 {content_type} 转图片函数异常: {e}")
                    # 如果转换过程中发生异常，也回退到纯文本
                    components.append(Plain(f"--- {content_type} 渲染异常 ---\n{content}"))
            else:
                # 如果不是标签，就是普通文本
                components.append(Plain(part.strip()))

        return components

    def _components_to_tool_messages(self, components: List) -> List[dict]:
        """将 Plain/Image 组件转换为 send_message_to_user 可接受的参数。"""
        messages = []
        for component in components:
            if isinstance(component, Plain):
                if component.text.strip():
                    messages.append({"type": "plain", "text": component.text})
            elif isinstance(component, Image):
                image_path = getattr(component, "path", "") or ""
                if not image_path and component.file.startswith("file:///"):
                    image_path = component.file[8:]
                if image_path:
                    messages.append({"type": "image", "path": image_path})
        return messages
    

if __name__ == "__main__":
    # 生成一个固定宽度的图片
    output_file_fixed_width = f"markdown_width_{uuid.uuid4().hex[:6]}.png"
    asyncio.run(markdown_to_image_playwright(
        markdown_string,
        output_file_fixed_width,
        scale=2,
        width=1000  # 设置宽度为 600px
    ))

    # 生成一个自适应宽度的图片(不设置 width 参数)
    output_file_auto_width = f"markdown_auto_{uuid.uuid4().hex[:6]}.png"
    asyncio.run(markdown_to_image_playwright(
        markdown_string,
        output_file_auto_width,
        scale=2
    ))
