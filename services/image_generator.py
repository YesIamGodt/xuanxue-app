"""图片生成服务 - 支持 MiniMax Image-01 和 OpenAI DALL-E"""
import httpx
import base64
import json
import os
from typing import Optional, Dict, Any, List
from config import get_settings

settings = get_settings()


# 小红书风格的预设提示词模板
STYLE_PROMPTS = {
    "温馨": "warm cozy lifestyle scene, soft warm tones, natural lighting, home atmosphere, photorealistic photography",
    "活泼": "bright vibrant colors, energetic dynamic composition, youthful fashion, clean background, photography",
    "专业": "clean minimal background, professional lighting, business style, high-end quality, magazine layout",
    "文艺": "cinematic color grading, vintage film style, soft bokeh, literary atmosphere, narrative composition",
    "搞笑": "cute cartoon style, fun illustration, exaggerated expression, humorous scene, anime style"
}


class ImageGenerationService:
    """AI 图片生成服务"""

    # 尺寸映射：size 参数 -> MiniMax aspect_ratio / OpenAI size
    SIZE_OPTIONS = {
        "square":    {"minimax": "1:1",   "openai": "1024x1024"},
        "portrait":  {"minimax": "9:16",  "openai": "1024x1792"},
        "landscape": {"minimax": "16:9",  "openai": "1792x1024"},
    }

    @staticmethod
    def _is_minimax_url(api_url: str) -> bool:
        """判断是否为 MiniMax API（使用不同的端点和参数格式）"""
        return "minimaxi" in api_url.lower() or "minimax" in api_url.lower()

    @staticmethod
    def _base_url(api_url: str) -> str:
        """提取 API 基础 URL（去掉 /v1/xxx 等路径）"""
        import re
        # 去掉末尾的 /v1/xxx 或 /v1 等后缀，只保留主机部分
        base = api_url.rstrip("/")
        # 如果已经包含 /v1/image_generation 等路径，只保留到主机部分
        # 支持各种格式：https://api.minimaxi.com, https://api.minimaxi.com/v1, https://api.minimaxi.com/v1/image_generation
        base = re.sub(r"/v\d+/?.*$", "", base, flags=re.IGNORECASE)
        print(f"[ImageGen] 基础URL: {api_url} -> {base}")
        return base

    @staticmethod
    async def generate_image(
        topic: str,
        style: str = "温馨",
        size: str = "portrait",
        quality: str = "standard",
        n: int = 3,
        image_api_url: Optional[str] = None,
        image_api_key: Optional[str] = None,
        image_model: Optional[str] = None,
        custom_image_prompt: Optional[str] = None,
        reference_image_url: Optional[str] = None,
        text_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成配图（支持多张）

        Args:
            topic: 图片主题
            style: 图片视觉风格
            size: 图片尺寸
            quality: 图片质量
            n: 生成图片数量
            image_api_url: 可选，自定义图片 API URL
            image_api_key: 可选，自定义图片 API Key
            image_model: 可选，自定义图片模型
            custom_image_prompt: 可选，直接使用此提示词
            reference_image_url: 可选，选中的模板封面图URL（用于 MiniMax 图生图）
            text_content: 可选，已生成的文案内容，用于生成与文案相关的配图

        Returns:
            Dict with image_urls (List[str]), placeholder (bool), prompt (str)
        """
        api_url = image_api_url or settings.image_api_url
        api_key = image_api_key or settings.image_api_key
        model = image_model or settings.image_model

        print(f"[ImageGen] 配置信息: api_url={api_url}, model={model}, has_key={bool(api_key)}")

        if not api_key:
            print("[ImageGen] 未找到 IMAGE_API_KEY，返回占位符")
            return {
                "image_urls": [],
                "placeholder": True,
                "prompt": custom_image_prompt or topic,
                "message": "请在 .env 中配置 IMAGE_API_KEY 以生成配图"
            }

        # 验证配置的完整性
        if not api_url or not model:
            print("[ImageGen] 图片生成配置不完整，返回占位符")
            return {
                "image_urls": [],
                "placeholder": True,
                "prompt": custom_image_prompt or topic,
                "message": "图片生成配置不完整，请检查 IMAGE_API_URL 和 IMAGE_MODEL"
            }

        try:
            if ImageGenerationService._is_minimax_url(api_url):
                base_url = ImageGenerationService._base_url(api_url)
                print(f"[ImageGen] 调用 MiniMax API: base_url={base_url}")
                result = await ImageGenerationService._call_minimax_api(
                    base_url, api_key, model, prompt="unused",
                    size=size, n=n, reference_image_url=reference_image_url,
                    text_content=text_content, style=style, custom_image_prompt=custom_image_prompt,
                    topic=topic,
                )
                print(f"[ImageGen] MiniMax API 响应: {len(result.get('image_urls', []))} 张图片")
                return result
            else:
                print(f"[ImageGen] 调用 OpenAI API: url={api_url}")
                result = await ImageGenerationService._call_openai_api(
                    api_url, api_key, model,
                    prompt=custom_image_prompt or topic,
                    size=size, quality=quality, n=n
                )
                print(f"[ImageGen] OpenAI API 响应: {len(result.get('image_urls', []))} 张图片")
                return result
        except Exception as e:
            print(f"[ImageGen] 图片生成失败: {e}")
            return {
                "image_urls": [],
                "placeholder": True,
                "prompt": custom_image_prompt or topic,
                "message": f"图片生成失败: {e}"
            }

    @staticmethod
    async def _call_minimax_api(
        api_url: str,
        api_key: str,
        model: str,
        prompt: str,
        size: str,
        n: int,
        reference_image_url: Optional[str] = None,
        text_content: Optional[str] = None,
        style: str = "温馨",
        custom_image_prompt: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """调用 MiniMax Image-01 API
        通过详细提示词引导生成，prompt_optimizer 优化提示词"""
        size_map = ImageGenerationService.SIZE_OPTIONS.get(
            size, ImageGenerationService.SIZE_OPTIONS["portrait"]
        )

        style_prompt_map = {
            "温馨": "warm cozy lifestyle scene, soft warm tones, natural lighting, home atmosphere",
            "活泼": "bright vibrant colors, energetic dynamic composition, youthful fashion, clean background",
            "专业": "clean minimal background, professional lighting, business style, high-end quality",
            "文艺": "cinematic color grading, vintage film style, soft bokeh, literary atmosphere",
            "搞笑": "cute cartoon style, fun illustration, exaggerated expression, humorous scene"
        }
        style_desc = style_prompt_map.get(style, style_prompt_map["温馨"])

        content_snippet = text_content[:300].replace("\n", " ").strip() if text_content else ""
        topic_text = topic or "Social media content"

        # 核心原则：内容为主，风格为辅
        # 把主题和文案内容放在最前面，让模型生成相关的视觉主体
        if content_snippet:
            image_prompt = (
                "Generate a Xiaohongshu (Little Red Book) social media COVER IMAGE based on the following post content.\n"
                "The image must visually represent or abstract the KEY SUBJECT and EMOTION from this content.\n\n"
                "【Post Topic / Theme】: {}\n\n"
                "【Post Content】: {}\n\n"
                "【Required Visual Style】: {} -- {} -- vertical 9:16 ratio, clean composition, high quality, no watermarks, Xiaohongshu trending cover aesthetic"
            ).format(topic_text, content_snippet, style, style_desc)
        else:
            image_prompt = (
                "Generate a Xiaohongshu (Little Red Book) social media COVER IMAGE.\n"
                "【Topic】: {}\n\n"
                "【Visual Style】: {} -- {} -- vertical 9:16 ratio, clean composition, high quality, no watermarks"
            ).format(topic_text, style, style_desc)

        if custom_image_prompt:
            image_prompt += "\n\n【Template Style Reference】: " + custom_image_prompt

        # 构建请求体
        request_body = {
            "model": model,
            "prompt": image_prompt,
            "aspect_ratio": size_map["minimax"],
            "response_format": "url",
            "n": min(n, 9),
            "prompt_optimizer": True,
        }

        # 添加参考图片（使用 subject_reference 字段）
        if reference_image_url:
            request_body["subject_reference"] = [
                {
                    "type": "character",
                    "image_file": reference_image_url
                }
            ]
            print(f"[ImageGen] 已添加参考图片: {reference_image_url}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{api_url.rstrip('/')}/v1/image_generation",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=request_body
            )

        if response.status_code == 200:
            data = response.json()
            resp_data = data.get("data", {})
            image_urls: List[str] = resp_data.get("image_urls", [])
            return {
                "image_urls": image_urls,
                "revised_prompt": image_prompt,
                "placeholder": False
            }
        else:
            raise Exception(f"MiniMax image generation failed ({response.status_code}): {response.text}")

    @staticmethod
    async def _call_openai_api(
        api_url: str,
        api_key: str,
        model: str,
        prompt: str,
        size: str,
        quality: str,
        n: int,
    ) -> Dict[str, Any]:
        """调用 OpenAI DALL-E 兼容 API

        OpenAI endpoint: POST {base}/v1/images/generations
        Response: {"data": [{"url": "..."}]}
        """
        size_map = ImageGenerationService.SIZE_OPTIONS.get(
            size, ImageGenerationService.SIZE_OPTIONS["portrait"]
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{api_url.rstrip('/')}/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "size": size_map["openai"],
                    "quality": quality,
                    "n": n
                }
            )

        if response.status_code == 200:
            data = response.json()
            image_urls: List[str] = [item.get("url", "") for item in data.get("data", [])]
            revised_prompt = data["data"][0].get("revised_prompt", "") if data.get("data") else ""
            return {
                "image_urls": image_urls,
                "revised_prompt": revised_prompt,
                "placeholder": False
            }
        else:
            raise Exception(f"Image generation failed ({response.status_code}): {response.text}")

    @staticmethod
    async def download_image(image_url: str) -> Optional[bytes]:
        """下载图片"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                if response.status_code == 200:
                    return response.content
        except Exception as e:
            print(f"Failed to download image: {e}")
        return None

    @staticmethod
    def get_style_options() -> list:
        """获取可用的风格选项"""
        return [
            {"id": "温馨", "name": "温馨", "icon": "☀️", "description": "温暖柔和的色调"},
            {"id": "活泼", "name": "活泼", "icon": "🎀", "description": "明亮活泼的风格"},
            {"id": "专业", "name": "专业", "icon": "📚", "description": "简洁专业的风格"},
            {"id": "文艺", "name": "文艺", "icon": "🎨", "description": "文艺复古的风格"},
            {"id": "搞笑", "name": "搞笑", "icon": "😂", "description": "幽默有趣的风格"}
        ]

    @staticmethod
    def get_size_options() -> list:
        """获取可用的尺寸选项"""
        return [
            {"id": "portrait", "name": "竖图", "description": "1024x1792 (小红书推荐)"},
            {"id": "square", "name": "方图", "description": "1024x1024"},
            {"id": "landscape", "name": "横图", "description": "1792x1024"}
        ]
