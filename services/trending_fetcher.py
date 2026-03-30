"""热点话题获取服务 - 微博/百度热搜"""
import httpx
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import json
import os

# 简单的内存缓存
class TrendingCache:
    """内存缓存替代 Redis"""

    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)

    def get(self, key: str) -> Optional[List]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: List, minutes: int = 15):
        expiry = datetime.now() + timedelta(minutes=minutes)
        self._cache[key] = (value, expiry)

_cache = TrendingCache()

class TrendingFetcherService:
    """热点话题获取服务"""

    # 热搜数据源
    SOURCES = {
        "weibo": {
            "name": "微博热搜",
            "url": "https://s.weibo.com/top/summary",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cookie": ""
            }
        },
        "baidu": {
            "name": "百度热搜",
            "url": "https://top.baidu.com/board?tab=realtime",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        }
    }

    # 百度热搜分类 tab URL 映射
    BAIDU_CATEGORY_URLS = {
        "all": "https://top.baidu.com/board?tab=realtime",
        "entertainment": "https://top.baidu.com/board?tab=huayou",
        "sports": "https://top.baidu.com/board?tab=tiyu",
        "tech": "https://top.baidu.com/board?tab=digital",
        "social": "https://top.baidu.com/board?tab=shehui",
        "food": "https://top.baidu.com/board?tab=meishi",
        "travel": "https://top.baidu.com/board?tab=lvyou",
        "fashion": "https://top.baidu.com/board?tab=shishang",
    }

    # 分类中文名到 ID 的映射（用于从页面标题推断分类）
    CATEGORY_KEYWORDS = {
        "entertainment": ["娱乐", "明星", "影视", "综艺", "电影", "电视剧", "演员"],
        "sports": ["体育", "足球", "篮球", "奥运", "CBA", "NBA", "乒乓球"],
        "tech": ["科技", "手机", "电脑", "数码", "AI", "互联网", "芯片"],
        "social": ["社会", "热点", "民生", "新闻", "事件"],
        "food": ["美食", "吃", "餐厅", "菜谱", "食材"],
        "travel": ["旅游", "旅行", "景点", "酒店", "出行"],
        "fashion": ["时尚", "穿搭", "美妆", "护肤", "服装"],
    }

    # 来源平台 URL 映射
    SOURCE_URLS = {
        "baidu": "https://top.baidu.com",
        "weibo": "https://s.weibo.com",
        "recommend": None,
    }

    @staticmethod
    async def get_trending_topics(
        source: str = "baidu",
        limit: int = 20,
        category: str = "all"
    ) -> List[Dict]:
        """获取热点话题"""
        cache_key = f"trending:{source}:{category}:{limit}"

        # 检查缓存
        cached = _cache.get(cache_key)
        if cached:
            return cached

        # 根据数据源获取
        if source == "baidu":
            topics = await TrendingFetcherService._fetch_baidu_trending(limit, category)
        elif source == "weibo":
            topics = await TrendingFetcherService._fetch_weibo_trending(limit, category)
        else:
            topics = TrendingFetcherService._get_default_topics(category)

        # 如果是"全部"分类且来源不是recommend，尝试过滤
        if category != "all":
            topics = TrendingFetcherService._filter_by_category(topics, category)

        # 缓存 15 分钟
        _cache.set(cache_key, topics, minutes=15)

        return topics

    @staticmethod
    async def search_news(keyword: str, limit: int = 5) -> List[Dict]:
        """根据关键词搜索相关新闻（用于文案写作参考）

        使用今日头条/百度新闻搜索API获取真实新闻摘要。
        """
        cache_key = f"news:{keyword}:{limit}"
        cached = _cache.get(cache_key)
        if cached:
            return cached

        # 尝试今日头条新闻搜索
        topics = await TrendingFetcherService._search_toutiao_news(keyword, limit)
        if topics:
            _cache.set(cache_key, topics, minutes=10)
            return topics

        # Fallback：尝试腾讯新闻搜索
        topics = await TrendingFetcherService._search_qq_news(keyword, limit)
        if topics:
            _cache.set(cache_key, topics, minutes=10)
            return topics

        return []

    @staticmethod
    async def _fetch_toutiao_trending(limit: int) -> List[Dict]:
        """获取头条热搜"""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://www.toutiao.com/hot-event/hot-board/?origin=hot_board",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "application/json, text/plain, */*",
                        "Referer": "https://www.toutiao.com/",
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", []) or data.get("hot_list", [])
                    topics = []
                    for i, item in enumerate(items[:limit]):
                        title = item.get("Title", "") or item.get("word", "") or item.get("title", "")
                        if title:
                            topics.append({
                                "rank": i + 1,
                                "title": title,
                                "source": "toutiao",
                                "hot_value": str(item.get("HotValue", item.get("hot_value", ""))),
                                "url": item.get("Url", "") or f"https://so.toutiao.com/search?keyword={title}",
                                "category": TrendingFetcherService._infer_category(title),
                            })
                    if topics:
                        return topics
        except Exception as e:
            print(f"[_fetch_toutiao_trending] Failed: {e}")
        return []

    @staticmethod
    async def _search_toutiao_news(keyword: str, limit: int = 5) -> List[Dict]:
        """今日头条新闻搜索"""
        try:
            # 今日头条热搜API（无需登录）
            url = "https://www.toutiao.com/api/search/content/"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    params={
                        "keyword": keyword,
                        "pd": "news",
                        "source": "input",
                        "offset": 0,
                        "count": limit,
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "https://www.toutiao.com/",
                    }
                )
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = data.get("data", [])
            news_list = []
            for item in results[:limit]:
                title = item.get("title", "")
                abstract = item.get("abstract", "") or item.get("content", "") or ""
                if title and abstract:
                    news_list.append({
                        "title": title.strip(),
                        "summary": abstract.strip()[:200],
                    })
            return news_list
        except Exception as e:
            print("[_search_toutiao_news] Failed:", e)
            return []

    @staticmethod
    async def _search_qq_news(keyword: str, limit: int = 5) -> List[Dict]:
        """腾讯新闻搜索"""
        try:
            url = "https://new.qq.com/omn/search/search.htm"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    params={"query": keyword, "page": 1, "n": limit},
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.select(".news-item")[:limit]
            results = []
            for item in items:
                title_el = item.select_one("h3 a, .title a")
                desc_el = item.select_one(".desc, .brief")
                if title_el:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "summary": desc_el.get_text(strip=True)[:200] if desc_el else "",
                    })
            return results
        except Exception as e:
            print("[_search_qq_news] Failed:", e)
            return []

    @staticmethod
    async def _fetch_baidu_trending(limit: int, category: str = "all") -> List[Dict]:
        """获取百度热搜 - 尝试多种方式获取"""
        # 方式1：尝试百度热搜官方 API（PC 端接口）
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://top.baidu.com/api.php",
                    params={"url": "top.baidu.com/board?tab=realtime", "node": "-entry"},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "application/json, text/plain, */*",
                        "Referer": "https://top.baidu.com/board?tab=realtime",
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", []) or []
                    topics = []
                    for i, item in enumerate(items[:limit]):
                        topics.append({
                            "rank": i + 1,
                            "title": item.get("query", ""),
                            "source": "baidu",
                            "hot_value": str(item.get("hotScore", "")),
                            "url": item.get("rawUrl", "") or f"https://top.baidu.com/board?tab=realtime",
                            "category": TrendingFetcherService._infer_category(item.get("query", "")),
                        })
                    if topics:
                        return topics
        except Exception as e:
            print(f"[_fetch_baidu_trending] API方式1失败: {e}")

        # 方式2：尝试百度热搜备用接口
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://top.baidu.com/board?tab=realtime",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                    }
                )
                if resp.status_code == 200:
                    # 从 HTML 中提取热搜数据（百度有时会内嵌 JSON 数据）
                    html = resp.text
                    import re as _re
                    # 匹配 window.__INITIAL_STATE__ 或 JSON 数据块
                    json_match = _re.search(r'"query":"([^"]+)","index":(\d+)', html)
                    if json_match:
                        # 提取所有热搜词
                        all_matches = _re.findall(r'"query":"([^"]+)","index":(\d+)', html)
                        topics = []
                        for i, (title, idx) in enumerate(all_matches[:limit]):
                            topics.append({
                                "rank": i + 1,
                                "title": title,
                                "source": "baidu",
                                "hot_value": "",
                                "url": f"https://www.baidu.com/s?wd={title}",
                                "category": TrendingFetcherService._infer_category(title),
                            })
                        if topics:
                            return topics
        except Exception as e:
            print(f"[_fetch_baidu_trending] API方式2失败: {e}")

        # 方式3：尝试知乎/头条热搜作为备选
        try:
            topics = await TrendingFetcherService._fetch_toutiao_trending(limit)
            if topics:
                return topics
        except Exception as e:
            print(f"[_fetch_baidu_trending] 头条热搜失败: {e}")

        return TrendingFetcherService._get_default_topics(category)

    @staticmethod
    async def _fetch_weibo_trending(limit: int, category: str = "all") -> List[Dict]:
        """获取微博热搜 - 使用官方 AJAX API"""
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(
                    "https://weibo.com/ajax/side/hotSearch",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://weibo.com/",
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    realtime = data.get("data", {}).get("realtime", [])
                    topics = []
                    for i, item in enumerate(realtime[:limit]):
                        word = item.get("word", "")
                        if not word:
                            continue
                        # word_scheme 通常是编码的话题名如 #xxx#
                        scheme = item.get("word_scheme", "")
                        if scheme:
                            # 构建微博话题搜索页 URL
                            encoded = scheme.replace("#", "%23")
                            real_url = f"https://s.weibo.com/weibo?q={encoded}"
                        else:
                            encoded = word.replace("#", "%23")
                            real_url = f"https://s.weibo.com/weibo?q={encoded}"
                        topics.append({
                            "rank": i + 1,
                            "title": word,
                            "source": "weibo",
                            "hot_value": str(item.get("num", "")),
                            "url": real_url,
                            "category": TrendingFetcherService._infer_category(word),
                        })
                    if topics:
                        return topics
        except Exception as e:
            print(f"[_fetch_weibo_trending] Failed: {e}")

        return TrendingFetcherService._get_default_topics(category)

    @staticmethod
    def _get_default_topics(category: str = "all") -> List[Dict]:
        """获取默认热点（用于演示或 API 不可用时）"""
        all_topics = [
            {"rank": 1, "title": "周末去哪儿玩", "source": "recommend", "hot_value": "🔥", "category": "travel", "url": None},
            {"rank": 2, "title": "春季穿搭灵感", "source": "recommend", "hot_value": "👗", "category": "fashion", "url": None},
            {"rank": 3, "title": "减脂餐食谱", "source": "recommend", "hot_value": "🥗", "category": "food", "url": None},
            {"rank": 4, "title": "职场沟通技巧", "source": "recommend", "hot_value": "💼", "category": "social", "url": None},
            {"rank": 5, "title": "露营装备推荐", "source": "recommend", "hot_value": "⛺", "category": "travel", "url": None},
            {"rank": 6, "title": "新手化妆教程", "source": "recommend", "hot_value": "💄", "category": "fashion", "url": None},
            {"rank": 7, "title": "读书笔记分享", "source": "recommend", "hot_value": "📚", "category": "entertainment", "url": None},
            {"rank": 8, "title": "宠物日常记录", "source": "recommend", "hot_value": "🐱", "category": "social", "url": None},
            {"rank": 9, "title": "咖啡探店日记", "source": "recommend", "hot_value": "☕", "category": "food", "url": None},
            {"rank": 10, "title": "数码产品测评", "source": "recommend", "hot_value": "📱", "category": "tech", "url": None},
            {"rank": 11, "title": "电影推荐合集", "source": "recommend", "hot_value": "🎬", "category": "entertainment", "url": None},
            {"rank": 12, "title": "篮球比赛精彩瞬间", "source": "recommend", "hot_value": "🏀", "category": "sports", "url": None},
        ]
        if category != "all":
            return [t for t in all_topics if t["category"] == category]
        return all_topics

    @staticmethod
    def _infer_category(title: str) -> str:
        """根据标题关键词推断分类"""
        for cat_id, keywords in TrendingFetcherService.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in title:
                    return cat_id
        return "social"  # 默认社会类

    @staticmethod
    def _filter_by_category(topics: List[Dict], category: str) -> List[Dict]:
        """按分类过滤话题（基于标题关键词匹配）"""
        if category == "all":
            return topics
        keywords = TrendingFetcherService.CATEGORY_KEYWORDS.get(category, [])
        if not keywords:
            return topics
        filtered = [t for t in topics if any(kw in t.get("title", "") for kw in keywords)]
        return filtered if filtered else topics

    @staticmethod
    def get_sources() -> List[Dict]:
        """获取可用的数据源"""
        return [
            {"id": "baidu", "name": "百度热搜", "icon": "🔍"},
            {"id": "weibo", "name": "微博热搜", "icon": "📱"},
            {"id": "recommend", "name": "编辑推荐", "icon": "✨"}
        ]

    @staticmethod
    def get_categories() -> List[Dict]:
        """获取可用的分类"""
        return [
            {"id": "all", "name": "全部"},
            {"id": "entertainment", "name": "娱乐"},
            {"id": "sports", "name": "体育"},
            {"id": "tech", "name": "科技"},
            {"id": "social", "name": "社会"},
            {"id": "food", "name": "美食"},
            {"id": "travel", "name": "旅游"},
            {"id": "fashion", "name": "时尚"}
        ]
