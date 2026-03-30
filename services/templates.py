"""小红书图片模板仓库 - 视觉风格分类"""
import asyncio
import httpx
import time
from typing import List, Dict, Optional
from functools import lru_cache

# 每个风格对应的小红书搜索关键词（用于获取真实样本封面图）
TEMPLATE_SEARCH_KEYWORDS = {
    "yellow-cartoon": "黄色系卡通 小红书封面",
    "fresh-green": "清新绿色 小红书配图",
    "premium-dark": "高级感暗色调 小红书",
    "vintage-film": "复古胶片 小红书",
    "cinematic": "电影感 小红书封面",
    "minimal-white": "极简留白 小红书",
    "bold-color": "撞色插画 小红书",
    "warm-life": "暖调生活 小红书",
    "hand-drawn": "手绘感 小红书封面",
}

# 视觉风格模板基础数据
BASE_TEMPLATES: List[Dict] = [
    {
        "id": "yellow-cartoon",
        "name": "黄色卡通",
        "description": "明亮的黄色主调，卡通插画风格，可爱活泼，适合日常分享和种草类内容",
        "prompt_hint": "明亮吸睛，卡通插画风格，黄色调为主，适合种草和日常分享",
        "image_style": "活泼",
        "image_prompt": "bright yellow cartoon illustration style, cute hand-drawn characters, cheerful vibrant mood, clean white background, vertical 9:16 format, Xiaohongshu social media cover, modern flat design with warm yellow tones",
    },
    {
        "id": "fresh-green",
        "name": "清新绿色",
        "description": "清新的绿色调，自然植物元素，清爽干净，适合生活方式和美妆类内容",
        "prompt_hint": "清新自然，绿色调为主，让人感到舒适放松",
        "image_style": "温馨",
        "image_prompt": "fresh green color palette, natural plants and leaves, clean minimalist aesthetic, soft natural lighting, bright and airy atmosphere, vertical 9:16 portrait format, Xiaohongshu lifestyle cover, professional photography style with green tones",
    },
    {
        "id": "premium-dark",
        "name": "高级感",
        "description": "深邃的暗色调，高级质感，适合职场干货和专业分享",
        "prompt_hint": "低调有质感，暗色调为主，透露出专业和高级感",
        "image_style": "专业",
        "image_prompt": "dark moody premium aesthetic, deep charcoal and black tones, elegant luxury feel, professional studio lighting, minimalist composition, vertical 9:16 portrait format, Xiaohongshu premium cover, high-end fashion magazine style",
    },
    {
        "id": "vintage-film",
        "name": "复古胶片",
        "description": "复古胶片质感，暖色调和颗粒感，适合文艺和旅行类内容",
        "prompt_hint": "复古胶片感，暖色调，有质感和年代感",
        "image_style": "文艺",
        "image_prompt": "vintage film photography aesthetic, warm sepia tones, film grain texture, nostalgic and romantic mood, 35mm film camera look, soft bokeh background, vertical 9:16 portrait format, Xiaohongshu retro style cover",
    },
    {
        "id": "cinematic",
        "name": "电影感",
        "description": "电影级构图和色调，宽幅感，适合故事性强的内容",
        "prompt_hint": "电影级质感，构图讲究，有故事感",
        "image_style": "文艺",
        "image_prompt": "cinematic film aesthetic, anamorphic lens look, dramatic lighting, movie still quality, widescreen composition, rich color grading, emotional narrative mood, vertical 9:16 portrait format, Xiaohongshu cinematic cover",
    },
    {
        "id": "minimal-white",
        "name": "极简留白",
        "description": "大量留白，极简设计，干净利落，适合文艺和干货类内容",
        "prompt_hint": "极简主义，大量留白，高级干净",
        "image_style": "专业",
        "image_prompt": "minimalist white aesthetic, vast white space, ultra clean composition, modern typography, simple and elegant, zen-like calm mood, vertical 9:16 portrait format, Xiaohongshu minimalist cover, Apple design aesthetic",
    },
    {
        "id": "bold-color",
        "name": "撞色插画",
        "description": "强对比撞色，插画感强，适合时尚和穿搭类内容",
        "prompt_hint": "撞色大胆，插画风格，时尚前卫",
        "image_style": "活泼",
        "image_prompt": "bold color blocking illustration style, vibrant contrasting colors, geometric shapes, modern pop art influence, energetic dynamic composition, vertical 9:16 portrait format, Xiaohongshu fashion cover, colorful street art aesthetic",
    },
    {
        "id": "warm-life",
        "name": "暖调生活",
        "description": "温暖的橘黄色调，生活气息浓，适合日常vlog和生活方式内容",
        "prompt_hint": "温暖生活感，橘黄色调，有家的感觉",
        "image_style": "温馨",
        "image_prompt": "warm cozy lifestyle photography, golden hour sunlight, warm orange and amber tones, cozy home atmosphere, everyday life documentary style, authentic and relatable mood, vertical 9:16 portrait format, Xiaohongshu warm lifestyle cover",
    },
    {
        "id": "hand-drawn",
        "name": "手绘感",
        "description": "手绘插画风格，有温度和个性，适合情感和文青类内容",
        "prompt_hint": "手绘插画风格，有温度有个性",
        "image_style": "文艺",
        "image_prompt": "hand-drawn illustration style, watercolor texture, artistic sketch aesthetic, warm handcrafted feeling, personal and intimate mood, vertical 9:16 portrait format, Xiaohongshu artistic cover, diary-like hand-drawn quality with soft colors",
    },
]


