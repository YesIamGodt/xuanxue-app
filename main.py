
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncio
import re
from contextlib import asynccontextmanager
import os
from datetime import datetime
from config import get_settings
import asyncio

# Supabase 认证（延迟导入，避免启动时出错）
try:
    from services.supabase_auth import SupabaseAuthService
    _supabase_available = True
except ImportError:
    SupabaseAuthService = None
    _supabase_available = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 初始化系统
    print("[启动] 玄学互动平台正在初始化...")
    try:
        # 初始化用户画像系统
        from services.metaphysics import get_current_profile
        print("[启动] 用户玄学画像系统已初始化")
    except Exception as e:
        print(f"[启动] 初始化失败: {e}")
    yield
    # Shutdown: nothing needed


app = FastAPI(title="玄学互动平台", description="基于AI的玄学互动平台", lifespan=lifespan)
settings = get_settings()

# 启用CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class UserProfileRequest(BaseModel):
    """用户玄学画像请求模型"""
    name: str
    year: int
    month: int
    day: int
    time_str: str = "00:00"
    gender: str = "男"
    location: str = "未知"

class FateDialogueRequest(BaseModel):
    """命运对话框请求模型"""
    message: str
    conversation_history: Optional[List[dict]] = None
    today_date: Optional[str] = None
    shichen: Optional[str] = None

class HepanRequest(BaseModel):
    """双人合盘请求模型"""
    name1: str
    year1: int
    month1: int
    day1: int
    time_str1: str = "00:00"
    gender1: str = "男"
    name2: str
    year2: int
    month2: int
    day2: int
    time_str2: str = "00:00"
    gender2: str = "男"

class HotspotAnalysisRequest(BaseModel):
    """热点分析请求模型"""
    topic: str
    url: Optional[str] = None

class HotspotContentRequest(BaseModel):
    """热点内容获取请求"""
    topic: str
    url: Optional[str] = None

class HotspotPredictRequest(BaseModel):
    """热点未来预测请求"""
    topic: str
    topic_data: Optional[Dict] = None

class SignUpRequest(BaseModel):
    """用户注册"""
    email: str
    password: str

class SignInRequest(BaseModel):
    """用户登录"""
    email: str
    password: str

class MomentsTextRequest(BaseModel):
    """微信朋友圈文案请求模型"""
    content: str
    style: str = "幽默"


class DailyDivinationRequest(BaseModel):
    """水晶球今日运势请求"""
    question: Optional[str] = None


class DivinationRecordRequest(BaseModel):
    """保存占卜记录请求"""
    record_type: str  # "daily" | "question"
    bazi_summary: str
    ai_response: str
    question: Optional[str] = None
    daily_fortune: Optional[Dict] = None


