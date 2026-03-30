
# -*- coding: utf-8 -*-
"""玄学画像系统 - 用户八字计算和玄学画像刻画"""
from datetime import datetime
from typing import Dict, Optional, List

# 天干地支数据
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
SHENG_XIAO = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

# 五行数据
WU_XING = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水"
}

# 时辰数据
SHI_CHEN = [
    ("23:00", "01:00", "子"),
    ("01:00", "03:00", "丑"),
    ("03:00", "05:00", "寅"),
    ("05:00", "07:00", "卯"),
    ("07:00", "09:00", "辰"),
    ("09:00", "11:00", "巳"),
    ("11:00", "13:00", "午"),
    ("13:00", "15:00", "未"),
    ("15:00", "17:00", "申"),
    ("17:00", "19:00", "酉"),
    ("19:00", "21:00", "戌"),
    ("21:00", "23:00", "亥"),
]


class BaziCalculator:
    """八字计算器"""

    @staticmethod
    def get_shichen_from_time(time_str: str) -> str:
        """从时间字符串获取时辰"""
        try:
            if ":" not in time_str:
                return "子"
            hour = int(time_str.split(":")[0])
            for start, end, zhi in SHI_CHEN:
                start_h = int(start.split(":")[0])
                end_h = int(end.split(":")[0])
                if start_h <= hour < end_h:
                    return zhi
            if hour >= 23 or hour < 1:
                return "子"
            return "子"
        except:
            return "子"

    @staticmethod
    def calculate_bazi(
        year: int, month: int, day: int,
        time_str: str = "00:00", gender: str = "男"
    ) -> Dict:
        """计算八字（简化版）"""

        # 简化版八字计算（实际项目中需要更精确的算法）
        # 这里使用一个简化的算法用于演示
        year_gz = BaziCalculator._year_to_ganzhi(year)
        month_gz = BaziCalculator._month_to_ganzhi(year, month)
        day_gz = BaziCalculator._day_to_ganzhi(year, month, day)
        shichen = BaziCalculator.get_shichen_from_time(time_str)
        time_gz = BaziCalculator._shichen_to_ganzhi(day_gz[0], shichen)

        bazi = [
            year_gz,
            month_gz,
            day_gz,
            time_gz
        ]

        # 分析五行
        wuxing_count = BaziCalculator.analyze_wuxing(bazi)

        # 日干
        day_tian = day_gz[0]
        mingzhu = WU_XING.get(day_tian, "土")

        # 生肖
        shengxiao = SHENG_XIAO[(year - 4) % 12]

        return {
            "bazi": bazi,
            "year": year,
            "month": month,
            "day": day,
            "time": time_str,
            "gender": gender,
            "shengxiao": shengxiao,
            "mingzhu": mingzhu,
            "day_tian": day_tian,
            "wuxing_count": wuxing_count,
            "shichen": shichen
        }

    @staticmethod
    def _year_to_ganzhi(year: int) -> tuple:
        """年柱计算（简化版）"""
        tian_idx = (year - 4) % 10
        di_idx = (year - 4) % 12
        return (TIAN_GAN[tian_idx], DI_ZHI[di_idx])

    @staticmethod
    def _month_to_ganzhi(year: int, month: int) -> tuple:
        """月柱计算（简化版）"""
        year_tian = (year - 4) % 10
        # 简化的年上起月法
        month_tian_map = {
            0: ["丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁"],  # 甲己
            1: ["戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己"],  # 乙庚
            2: ["庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛"],  # 丙辛
            3: ["壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"],  # 丁壬
            4: ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙"],  # 戊癸
            5: ["丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁"],  # 甲己
            6: ["戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己"],  # 乙庚
            7: ["庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛"],  # 丙辛
            8: ["壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"],  # 丁壬
            9: ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙"],  # 戊癸
        }
        tian_list = month_tian_map.get(year_tian, month_tian_map[0])
        tian = tian_list[month - 1] if month <= 12 else tian_list[0]
        di = DI_ZHI[(month + 1) % 12]
        return (tian, di)

    @staticmethod
    def _day_to_ganzhi(year: int, month: int, day: int) -> tuple:
        """日柱计算（简化版）"""
        # 使用一个简化算法
        base = 4
        total_days = (year - 1900) * 365 + (year - 1900) // 4
        months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
            months[1] = 29
        for i in range(month - 1):
            total_days += months[i]
        total_days += day - 1
        tian_idx = (total_days + base) % 10
        di_idx = (total_days + base) % 12
        return (TIAN_GAN[tian_idx], DI_ZHI[di_idx])

    @staticmethod
    def _shichen_to_ganzhi(day_tian: str, shichen: str) -> tuple:
        """时柱计算"""
        # 日上起时法
        day_tian_idx = TIAN_GAN.index(day_tian)
        shichen_idx = DI_ZHI.index(shichen)

        tian_map = {
            0: ["戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己"],  # 甲己
            1: ["庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛"],  # 乙庚
            2: ["壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"],  # 丙辛
            3: ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙"],  # 丁壬
            4: ["丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁"],  # 戊癸
            5: ["戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己"],  # 甲己
            6: ["庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛"],  # 乙庚
            7: ["壬", "癸", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"],  # 丙辛
            8: ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙"],  # 丁壬
            9: ["丙", "丁", "戊", "己", "庚", "辛", "壬", "癸", "甲", "乙", "丙", "丁"],  # 戊癸
        }
        tian_list = tian_map.get(day_tian_idx, tian_map[0])
        tian = tian_list[shichen_idx] if shichen_idx < len(tian_list) else tian_list[0]
        return (tian, shichen)

    @staticmethod
    def analyze_wuxing(bazi: List[tuple]) -> Dict[str, int]:
        """分析五行分布"""
        count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        for tian, di in bazi:
            if tian in WU_XING:
                count[WU_XING[tian]] += 1
            # 简化版，地支五行暂时用天干替代
        return count


class UserProfile:
    """用户玄学画像"""

    def __init__(self):
        self.bazi_data: Optional[Dict] = None
        self.name: str = ""
        self.location: str = ""

    def set_profile(
        self, name: str, year: int, month: int, day: int,
        time_str: str, gender: str, location: str
    ):
        """设置用户画像"""
        self.name = name
        self.location = location
        self.bazi_data = BaziCalculator.calculate_bazi(
            year, month, day, time_str, gender
        )

    def get_profile_description(self) -> str:
        """获取用户画像描述（用于AI提示词）"""
        if not self.bazi_data:
            return "用户未设置玄学画像"

        bazi_str = "".join([f"{t}{d}" for t, d in self.bazi_data["bazi"]])
        wuxing = self.bazi_data["wuxing_count"]
        wuxing_desc = " ".join([f"{k}{v}" for k, v in wuxing.items()])

        return f"""
【用户玄学画像】
姓名：{self.name}
性别：{self.bazi_data['gender']}
出生地：{self.location}
生肖：{self.bazi_data['shengxiao']}
八字：{bazi_str}
命主：{self.bazi_data['mingzhu']}命
五行分布：{wuxing_desc}
日柱天干：{self.bazi_data['day_tian']}
时辰：{self.bazi_data['shichen']}时
""".strip()


# 全局用户画像实例
_current_profile = UserProfile()

# Profile 持久化文件
import os as _os
import json
_PROFILE_FILE = _os.path.join(_os.path.dirname(__file__), "..", "data", "user_profile.json")


def _load_profile() -> dict:
    """从文件加载用户画像"""
    try:
        if _os.path.exists(_PROFILE_FILE):
            with open(_PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_profile(data: dict):
    """保存用户画像到文件"""
    try:
        _os.makedirs(_os.path.dirname(_PROFILE_FILE), exist_ok=True)
        with open(_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# 启动时自动加载
_initial = _load_profile()
if _initial:
    _current_profile.set_profile(
        _initial.get("name", ""),
        _initial.get("year", 1990),
        _initial.get("month", 1),
        _initial.get("day", 1),
        _initial.get("time_str", "00:00"),
        _initial.get("gender", "男"),
        _initial.get("location", ""),
    )


def get_current_profile() -> UserProfile:
    """获取当前用户画像"""
    return _current_profile


def set_current_profile(
    name: str, year: int, month: int, day: int,
    time_str: str, gender: str, location: str
):
    """设置当前用户画像"""
    _current_profile.set_profile(
        name, year, month, day, time_str, gender, location
    )
    # 持久化到文件
    _save_profile({
        "name": name, "year": year, "month": month, "day": day,
        "time_str": time_str, "gender": gender, "location": location,
    })