# 小红书 MCP HTTP API 地址（与 xiaohongshu-mcp 服务通信）
XHS_API_BASE = "http://127.0.0.1:18060/api/v1"


class TemplateImageCache:
    """模板封面图缓存（从真实小红书搜索结果中提取）"""

    def __init__(self, ttl_seconds: int = 1800):  # 30分钟缓存
        self._cache: Dict[str, List[str]] = {}  # template_id -> list of cover URLs
        self._timestamps: Dict[str, float] = {}
        self._ttl = ttl_seconds
        self._fetching: Dict[str, asyncio.Task] = {}

    def _is_expired(self, template_id: str) -> bool:
        if template_id not in self._timestamps:
            return True
        return time.time() - self._timestamps[template_id] > self._ttl

    def get(self, template_id: str) -> List[str]:
        """同步获取缓存的图片URL列表（可能为空）"""
        if self._is_expired(template_id) and template_id not in self._fetching:
            # 触发后台刷新（不在这里 await）
            pass
        return self._cache.get(template_id, [])

    async def fetch_for_template(self, template_id: str, keyword: str, n: int = 3) -> List[str]:
        """从真实小红书搜索结果中提取封面图URL"""
        if not self._is_expired(template_id) and template_id in self._cache:
            return self._cache[template_id]

        if template_id in self._fetching:
            # 等待已在进行的请求
            try:
                return await self._fetching[template_id]
            except Exception:
                return self._cache.get(template_id, [])

        async def _do_fetch():
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    url = f"{XHS_API_BASE}/feeds/search"
                    try:
                        resp = await client.get(url, params={"keyword": keyword, "page": 1})
                    except Exception:
                        # POST fallback
                        resp = await client.post(url, json={"keyword": keyword, "page": 1})

                    if resp.status_code == 200:
                        feeds = resp.json().get("data", {}).get("feeds", [])
                        urls = []
                        for f in feeds[:n]:
                            cover = f.get("noteCard", {}).get("cover", {})
                            url = cover.get("urlDefault", "") or cover.get("urlPre", "")
                            if url:
                                urls.append(url)
                        self._cache[template_id] = urls
                        self._timestamps[template_id] = time.time()
                        return urls
            except Exception as e:
                print(f"[TemplateImageCache] Failed to fetch images for {template_id}: {e}")
            return self._cache.get(template_id, [])

        task = asyncio.create_task(_do_fetch())
        self._fetching[template_id] = task

        try:
            result = await task
        finally:
            self._fetching.pop(template_id, None)

        return result or []

    async def warmup_all(self):
        """启动时预热所有模板的封面图（每个风格抓6张封面）"""
        await asyncio.gather(*[
            self.fetch_for_template(t["id"], TEMPLATE_SEARCH_KEYWORDS.get(t["id"], t["name"]), n=6)
            for t in BASE_TEMPLATES
        ], return_exceptions=True)

    def get_sync(self, template_id: str) -> List[str]:
        """同步获取（返回缓存值，不触发网络请求）"""
        return self._cache.get(template_id, [])

    def get_first_cover(self, template_id: str) -> Optional[str]:
        """获取第一个封面图URL"""
        urls = self.get_sync(template_id)
        return urls[0] if urls else None