# 挂载静态文件（用于Web版本）
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def root():
    """返回主页面"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "玄学互动平台API"}

@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}


# ========== Supabase 认证 API ==========
@app.post("/api/auth/signup")
def signup(request: SignUpRequest):
    """用户注册（Supabase Auth）"""
    if not settings.supabase_enabled:
        return {"success": False, "error": "云端登录未配置，请先在设置中启用"}
    result = SupabaseAuthService.sign_up(request.email, request.password)
    return result


@app.post("/api/auth/signin")
def signin(request: SignInRequest):
    """用户登录（Supabase Auth）"""
    if not settings.supabase_enabled:
        return {"success": False, "error": "云端登录未配置"}
    result = SupabaseAuthService.sign_in(request.email, request.password)
    return result


@app.post("/api/auth/signout")
def signout(authorization: Optional[str] = None):
    """用户登出"""
    if not settings.supabase_enabled:
        return {"success": False}
    token = authorization.replace("Bearer ", "") if authorization else ""
    SupabaseAuthService.sign_out(token)
    return {"success": True}


@app.get("/api/auth/me")
def get_me(authorization: Optional[str] = None):
    """获取当前登录用户"""
    if not settings.supabase_enabled:
        return {"success": False, "user": None}
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = SupabaseAuthService.get_user(token)
    return {"success": bool(user), "user": user}

@app.get("/api/date")
def get_date_info():
    """获取今日日期和时辰信息"""
    now = datetime.now()
    from services.metaphysics import BaziCalculator
    shichen = BaziCalculator.get_shichen_from_time(f"{now.hour:02d}:00")
    return {
        "today": now.strftime("%Y年%m月%d日"),
        "weekday": ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()],
        "shichen": shichen,
        "hour": now.hour,
    }

@app.get("/config")
def get_config():
    """获取当前配置信息（仅用于调试）"""
    return {
        "provider": settings.ai_provider,
        "api_base": settings.api_base_url,
        "model": {
            "anthropic": settings.anthropic_model,
            "openai": settings.openai_model,
            "custom": settings.custom_model
        },
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens
    }


# 导入服务
from services.metaphysics import get_current_profile, set_current_profile
from services.trending_fetcher import TrendingFetcherService

# 用户画像API
@app.post("/api/profile/set")
def set_profile(request: UserProfileRequest):
    """设置用户玄学画像"""
    try:
        set_current_profile(
            request.name,
            request.year,
            request.month,
            request.day,
            request.time_str,
            request.gender,
            request.location
        )
        return {"success": True, "message": "用户画像设置成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/profile/get")
def get_profile():
    """获取用户玄学画像"""
    try:
        profile = get_current_profile()
        desc = profile.get_profile_description()
        return {"success": True, "data": desc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 热点话题API
@app.get("/api/trending")
async def get_trending(
    source: str = "baidu",
    limit: int = 15,
    category: str = "all"
):
    """获取分类热点话题"""
    try:
        from services.trending_fetcher import TrendingFetcherService
        topics = await TrendingFetcherService.get_trending_topics(
            source=source, limit=limit, category=category
        )
        return {"success": True, "topics": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trending/categories")
def get_trending_categories():
    """获取热点分类"""
    try:
        from services.trending_fetcher import TrendingFetcherService
        return {"success": True, "categories": TrendingFetcherService.get_categories()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hotspot/analyze")
async def analyze_hotspot(request: HotspotAnalysisRequest):
    """分析热点话题与用户的关系 - AI驱动"""
    try:
        from services.metaphysics import get_current_profile, BaziCalculator
        from services.ai_provider import AIProvider

        profile = get_current_profile()
        if not profile:
            return {"success": False, "analysis": "请先设置您的出生信息"}

        # 获取八字信息
        bazi_data = getattr(profile, "bazi_data", None) or {}
        if not bazi_data:
            return {"success": False, "analysis": "请先在「我的」页面设置您的出生信息"}

        bazi_list = bazi_data.get("bazi", [])
        bazi_str = " ".join([f"{g}{z}" for g, z in bazi_list]) if bazi_list else "未知"
        mingzhu = bazi_data.get("mingzhu", "未知")
        shengxiao = bazi_data.get("shengxiao", "")
        wuxing = bazi_data.get("wuxing_count", {})

        system_prompt = """你是一位精通八字命理的命理师。请根据用户的八字简短分析热点话题与其命运的关联。
要求：
- 回答控制在150字以内，简短精炼
- 多说好话，多给积极建议，让人充满希望
- 用委婉表达，不直说凶险
- 只输出文字，不用markdown格式
- 用神秘但温暖的语气回答"""

        user_prompt = f"""用户信息：
- 姓名：{profile.name}
- 四柱：{bazi_str}
- 生肖：{shengxiao}
- 命主：{mingzhu}
- 五行：{", ".join([f"{k}={v}分" for k,v in wuxing.items()]) if wuxing else "未知"}

热点话题：{request.topic}
{"原文链接：" + request.url if request.url else ""}

