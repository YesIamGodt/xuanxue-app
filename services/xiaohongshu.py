# -*- coding: utf-8 -*-
"""小红书文案生成服务 - 先文案后图片（模板图参考）"""
import asyncio
import re
import httpx
import anthropic
import openai
import base64 as _b64
from typing import Optional, Dict, Any

from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """你是一个专业的小红书文案写手。请根据用户提供的主题，生成吸引人的小红书文案。
要求：
1. 标题要吸引眼球，包含emoji
2. 内容要有代入感，使用第一人称
3. 适当使用emoji点缀
4. 添加相关的话题标签（hashtags）
5. 结构清晰，段落分明"""

STYLE_PROMPTS = {
    "温馨": "温暖亲切，像和闺蜜聊天一样",
    "活泼": "充满活力，使用emoji表情",
    "专业": "专业可信，提供实用干货",
    "文艺": "文艺清新，富有诗意",
    "搞笑": "幽默风趣，轻松有趣"
}

LENGTH_PROMPTS = {
    "简短": "100-200字左右",
    "中等": "300-500字左右",
    "详细": "600-800字左右"
}


def _strip_think_content(text):
    """彻底清理所有可能的思考标签和空行"""
    if not text:
        return ""

    # 清理各种格式的think标签
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<thinking>[\s\S]*?</thinking>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"【思考】[\s\S]*?【思考结束】", "", text)
    text = re.sub(r"思考过程:[\s\S]*?(?=\n\S)", "", text)

    # 清理可能的XML标签格式
    text = re.sub(r"<\w+>[\s\S]*?</\1>", "", text)

    # 清理多余空行和空白
    lines = text.split('\n')
    cleaned_lines = [line.rstrip() for line in lines if line.strip()]
    text = '\n'.join(cleaned_lines)

    return text.strip()


def _build_user_prompt(topic, style, length, image_data, template_prompt_hint, topic_news):
    base = "请为「{}」生成一篇{}的小红书文案。".format(
        topic, STYLE_PROMPTS.get(style, STYLE_PROMPTS["温馨"]))
    if image_data:
        base = "请根据这张图片，为「{}」生成一篇{}的小红书文案。请结合图片内容进行描述，增加真实性和吸引力。".format(
            topic, STYLE_PROMPTS.get(style, STYLE_PROMPTS["温馨"]))
    base += "\n长度要求：" + LENGTH_PROMPTS.get(length, LENGTH_PROMPTS["中等"])

    # 注入相关新闻参考（最重要的！）
    if topic_news:
        news_str = "\n".join(["  - {}：{}".format(n["title"], n["summary"]) for n in topic_news[:5]])
        base += "\n\n[相关最新新闻/资讯参考]\n" + news_str

    if template_prompt_hint:
        base += "\n\n[文案风格指导]\n" + template_prompt_hint
    return base


def _generate_text_sync(topic, style, length, image_data=None, image_type=None,
                         template_id=None, topic_news=None):
    template_prompt_hint = ""
    if template_id:
        try:
            from services.templates import TemplateRepository
            repo = TemplateRepository()
            tmpl = repo.get_template(template_id)
            if tmpl:
                template_prompt_hint = tmpl.get("prompt_hint", "")
        except Exception:
            template_prompt_hint = ""

    user_prompt = _build_user_prompt(
        topic, style, length, image_data,
        template_prompt_hint, topic_news or []
    )

    provider = settings.ai_provider.lower()
    if provider == "anthropic":
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        messages = []
        if image_data:
            b64 = _b64.b64encode(image_data).decode("utf-8")
            messages.append({
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": image_type or "image/jpeg", "data": b64}},
                    {"type": "text", "text": user_prompt},
                ],
            })
        else:
            messages.append({"role": "user", "content": user_prompt})
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return _strip_think_content(response.content[0].text)
    else:
        if settings.is_custom_provider and settings.custom_api_url:
            client = openai.OpenAI(
                api_key=settings.custom_api_key,
                base_url=settings.custom_api_url.replace("/chat/completions", ""),
            )
            model = settings.custom_model
        else:
            client = openai.OpenAI(api_key=settings.openai_api_key)
            model = settings.openai_model
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if image_data:
            b64 = _b64.b64encode(image_data).decode("utf-8")
            mime = image_type or "image/jpeg"
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," + b64}},
                ],
            })
        else:
            messages.append({"role": "user", "content": user_prompt})
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )
        return _strip_think_content(response.choices[0].message.content)


async def _generate_image_with_ref(topic, style, text_content, reference_image_url, template_id=None):
    from services.image_generator import ImageGenerationService

    image_style = style
    custom_image_prompt = None
    if template_id:
        try:
            from services.templates import TemplateRepository
            repo = TemplateRepository()
            tmpl = repo.get_template(template_id)
            if tmpl:
                custom_image_prompt = tmpl.get("image_prompt")
                image_style = tmpl.get("image_style", style)
        except Exception:
            pass

    try:
        print(f"[XHS Image] 开始生成图片: topic={topic}, style={image_style}")
        result = await ImageGenerationService.generate_image(
            topic=topic,
            style=image_style,
            size="portrait",
            n=3,
            custom_image_prompt=custom_image_prompt,
            reference_image_url=reference_image_url,
            text_content=text_content,
        )
        image_urls = result.get("image_urls", [])
        placeholder = result.get("placeholder", True)
        print(f"[XHS Image] 图片生成结果: {len(image_urls)} 张, placeholder={placeholder}")
        return {
            "image_url": image_urls[0] if image_urls else None,
            "image_urls": image_urls,
            "placeholder": placeholder,
            "image_prompt": result.get("prompt") or result.get("revised_prompt", ""),
        }
    except Exception as e:
        print(f"[XHS Image] 图片生成异常: {e}")
        return {
            "image_url": None,
            "image_urls": [],
            "placeholder": True,
            "image_prompt": "Image generation failed: " + str(e),
        }


class XiaohongshuService:
    @staticmethod
    async def generate_content(
        topic,
        style="温馨",
        length="中等",
        image_data=None,
        image_type=None,
        template_id=None,
        reference_image_url=None,
    ):
        # 第一步：根据用户输入的主题搜索相关新闻作为写作参考
        topic_news = []
        try:
            from services.trending_fetcher import TrendingFetcherService
            topic_news = await TrendingFetcherService.search_news(topic, limit=5)
        except Exception as e:
            print("[Xiaohongshu] Failed to search news:", e)

        # 第二步：生成文案（注入新闻参考）
        text_result = await asyncio.to_thread(
            _generate_text_sync,
            topic=topic,
            style=style,
            length=length,
            image_data=image_data,
            image_type=image_type,
            template_id=template_id,
            topic_news=topic_news,
        )
        if isinstance(text_result, Exception):
            raise Exception("文案生成失败: " + str(text_result))

        # 第三步：生成配图（用模板封面图作参考）
        image_result = await _generate_image_with_ref(
            topic=topic,
            style=style,
            text_content=text_result,
            reference_image_url=reference_image_url,
            template_id=template_id,
        )

        return {
            "text": text_result,
            "image_url": image_result.get("image_url"),
            "image_urls": image_result.get("image_urls", []),
            "placeholder": image_result["placeholder"],
            "image_prompt": image_result["image_prompt"],
        }
