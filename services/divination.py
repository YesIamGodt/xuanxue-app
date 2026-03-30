"""今日运势占卜服务 - 基于八字和 AI 生成专属命运解读"""
import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from config import get_settings
from services.ai_provider import AIProvider
from services.metaphysics import BaziCalculator, get_current_profile

settings = get_settings()

# 历史记录文件
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "divination_history.json")


def _load_history() -> List[Dict]:
    """加载占卜历史"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_history(records: List[Dict]):
    """保存占卜历史"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


class DivinationService:
    """命运占卜服务"""

    @staticmethod
    def _get_current_shichen() -> str:
        """获取当前时辰（地支）"""
        now = datetime.now()
        hour = now.hour
        shichen_map = [
            (23, 0, "子时"), (1, 2, "丑时"), (3, 4, "寅时"), (5, 6, "卯时"),
            (7, 8, "辰时"), (9, 10, "巳时"), (11, 12, "午时"), (13, 14, "未时"),
            (15, 16, "申时"), (17, 18, "酉时"), (19, 20, "戌时"), (21, 22, "亥时"),
        ]
        for start, end, name in shichen_map:
            if start <= hour <= end:
                return name
        return "子时"

    @staticmethod
    def _get_gann_zhi_time(hour: int) -> str:
        """获取当前时辰干支"""
        from services.metaphysics import BaziCalculator
        return BaziCalculator.get_shichen_from_time(f"{hour:02d}:00")

    @staticmethod
    def _build_system_prompt(bazi_info: Dict, today_str: str, shichen: str) -> str:
        """构建占卜系统提示词（融入 bazi-mingli 知识）"""

        # 获取五行相关的知识片段
        wuxing_desc = DivinationService._get_wuxing_desc(bazi_info)

        return f"""你是一位修行千年的通灵命理大师，洞察天机，语气神秘温和，充满慈爱。

【铁律】
- 以正面鼓励为主，多说好话，让人心情愉悦、充满希望
- 回复不超过200字，纯中文纯文字，不用任何markdown格式
- 遇到欠佳之处，用"若能...则更好"等委婉表达，不直说凶险
- 命由天定，运由己造，多给希望和力量

【求测者命盘】
{bazi_info.get('summary', '')}
五行：{wuxing_desc}

【今日】{today_str} {shichen}

请给出今日运势解读，多说好话给人希望。先写运势等级（大吉/吉/平/凶），再写年运、月运、日运各一句（50字内，多说好话），然后写今日吉方位、幸运色、幸运数字各一个，最后写养生建议一句。"""

    @staticmethod
    def _get_wuxing_desc(bazi_info: Dict) -> str:
        """获取五行相关描述"""
        wuxing = bazi_info.get("wuxing", {})
        if not wuxing:
            return "五行信息待分析"
        lines = [f"- {k}：{v}分" for k, v in wuxing.items()]
        return "\n".join(lines)

    @staticmethod
    async def tell_daily_fortune(user_question: Optional[str] = None) -> Dict:
        """生成今日运势（AI + 八字）

        Args:
            user_question: 用户当前想问的问题（可选）

        Returns:
            {
                "fortune_level": "大吉|吉|平|凶",
                "year_fortune": "年运描述",
                "month_fortune": "月运描述",
                "day_fortune": "日运描述",
                "lucky_directions": ["东", "南"],
                "lucky_color": "金色",
                "lucky_number": 8,
                "health_advice": "健康建议",
                "question_answer": "针对用户问题的解答（如果有）",
                "ai_full_response": "完整 AI 回复",
                "bazi_summary": "八字概要",
                "today": "今日日期",
                "shichen": "当前时辰",
            }
        """
        profile = get_current_profile()
        today = datetime.now()
        today_str = today.strftime("%Y年%m月%d日")
        hour = today.hour
        shichen = DivinationService._get_current_shichen()
        ganzhi_time = BaziCalculator.get_shichen_from_time(f"{hour:02d}:00")

        # 获取八字数据
        bazi_data = profile.bazi_data or {}
        if not bazi_data:
            return {"error": "请先在「我的」页面设置您的出生信息"}

        # 构建八字概要
        bazi_list = bazi_data.get("bazi", [])
        if bazi_list:
            bazi_str = " ".join([f"{g}{z}" for g, z in bazi_list])
        else:
            bazi_str = "四柱信息不完整"

        mingzhu = bazi_data.get("mingzhu", "待分析")
        shengxiao = bazi_data.get("shengxiao", "")
        wuxing = bazi_data.get("wuxing_count", {})
        gender = bazi_data.get("gender", "未知")

        bazi_summary = (
            f"姓名：{profile.name} | 性别：{gender} | "
            f"四柱：{bazi_str} | 生肖：{shengxiao} | 命主：{mingzhu}"
        )

        bazi_info = {
            "summary": bazi_summary,
            "wuxing": wuxing,
            "bazi_list": bazi_list,
            "mingzhu": mingzhu,
        }

        # 构建用户问题部分
        question_block = ""
        if user_question:
            question_block = f"""

【求测者当前问题】
"{user_question}"

请特别针对这个问题给出命理角度的解答。"""

        user_prompt = f"""{bazi_summary}

【今日】{today_str} {shichen}（{ganzhi_time}）

{question_block}

请按顺序输出：
运势等级（大吉/吉/平/凶）
年运（不超过50字）
月运（不超过50字）
日运（不超过80字）
吉方位（东南西北选2-3个）
幸运色（一种）
幸运数（一个数字）
养生建议（不超过30字）
{f'问题解答（不超过80字）' if user_question else ''}"""

        system_prompt = DivinationService._build_system_prompt(bazi_info, today_str, shichen)

        try:
            ai_client = AIProvider.get_client()
            ai_response = await asyncio.to_thread(
                ai_client.generate, system_prompt, user_prompt
            )
        except Exception as e:
            ai_response = f"占卜系统暂时无法连接，请稍后再试。错误：{e}"

        # 彻底去掉 think 标签
        import re
        ai_response = re.sub(r'</?(?:think|result|python|javascript)[^>]*>.*?</(?:think|result|python|javascript)[^>]*>', '', ai_response, flags=re.DOTALL | re.IGNORECASE)
        ai_response = re.sub(r'<think>[\s\S]*?</think>', '', ai_response)
        ai_response = re.sub(r'\[/?(?:think|result)\]', '', ai_response, flags=re.IGNORECASE)
        ai_response = ai_response.strip()

        # 解析 AI 回复（提取结构化信息）
        parsed = DivinationService._parse_fortune_response(ai_response)

        return {
            "fortune_level": parsed.get("level", "平"),
            "year_fortune": (parsed.get("year") or "年运平稳")[:200],
            "month_fortune": (parsed.get("month") or "本月运势一般")[:200],
            "day_fortune": (parsed.get("day") or ai_response[:200]),
            "lucky_directions": parsed.get("directions", ["东", "南"]),
            "lucky_color": parsed.get("color", "金色"),
            "lucky_number": parsed.get("number", 8),
            "health_advice": (parsed.get("health") or "今日注意休息，顺时调养")[:100],
            "question_answer": (parsed.get("question") or "")[:200],
            "ai_full_response": ai_response[:500],
            "bazi_summary": bazi_summary,
            "today": today_str,
            "shichen": f"{shichen}（{ganzhi_time}）",
        }

    @staticmethod
    def _parse_fortune_response(response: str) -> Dict:
        """从 AI 回复中解析结构化信息"""
        result = {}

        # 运势等级
        for level in ["大吉", "吉", "平", "凶"]:
            if level in response:
                result["level"] = level
                break
        if "level" not in result:
            result["level"] = "平"

        # 按行解析
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "年运" in line:
                result["year"] = line.split("年运")[-1].lstrip(":：").strip()
            elif "月运" in line:
                result["month"] = line.split("月运")[-1].lstrip(":：").strip()
            elif "日运" in line:
                result["day"] = line.split("日运")[-1].lstrip(":：").strip()
            elif "吉方位" in line:
                dirs = [d for d in ["东","南","西","北","中"] if d in line]
                if dirs:
                    result["directions"] = dirs[:4]
            elif "幸运色" in line:
                colors = ["金色","红色","蓝色","绿色","紫色","白色","黑色","黄色","粉色","橙色"]
                for c in colors:
                    if c in line:
                        result["color"] = c
                        break
            elif "幸运数" in line or "幸运数字" in line:
                import re
                nums = re.findall(r"\d+", line)
                if nums:
                    result["number"] = int(nums[0])
            elif "养生" in line or "健康" in line:
                val = line.split(":")[-1].split("。")[0].strip()
                if val:
                    result["health"] = val
            elif "问题解答" in line or "解答" in line:
                result["question"] = line.split(":")[-1].strip()

        # 默认值
        if "color" not in result:
            result["color"] = "金色"
        if "number" not in result:
            result["number"] = 8
        if "directions" not in result:
            result["directions"] = ["东", "南"]
        if "year" not in result:
            result["year"] = response[:60]
        if "month" not in result:
            result["month"] = response[:60]
        if "day" not in result:
            result["day"] = response[:120]

        return result

    @staticmethod
    def save_record(
        record_type: str,
        bazi_summary: str,
        ai_response: str,
        question: Optional[str] = None,
        daily_fortune: Optional[Dict] = None
    ) -> Dict:
        """保存一条占卜记录"""
        records = _load_history()

        record = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "type": record_type,  # "daily" | "question"
            "bazi_summary": bazi_summary,
            "question": question,
            "ai_response": ai_response,
            "daily_fortune": daily_fortune,
        }

        records.insert(0, record)  # 最新在前
        # 最多保留 100 条
        records = records[:100]

        _save_history(records)
        return record

    @staticmethod
    def get_history(limit: int = 20) -> List[Dict]:
        """获取占卜历史"""
        records = _load_history()
        return records[:limit]