请分析这个热点话题与该用户命运的关联，包括：
1. 该话题与用户八字的五行关系
2. 对用户近期运势的影响（事业/财运/感情）
3. 给用户的具体建议"""

        client = AIProvider.get_client()
        try:
            import asyncio
            analysis = await asyncio.to_thread(client.generate, system_prompt, user_prompt)
        except Exception as e:
            analysis = f"命理分析暂时无法连接，请稍后再试。错误：{e}"

        # 彻底去掉 think 标签和多余内容
        import re
        analysis = re.sub(r'</?(?:think|result|python|javascript)[^>]*>.*?</(?:think|result|python|javascript)[^>]*>', '', analysis, flags=re.DOTALL | re.IGNORECASE)
        analysis = re.sub(r'<think>[\s\S]*?</think>', '', analysis)
        analysis = re.sub(r'\[/?(?:think|result)\]', '', analysis, flags=re.IGNORECASE)
        analysis = analysis.strip()

        return {"success": True, "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/hotspot/content")
async def fetch_hotspot_content(request: HotspotContentRequest):
    """抓取热点话题的微博内容摘要（无需登录）"""
    try:
        import httpx
        from bs4 import BeautifulSoup

        topic = request.topic.strip()
        if not topic:
            return {"success": False, "content": "", "summary": ""}

        raw_content = ""

        # 尝试从微博移动版搜索页抓取帖子内容（JSON API，无需登录）
        try:
            encoded = topic.replace("#", "%23").replace(" ", "%20")
            search_url = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{httpx.URLQueryParams({'q': topic}).render().lstrip('?')}&page_type=searchall"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    search_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                        "Referer": "https://m.weibo.cn/",
                        "Accept": "application/json, text/plain, */*",
                    }
                )
            if resp.status_code == 200:
                data = resp.json()
                cards = data.get("data", {}).get("cards", [])
                for card in cards:
                    mblog = card.get("mblog", {})
                    if mblog:
                        text = mblog.get("text", "") or ""
                        if text:
                            soup = BeautifulSoup(text, "html.parser")
                            text = soup.get_text(separator=" ", strip=True)
                            if len(text) > 30:
                                raw_content = text
                                break
        except Exception as e:
            print(f"[fetch_hotspot_content] Weibo fetch failed: {e}")

        # 用 AI 生成内容摘要
        summary = ""
        try:
            from services.ai_provider import AIProvider
            client = AIProvider.get_client()
            if raw_content:
                prompt = f"请用80字以内概括以下微博内容核心要点，客观准确，不要标题党：\n\n{raw_content[:600]}"
                sys_p = "你是微博内容摘要助手，80字以内概括核心，客观准确。"
            else:
                prompt = f"请用80字以内说明热搜话题「{topic}」的背景或当前情况，客观准确，不要标题党。"
                sys_p = "你是新闻助手，80字以内客观描述热搜话题背景，不用感叹号。"

            import asyncio
            summary = await asyncio.to_thread(client.generate, sys_p, prompt)
        except Exception as e:
            print(f"[fetch_hotspot_content] AI summary failed: {e}")
            summary = ""

        import re
        summary = re.sub(r'</?(?:think|result|python|javascript)[^>]*>.*?</(?:think|result|python|javascript)[^>]*>', '', summary, flags=re.DOTALL | re.IGNORECASE)
        summary = re.sub(r'<think>[\s\S]*?</think>', '', summary)
        summary = re.sub(r'\[/?(?:think|result)\]', '', summary, flags=re.IGNORECASE)
        summary = summary.strip()

        return {"success": True, "content": raw_content[:500] if raw_content else "", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/hotspot/predict")
async def predict_hotspot_future(request: HotspotPredictRequest):
    """从玄学视角预测热点事件的明日走向"""
    try:
        from services.ai_provider import AIProvider
        from services.metaphysics import get_current_profile

        topic = request.topic.strip()
        if not topic:
            return {"success": False, "data": None}

        profile = get_current_profile()
        bazi_info = ""
        if profile and profile.bazi_data:
            bazi_data = profile.bazi_data
            bazi_list = bazi_data.get("bazi", [])
            bazi_str = " ".join([f"{g}{z}" for g, z in bazi_list]) if bazi_list else "未知"
            bazi_info = f"求测者四柱：{bazi_str} | 生肖：{bazi_data.get('shengxiao', '')} | 命主：{bazi_data.get('mingzhu', '')}"

        today_str = datetime.now().strftime("%Y年%m月%d日")

        system_prompt = """你是一位修行千年的通灵命理大师，擅长从天象、阴阳五行角度解读世间万象。

你的预测风格：
- 开门见山，直接给结论（不超过20字），再说原因
- 语气像老朋友聊天，不故弄玄虚
- 预测要有理有据，结合五行生克、天象时辰
- 永远给人希望和力量，哪怕大凶也要留有余地
- 只输出纯文字，不用任何markdown格式"""

        user_prompt = f"""【今日热点事件】
{topic}

【求测者命理信息】
{bazi_info}

【今日】{today_str}

