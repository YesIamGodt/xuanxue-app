"""双人合盘服务 - AI生成八字合盘分析"""
import asyncio
import re
from datetime import datetime
from typing import Dict, Optional, List
from config import get_settings
from services.ai_provider import AIProvider
from services.metaphysics import BaziCalculator

settings = get_settings()


def _calculate_compatibility_level(p1_wuxing: Dict, p2_wuxing: Dict,
                                   p1_mingzhu: str, p2_mingzhu: str,
                                   p1_bazi: List, p2_bazi: List) -> str:
    """基于五行相生相克计算基础契合度"""
    wx1 = p1_wuxing
    wx2 = p2_wuxing

    # 五行相生：木生火、火生土、土生金、金生水、水生木
    sheng = {
        "木": "火", "火": "土", "土": "金", "金": "水", "水": "木",
    }
    # 五行相克：木克土、土克水、水克火、火克金、金克木
    ke = {
        "木": "土", "土": "水", "水": "火", "火": "金", "金": "木",
    }

    # 计算互生互克
    score = 0
    p1_elements = list(wx1.keys())
    p2_elements = list(wx2.keys())

    for el in p1_elements:
        if wx1[el] > 0:
            # p1 的某行是否生 p2 的某行
            target = sheng.get(el, "")
            if target and wx2[target] > 0:
                score += wx1[el] * wx2[target]
            # p2 的某行是否生 p1
            if wx2[el] > 0 and sheng.get(el) in wx2:
                score += wx2[el] * wx1[sheng[el]]
            # p1 克 p2
            target = ke.get(el, "")
            if target and wx2[target] > 0:
                score -= wx1[el] * wx2[target] * 2  # 相克扣分更重

    # 日主关系（同我者、我生者、我克者、生我者）
    mingzhu1 = p1_mingzhu
    mingzhu2 = p2_mingzhu

    if mingzhu1 == mingzhu2:
        score += 5  # 同命
    elif sheng.get(mingzhu1) == mingzhu2 or sheng.get(mingzhu2) == mingzhu1:
        score += 8  # 相生
    elif ke.get(mingzhu1) == mingzhu2 or ke.get(mingzhu2) == mingzhu1:
        score -= 5  # 相克

    # 四柱对应关系
    bazi_pairs = [(p1_bazi[i], p2_bazi[i]) for i in range(4)]
    for (t1, z1), (t2, z2) in bazi_pairs:
        if t1 == t2:
            score += 3  # 天干相同
        if z1 == z2:
            score += 3  # 地支相同

    # 评分转等级
    if score >= 15:
        return "上吉"
    elif score >= 5:
        return "吉"
    elif score >= -5:
        return "中平"
    elif score >= -15:
        return "小凶"
    else:
        return "大凶"


def _analyze_element互补(p1_wuxing: Dict, p2_wuxing: Dict) -> Dict[str, str]:
    """分析五行互补关系"""
    result = {"p1_needs": [], "p2_needs": [], "互补分析": ""}

    elements = ["木", "火", "土", "金", "水"]
    for el in elements:
        cnt1 = p1_wuxing.get(el, 0)
        cnt2 = p2_wuxing.get(el, 0)
        if cnt1 == 0 and cnt2 > 0:
            result["p1_needs"].append(el)
        elif cnt2 == 0 and cnt1 > 0:
            result["p2_needs"].append(el)

    if result["p1_needs"] and result["p2_needs"]:
        result["互补分析"] = f"一方{''.join(result['p1_needs'])}弱需补，另一方{''.join(result['p2_needs'])}可相助。"
    elif result["p1_needs"]:
        result["互补分析"] = f"一方宜多接触{''.join(result['p1_needs'])}属性的环境。"
    elif result["p2_needs"]:
        result["互补分析"] = f"另一方宜多接触{''.join(result['p2_needs'])}属性的环境。"
    else:
        result["互补分析"] = "五行分布各有强弱，相处中可互补学习。"

    return result