# 全局缓存实例
_image_cache = TemplateImageCache(ttl_seconds=1800)


class TemplateRepository:
    """模板仓库查询接口"""

    def __init__(self):
        self._templates = BASE_TEMPLATES

    def list_templates(self) -> List[Dict]:
        """列出所有模板（包含默认封面图）"""
        # 默认高质量封面图（来自 Unsplash，稳定可访问）
        DEFAULT_COVERS = {
            "yellow-cartoon": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=400&h=700&fit=crop",
            "fresh-green": "https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?w=400&h=700&fit=crop",
            "premium-dark": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=700&fit=crop",
            "vintage-film": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=400&h=700&fit=crop",
            "cinematic": "https://images.unsplash.com/photo-1478720568477-152d9b164e26?w=400&h=700&fit=crop",
            "minimal-white": "https://images.unsplash.com/photo-1506157786151-b8491531f063?w=400&h=700&fit=crop",
            "bold-color": "https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=400&h=700&fit=crop",
            "warm-life": "https://images.unsplash.com/photo-1494438639946-1ebd1d20bf85?w=400&h=700&fit=crop",
            "hand-drawn": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=400&h=700&fit=crop",
        }
        result = []
        print(f"[Templates] 开始获取 {len(self._templates)} 个模板")
        for t in self._templates:
            cached_urls = _image_cache.get_sync(t["id"])
            cover_url = cached_urls[0] if cached_urls else DEFAULT_COVERS.get(t["id"])
            print(f"[Templates] 模板 {t['id']} ({t['name']}) - 封面图: {cover_url}")
            result.append({
                "id": t["id"],
                "name": t["name"],
                "description": t["description"],
                "preview_urls": cached_urls or [cover_url],
                "cover_url": cover_url,
                "image_style": t.get("image_style", "温馨"),
                "prompt_hint": t.get("prompt_hint", ""),
                "image_prompt": t.get("image_prompt", ""),
            })
        print(f"[Templates] 返回 {len(result)} 个模板")
        return result

    def get_template(self, template_id: str) -> Optional[Dict]:
        """根据ID获取模板完整数据"""
        for t in self._templates:
            if t["id"] == template_id:
                cached_urls = _image_cache.get_sync(template_id)
                result = dict(t)
                result["preview_urls"] = cached_urls
                result["cover_url"] = cached_urls[0] if cached_urls else None
                return result
        return None

    def get_image_style(self, template_id: str) -> str:
        t = self.get_template(template_id)
        return t["image_style"] if t else "温馨"

    def get_image_prompt(self, template_id: str, topic: str) -> Optional[str]:
        """获取图片生成提示词（可注入真实小红书封面URL用于风格参考）"""
        t = self.get_template(template_id)
        if not t:
            return None
        return t["image_prompt"]

    def get_style_reference_urls(self, template_id: str) -> List[str]:
        """获取模板对应的真实小红书封面图URL列表（用于图片生成参考）"""
        return _image_cache.get_sync(template_id)


def get_template_by_id(template_id: str) -> Optional[Dict]:
    """便捷函数：根据ID获取模板完整数据"""
    return TemplateRepository().get_template(template_id)