请从玄学命理角度，分析这个热点事件在明日的可能走向：
1. 给出运势等级（大吉/吉/平/凶/大凶）
2. 预测明日最可能的发展（不超过100字）
3. 给出一个基于五行/天象的命理提示或建议（不超过50字）

严格按以下JSON格式输出，不要有多余文字：
{{"level":"等级","prediction":"预测内容","advice":"命理提示"}}"""

        client = AIProvider.get_client()
        try:
            response = await asyncio.to_thread(client.generate, system_prompt, user_prompt)
        except Exception as e:
            return {"success": False, "data": None}

        # 清理响应
        import re
        response = re.sub(r'```[^`]*```', '', response)
        response = re.sub(r'<\/?think[^>]*>', '', response, flags=re.IGNORECASE)
        response = re.sub(r'<think>[\s\S]*?</think>', '', response)
        response = re.sub(r'\[/?(?:think|result)\]', '', response, flags=re.IGNORECASE)
        response = response.strip()

        # 提取JSON
        json_match = re.search(r'\{[^{}]*(?:\"level\"[^{}]*\}[^{}]*)?\}', response, re.DOTALL)
        if json_match:
            import json as _json
            parsed = _json.loads(json_match.group())
            return {"success": True, "data": {
                "level": parsed.get("level", "平"),
                "prediction": parsed.get("prediction", response[:100]),
                "advice": parsed.get("advice", ""),
            }}

        return {"success": True, "data": {
            "level": "平",
            "prediction": response[:100] if response else "天机难测，静观其变。",
            "advice": "顺势而为，趋吉避凶。",
        }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 命运热点联动 API ==========

@app.post("/api/fate/impact")
async def fate_impact_analysis(request: HotspotPredictRequest):
    """分析所有热点对用户命盘的影响，找出最相关的热点"""
    try:
        from services.ai_provider import AIProvider
        from services.metaphysics import get_current_profile

        profile = get_current_profile()
        if not profile or not profile.bazi_data:
            return {"success": False, "top_topics": [], "trend": "平"}

        bazi_data = profile.bazi_data
        bazi_list = bazi_data.get("bazi", [])
        bazi_str = " ".join([f"{g}{z}" for g, z in bazi_list]) if bazi_list else ""
        mingzhu = bazi_data.get("mingzhu", "")
        wuxing = bazi_data.get("wuxing_count", {})

        topics = request.topic_data.get("topics", []) if request.topic_data else []
        topic_titles = [t.get("title", "") for t in topics[:10] if t.get("title")]
        topics_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(topic_titles)]) or "（无热点数据）"

        # 找出用户命盘的优势领域
        max_elem = max(wuxing.items(), key=lambda x: x[1]) if wuxing else (None, 0)
        fav_elem = max_elem[0] if max_elem[1] > 0 else "金"
        fav_elem_map = {"金": "财运、事业、决断力", "木": "学业、创作、生发之力", "水": "智慧、财运、流动性", "火": "热情、社交、名声", "土": "人际、稳定、房产、田产"}

        today_str = datetime.now().strftime("%Y年%m月%d日")

        system_prompt = """你是命理大师，擅长从天象五行角度解读世间万象对个人命运的影响。

输出要求：
1. 先给出结论（用户当前运势总趋势：大吉/吉/平/小吉/小凶/凶）
2. 从10个热点中找出最影响用户命盘的2-3个
3. 说明每个热点对用户的影响方向（有利/不利/中性）
4. 用一句话说明为什么这个热点会影响该用户

只输出纯文字，不用JSON格式。语气专业但接地气，像老朋友聊天。"""

        user_prompt = f"""【用户命盘】
姓名：{profile.name}
四柱：{bazi_str}
命主：{mingzhu}
五行得分：{wuxing}
优势领域：{fav_elem_map.get(fav_elem, fav_elem)}
今日：{today_str}

【今日热点话题】
{topics_text}

请分析：
1. 用户当前整体运势趋势（结合流年、流月）
2. 哪些热点最可能影响该用户的命运（考虑五行喜忌、日主强弱）
3. 用户应该如何应对这些热点事件