async def generate_hepan_report(p1_info: Dict, p2_info: Dict) -> Dict:
    """AI生成双人合盘报告"""
    bazi1 = BaziCalculator.calculate_bazi(
        p1_info["year"], p1_info["month"], p1_info["day"],
        p1_info.get("time_str", "00:00"), p1_info.get("gender", "男")
    )
    bazi2 = BaziCalculator.calculate_bazi(
        p2_info["year"], p2_info["month"], p2_info["day"],
        p2_info.get("time_str", "00:00"), p2_info.get("gender", "男")
    )

    # 基础信息
    bazi_str1 = " ".join([f"{g}{z}" for g, z in bazi1["bazi"]])
    bazi_str2 = " ".join([f"{g}{z}" for g, z in bazi2["bazi"]])
    wx1 = bazi1.get("wuxing_count", {})
    wx2 = bazi2.get("wuxing_count", {})

    # 计算基础契合度
    basic_level = _calculate_compatibility_level(
        wx1, wx2, bazi1["mingzhu"], bazi2["mingzhu"],
        bazi1["bazi"], bazi2["bazi"]
    )

    # 五行互补分析
    wx_analysis = _analyze_element互补(wx1, wx2)

    p1_wx_str = " ".join([f"{el}×{cnt}" for el, cnt in wx1.items() if cnt > 0])
    p2_wx_str = " ".join([f"{el}×{cnt}" for el, cnt in wx2.items() if cnt > 0])

    user_prompt = f"""【合盘分析请求】

甲方：{p1_info["name"]} | 性别：{p1_info.get("gender","未知")} | 八字：{bazi_str1} | 生肖：{bazi1["shengxiao"]} | 命主：{bazi1["mingzhu"]} | 五行：{p1_wx_str}
乙方：{p2_info["name"]} | 性别：{p2_info.get("gender","未知")} | 八字：{bazi_str2} | 生肖：{bazi2["shengxiao"]} | 命主：{bazi2["mingzhu"]} | 五行：{p2_wx_str}

基础契合度：{basic_level}
五行互补分析：{wx_analysis["互补分析"]}

请以通灵大师身份，对这对命盘进行深度合盘分析，严格按以下JSON格式输出（不要有多余文字）：
{{
    "level": "上吉/吉/中平/小凶/大凶",
    "level_desc": "等级描述（10字内）",
    "综合评分": "75分",
    "性格相性": "性格分析（30字内）",
    "财运协同": "财运分析（30字内）",
    "感情匹配": "感情分析（30字内）",
    "冲突预警": "潜在冲突（30字内，无则填"暂无明显冲突"）",
    "最佳相处": "最佳相处方式（40字内）",
    "互补五行": "五行互补建议（30字内）",
    "summary": "一段完整的合盘综述（100字内，包含对双方的整体评价和关系建议）"
}}"""

    system_prompt = """你是一位精通八字命理的通灵大师，擅长合婚、合盘分析。请根据双方的八字，从五行生克、十神关系、命主强弱、大运流年等角度，给出专业、温暖、富有洞察力的合盘分析。回复只输出JSON，不要有多余文字。分析要客观中性，既要指出优势也要指出需要注意的地方。"""

    try:
        client = AIProvider.get_client()
        response = await client.generate_async(system_prompt, user_prompt)
    except Exception as e:
        # 如果AI失败，返回基础分析
        return {
            "p1": _format_bazi_summary(p1_info["name"], bazi1),
            "p2": _format_bazi_summary(p2_info["name"], bazi2),
            "level": basic_level,
            "level_desc": "AI分析生成中",
            "综合评分": "待分析",
            "性格相性": wx_analysis["互补分析"],
            "财运协同": "需AI深度分析",
            "感情匹配": "需AI深度分析",
            "冲突预警": "需AI深度分析",
            "最佳相处": "需AI深度分析",
            "互补五行": wx_analysis["互补分析"],
            "summary": f"基础合盘显示双方{basic_level}，{wx_analysis['互补分析']}建议进一步咨询大师。",
            "ai_raw": str(e),
        }

    # 清理响应
    response = re.sub(r'```[^`]*```', '', response)
    response = re.sub(r'<\/?think[^>]*>', '', response, flags=re.IGNORECASE)
    response = re.sub(r'<think>[\s\S]*?<\/think>', '', response)
    response = response.strip()

    # 解析JSON
    try:
        import json as _json
        json_match = re.search(r'\{[\s\S]+\}', response)
        if json_match:
            parsed = _json.loads(json_match.group())
        else:
            parsed = {}

        return {
            "p1": _format_bazi_summary(p1_info["name"], bazi1),
            "p2": _format_bazi_summary(p2_info["name"], bazi2),
            "level": parsed.get("level", basic_level),
            "level_desc": parsed.get("level_desc", ""),
            "综合评分": parsed.get("综合评分", ""),
            "性格相性": parsed.get("性格相性", ""),
            "财运协同": parsed.get("财运协同", ""),
            "感情匹配": parsed.get("感情匹配", ""),
            "冲突预警": parsed.get("冲突预警", "暂无明显冲突"),
            "最佳相处": parsed.get("最佳相处", ""),
            "互补五行": parsed.get("互补五行", wx_analysis["互补分析"]),
            "summary": parsed.get("summary", f"双方基础合盘显示{basic_level}，{wx_analysis['互补分析']}"),
            "ai_raw": response[:500],
        }
    except Exception:
        return {
            "p1": _format_bazi_summary(p1_info["name"], bazi1),
            "p2": _format_bazi_summary(p2_info["name"], bazi2),
            "level": basic_level,
            "level_desc": "分析结果",
            "综合评分": "待计算",
            "性格相性": wx_analysis["互补分析"],
            "财运协同": "AI解析失败",
            "感情匹配": "AI解析失败",
            "冲突预警": "暂无明显冲突",
            "最佳相处": wx_analysis["互补分析"],
            "互补五行": wx_analysis["互补分析"],
            "summary": f"基础合盘显示双方{basic_level}，{wx_analysis['互补分析']}",
            "ai_raw": response[:500],
        }


def _format_bazi_summary(name: str, bazi_data: Dict) -> str:
    """格式化八字概要"""
    bazi_str = " ".join([f"{g}{z}" for g, z in bazi_data["bazi"]])
    return f"{name}：{bazi_str} {bazi_data['shengxiao']} {bazi_data['mingzhu']}命"