只分析最相关的2-3个热点，不要每个都分析。"""

        client = AIProvider.get_client()
        try:
            response = await asyncio.to_thread(client.generate, system_prompt, user_prompt)
        except Exception as e:
            return {"success": False, "top_topics": [], "trend": "平", "error": str(e)}

        # 清理响应
        import re
        response = re.sub(r'<\/?think[^>]*>', '', response, flags=re.IGNORECASE)
        response = re.sub(r'<think>[\s\S]*?</think>', '', response)
        response = re.sub(r'\[/?(?:think|result)\]', '', response, flags=re.IGNORECASE)
        response = response.strip()

        # 从热点列表中找出最相关的
        top_topics = []
        for t in topics[:10]:
            title = t.get("title", "")
            if any(keyword in title for keyword in ["财", "钱", "投资", "股", "房", "薪", "赚"]):
                top_topics.append({**t, "impact": "财运相关", "direction": "中性"})
            elif any(keyword in title for keyword in ["婚", "恋", "爱", "桃花", "分手", "感情"]):
                top_topics.append({**t, "impact": "感情相关", "direction": "中性"})
            elif any(keyword in title for keyword in ["工作", "职场", "升职", "辞职", "裁员", "事业"]):
                top_topics.append({**t, "impact": "事业相关", "direction": "中性"})

        # 判断整体趋势
        trend = "平"
        if "大吉" in response or "上升" in response or "发力" in response:
            trend = "↑"
        elif "凶" in response or "下滑" in response or "谨慎" in response:
            trend = "↓"
        else:
            trend = "→"

        return {
            "success": True,
            "analysis": response[:500],
            "top_topics": top_topics[:3],
            "trend": trend,
            "fav_elem": fav_elem,
            "fav_area": fav_elem_map.get(fav_elem, ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fate/trend")
def fate_trend():
    """获取用户当前运势趋势（上行/平稳/下行）"""
    try:
        from services.metaphysics import get_current_profile

        profile = get_current_profile()
        if not profile or not profile.bazi_data:
            return {"success": False, "trend": "平", "direction": "→"}

        bazi_data = profile.bazi_data
        bazi_list = bazi_data.get("bazi", [])
        mingzhu = bazi_data.get("mingzhu", "")
        wuxing = bazi_data.get("wuxing_count", {})

        # 基于五行简单判断当前运势方向
        max_elem = max(wuxing.items(), key=lambda x: x[1])[0] if wuxing else "金"
        month = datetime.now().month
        hour = datetime.now().hour

        # 简单趋势判断
        direction = "→"
        msg = "运势平稳，宜守不宜攻"

        # 流年/月与日主的关系判断
        if mingzhu in ["水", "木"]:
            if month in [3, 4]:
                direction = "↑"
                msg = "木气旺盛，运势上升，创造力爆发期"
            elif month in [7, 8]:
                direction = "↓"
                msg = "金气肃杀，注意收敛，低调行事"
        elif mingzhu in ["火", "土"]:
            if month in [7, 8]:
                direction = "↑"
                msg = "火气当令，运势旺盛，名利双收"
            elif month in [1, 2]:
                direction = "↓"
                msg = "水寒土冻，运势偏弱，蓄势待发"

        return {
            "success": True,
            "trend": direction,
            "message": msg,
            "hour": hour,
        }
    except Exception as e:
        return {"success": False, "trend": "→", "message": "命盘读取中...", "error": str(e)}


@app.post("/api/fate/timing")
async def fate_timing_advice(request: FateDialogueRequest):
    """择机而行：根据用户命盘判断当前时机是否适合重大决策"""
    try:
        from services.ai_provider import AIProvider
        from services.metaphysics import get_current_profile

        profile = get_current_profile()
        if not profile or not profile.bazi_data:
            return {"success": False, "response": "请先设置您的出生信息"}

        bazi_data = profile.bazi_data
        bazi_list = bazi_data.get("bazi", [])
        bazi_str = " ".join([f"{g}{z}" for g, z in bazi_list]) if bazi_list else ""
        mingzhu = bazi_data.get("mingzhu", "")
        shengxiao = bazi_data.get("shengxiao", "")
        wuxing = bazi_data.get("wuxing_count", {})

        today_str = datetime.now().strftime("%Y年%m月%d日")
        now_hour = datetime.now().hour

        # 时辰吉凶
        shichen_map = {
            23: "子时", 0: "子时", 1: "丑时", 2: "丑时",
            3: "寅时", 4: "寅时", 5: "卯时", 6: "卯时",
            7: "辰时", 8: "辰时", 9: "巳时", 10: "巳时",
            11: "午时", 12: "午时", 13: "未时", 14: "未时",
            15: "申时", 16: "申时", 17: "酉时", 18: "酉时",
            19: "戌时", 20: "戌时", 21: "亥时", 22: "亥时",
        }
        current_shichen = shichen_map.get(now_hour, "子时")

        question = request.message or "我现在适合做重大决定吗？"

        system_prompt = """你是一位修行千年的通灵命理大师，说话风格像老朋友聊天。

【风格要求】
- 开门见山，直接给结论：现在适合/不适合做这件事
- 给出理由（从五行喜忌、时辰吉凶、流年运势角度）
- 如果不适合，说明要等到什么时候最有利
- 控制在80字以内，越短越好
- 结尾用轻松的话收尾，如"稳了"、"再等等"、"冲冲冲"等
- 只输出纯文字，不用任何markdown格式"""

        user_prompt = f"""【求测者命盘】
姓名：{profile.name}
四柱：{bazi_str}
生肖：{shengxiao}
命主：{mingzhu}
五行得分：{wuxing}

【当前时辰】{today_str} {current_shichen}

【求测问题】
"{question}"

请从命理角度判断：现在做这件事的时机是否成熟？要注意什么？

80字以内给出明确建议。"""

        client = AIProvider.get_client()
        try:
            response = await asyncio.to_thread(client.generate, system_prompt, user_prompt)
        except Exception as e:
            response = "时机难测，请稍后再试。"

        import re
        response = re.sub(r'<\/?think[^>]*>', '', response, flags=re.IGNORECASE)
        response = re.sub(r'<think>[\s\S]*?</think>', '', response)
        response = re.sub(r'\[/?(?:think|result)\]', '', response, flags=re.IGNORECASE)
        response = response.strip()

        return {"success": True, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 命运对话框API
@app.post("/api/fate/dialogue")
async def fate_dialogue(request: FateDialogueRequest):
    """占卜大师对话 - AI驱动，使用八字命理"""
    try:
        from services.metaphysics import get_current_profile, BaziCalculator
        from services.ai_provider import AIProvider

        profile = get_current_profile()
        if not profile:
            return {"success": False, "response": "请先在「我的」页面设置您的出生信息"}

        # 获取八字信息
        bazi_data = getattr(profile, "bazi_data", None) or {}
        if not bazi_data:
            return {"success": False, "analysis": "请先在「我的」页面设置您的出生信息"}

        bazi_list = bazi_data.get("bazi", [])
        bazi_str = " ".join([f"{g}{z}" for g, z in bazi_list]) if bazi_list else "未知"
        mingzhu = bazi_data.get("mingzhu", "未知")
        shengxiao = bazi_data.get("shengxiao", "")
        wuxing = bazi_data.get("wuxing_count", {})
        shichen = bazi_data.get("shichen", "")

        # 构建对话历史
        history_context = ""
        if request.conversation_history:
            for msg in request.conversation_history[-6:]:  # 最近3轮
                role = "求测者" if msg.get("role") == "user" else "通灵大师"
                history_context += f"{role}：{msg.get('content', '')}\n"

        today_info = request.today_date or datetime.now().strftime("%Y年%m月%d日")
        shichen_info = request.shichen or shichen

        system_prompt = f"""你是一位修行千年的通灵命理大师，说话风格像老朋友聊天，风趣幽默接地气，不装神秘不说废话。

【风格要求】
- 像朋友聊天一样直接，不绕弯子，开头直接给结论
- 控制在100字以内，越短越好
- 结尾用一句轻松的话收尾，比如"去吧"、"哈哈"、"稳了"等
- 多说好话，给人希望和力量，但不说假话
- 绝对不说死亡、灾难、厄运等负面内容
- 只输出纯文字，不用任何markdown格式

【求测者命盘】
姓名：{profile.name}
四柱：{bazi_str}
生肖：{shengxiao}
命主：{mingzhu}
时柱：{shichen}
五行：{", ".join([f"{k}={v}分" for k,v in wuxing.items()]) if wuxing else "未知"}

【今日】{today_info} {shichen_info}

{history_context}

请像朋友聊天一样直接回答求测者的问题，开头就给出核心结论，然后简单解释原因。"""

        client = AIProvider.get_client()
        try:
            response = await asyncio.to_thread(client.generate, system_prompt, request.message)
        except Exception as e:
            response = "占卜系统暂时无法连接，请稍后再试。"

        # 彻底去掉 think 标签
        import re
        response = re.sub(r'</?(?:think|result|python|javascript)[^>]*>.*?</(?:think|result|python|javascript)[^>]*>', '', response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(r'<think>[\s\S]*?</think>', '', response)
        response = re.sub(r'\[/?(?:think|result)\]', '', response, flags=re.IGNORECASE)
        response = response.strip()

        return {"success": True, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 微信朋友圈文案API
@app.post("/api/moments/text")
async def generate_moments_text(request: MomentsTextRequest):
    """生成微信朋友圈文案"""
    try:
        # 简单的朋友圈文案生成（待完善）
        return {"success": True, "content": request.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 占卜服务 API ====================

@app.post("/api/divination/daily")
async def daily_divination(request: DailyDivinationRequest):
    """水晶球今日运势 - AI 生成专属运势"""
    try:
        from services.metaphysics import get_current_profile
        from services.divination import DivinationService

        profile = get_current_profile()
        if not profile or not profile.bazi_data:
            raise HTTPException(status_code=400, detail="请先在「我的」页面设置您的出生信息")

        result = await DivinationService.tell_daily_fortune(
            user_question=request.question
        )

        # 自动保存记录
        DivinationService.save_record(
            record_type="daily",
            bazi_summary=result["bazi_summary"],
            ai_response=result["ai_full_response"],
            daily_fortune=result,
        )

        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/divination/daily/stream")
async def daily_divination_stream(request: DailyDivinationRequest):
    """水晶球今日运势 - SSE流式版本，首字段立即返回，运势文字边读边显示"""
    from services.metaphysics import get_current_profile
    from services.divination import DivinationService
    from services.ai_provider import AIProvider

    profile = get_current_profile()
    if not profile or not profile.bazi_data:
        raise HTTPException(status_code=400, detail="请先在「我的」页面设置您的出生信息")

    bazi_data = profile.bazi_data or {}
    bazi_list = bazi_data.get("bazi", [])
    bazi_str = " ".join([f"{g}{z}" for g, z in bazi_list]) if bazi_list else "四柱信息不完整"
    mingzhu = bazi_data.get("mingzhu", "待分析")
    shengxiao = bazi_data.get("shengxiao", "")
    gender = bazi_data.get("gender", "未知")
    today_str = datetime.now().strftime("%Y年%m月%d日")
    hour = datetime.now().hour
    shichen = DivinationService._get_current_shichen()
    ganzhi_time = DivinationService._get_gann_zhi_time(hour)
    bazi_summary = f"姓名：{profile.name} | 性别：{gender} | 四柱：{bazi_str} | 生肖：{shengxiao} | 命主：{mingzhu}命"

    # 先发送基础信息
    base_info = {
        "fortune_level": "吉",
        "year_fortune": "年运解读中...",
        "month_fortune": "月运解读中...",
        "day_fortune": "",
        "lucky_directions": ["东", "南"],
        "lucky_color": "金色",
        "lucky_number": 8,
        "health_advice": "养生建议获取中...",
        "question_answer": "",
        "bazi_summary": bazi_summary,
        "today": today_str,
        "shichen": f"{shichen}（{ganzhi_time}）",
    }

    question_block = ""
    if request.question:
        question_block = f"\n【求测者当前问题】\n\"{request.question}\"\n\n请特别针对这个问题给出命理角度的解答。"

    user_prompt = f"""{bazi_summary}

【今日】{today_str} {shichen}（{ganzhi_time}）
{question_block}

请按顺序输出：
运势等级（大吉/吉/平/凶）
年运（不超过50字）
月运（不超过50字）
日运（不超过80字）
吉位（最多2个，用顿号分隔）
幸运色
幸运数（1-9整数）
养生建议（不超过30字）
针对求测者问题的解答（如果没有问题则留空）

请严格按以下JSON格式输出，不要有多余文字：
{{"level":"等级","year":"年运","month":"月运","day":"日运","directions":["方向1","方向2"],"color":"颜色","number":数字,"health":"养生","question":"回答"}}"""

    system_prompt = """你是一位精通八字命理的通灵大师。请根据用户的八字和当前时辰，结合命理学知识，给出专业、温暖、富有洞察力的运势解读。回复要简洁有力，不超过JSON格式限制。运势等级请根据五行生克、日主强弱、流年运势综合判断。"""

    async def event_generator():
        import json as _json

        def sse_event(data):
            return f"data: {_json.dumps(data, ensure_ascii=False)}\n\n"

        client = AIProvider.get_client()
        full_text = ""

        # 先发送初始状态
        yield sse_event({"type": "init", "data": base_info})

        # 流式读取 AI 响应
        try:
            stream = client.generate_stream_async(system_prompt, user_prompt)
            async for chunk in stream:
                full_text += chunk
                # 发送实时文本片段
                safe = chunk.replace("\n", " ").replace('"', "'")
                yield sse_event({"type": "chunk", "text": safe})
        except Exception as e:
            yield sse_event({"type": "error", "error": str(e)})

        # AI 响应完成后，解析并发送完整结果
        try:
            # 清理AI响应
            ai_response = re.sub(r'```[^`]*```', '', full_text)
            ai_response = re.sub(r'<\/?think[^>]*>', '', ai_response, flags=re.IGNORECASE)
            ai_response = re.sub(r'<think>[\s\S]*?<\/think>', '', ai_response)
            ai_response = ai_response.strip()

            # 提取JSON
            json_match = re.search(r'\{[^{}]*"level"[^}]+\}', ai_response, re.DOTALL)
            if json_match:
                parsed = _json.loads(json_match.group())
                directions = parsed.get("directions", ["东", "南"])
                if isinstance(directions, str):
                    directions = [d.strip() for d in directions.split("、") if d.strip()]

                complete_data = {
                    "fortune_level": parsed.get("level", "平"),
                    "year_fortune": parsed.get("year", "年运平稳")[:200],
                    "month_fortune": parsed.get("month", "本月运势一般")[:200],
                    "day_fortune": parsed.get("day", ai_response[:200]),
                    "lucky_directions": directions[:2],
                    "lucky_color": parsed.get("color", "金色"),
                    "lucky_number": int(parsed.get("number", 8) or 8),
                    "health_advice": parsed.get("health", "今日注意休息，顺时调养")[:100],
                    "question_answer": parsed.get("question", "")[:200],
                    "ai_full_response": ai_response[:500],
                    "bazi_summary": bazi_summary,
                    "today": today_str,
                    "shichen": f"{shichen}（{ganzhi_time}）",
                }
            else:
                # 没有JSON，回退到完整文本
                complete_data = dict(base_info)
                complete_data["day_fortune"] = ai_response[:200]
                complete_data["ai_full_response"] = ai_response[:500]

            # 保存记录
            DivinationService.save_record(
                record_type="daily",
                bazi_summary=bazi_summary,
                ai_response=ai_response[:500],
                daily_fortune=complete_data,
            )

            # 发送完成事件
            yield sse_event({"type": "complete", "data": complete_data})

        except Exception as e:
            yield sse_event({"type": "error", "error": f"解析失败: {str(e)}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/divination/history")
def get_divination_history(limit: int = 20):
    """获取占卜历史记录"""
    try:
        from services.divination import DivinationService
        records = DivinationService.get_history(limit=limit)
        return {"success": True, "records": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/divination/record")
def save_divination_record(request: DivinationRecordRequest):
    """手动保存占卜记录（如占卜大师对话）"""
    try:
        from services.divination import DivinationService
        record = DivinationService.save_record(
            record_type=request.record_type,
            bazi_summary=request.bazi_summary,
            ai_response=request.ai_response,
            question=request.question,
            daily_fortune=request.daily_fortune,
        )
        return {"success": True, "record": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/hepan")
async def do_hepan(request: HepanRequest):
    """双人合盘分析"""
    try:
        from services.hepan import generate_hepan_report

        p1 = {
            "name": request.name1,
            "year": request.year1,
            "month": request.month1,
            "day": request.day1,
            "time_str": request.time_str1,
            "gender": request.gender1,
        }
        p2 = {
            "name": request.name2,
            "year": request.year2,
            "month": request.month2,
            "day": request.day2,
            "time_str": request.time_str2,
            "gender": request.gender2,
        }

        result = await generate_hepan_report(p1, p2)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import os, uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
