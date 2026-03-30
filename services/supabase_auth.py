"""
Supabase 认证和数据库服务
免费 PostgreSQL: supabase.com
免费额度: 500MB 数据库, 不限认证用户

设置步骤:
1. 注册 supabase.com (用 GitHub 账号)
2. 创建新项目 -> Settings -> API
3. 复制 Project URL 和 anon/public key 到 .env:
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_ANON_KEY=eyJxxx
4. 在 Supabase SQL Editor 执行下方的建表语句
"""
import os
from typing import Optional
from config import get_settings

settings = get_settings()

# 数据库建表 SQL（在 Supabase SQL Editor 执行一次即可）
DATABASE_SCHEMA = """
-- 用户玄学画像表
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    name TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    time_str TEXT DEFAULT '00:00',
    gender TEXT DEFAULT '男',
    location TEXT DEFAULT '未知',
    bazi_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 占卜历史记录表
CREATE TABLE IF NOT EXISTS divination_records (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    record_type TEXT NOT NULL,         -- 'daily' | 'question'
    bazi_summary TEXT,
    question TEXT,
    ai_response TEXT,
    daily_fortune JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 启用 Row Level Security
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE divination_records ENABLE ROW LEVEL SECURITY;

-- 用户只能读写自己的数据
CREATE POLICY "Users can manage own profile" ON user_profiles
    FOR ALL USING (auth.uid() = id);

CREATE POLICY "Users can manage own records" ON divination_records
    FOR ALL USING (auth.uid() = user_id);
"""


def get_supabase_client():
    """获取 Supabase 客户端（带认证）"""
    try:
        from supabase import create_client, Client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_ANON_KEY", "")
        if url and key:
            return create_client(url, key)
    except Exception as e:
        print(f"[Supabase] 初始化失败: {e}")
    return None


def get_service_client():
    """服务端专用 client（绕过 RLS，用于管理操作）"""
    try:
        from supabase import create_client, Client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None


class SupabaseAuthService:
    """Supabase 认证服务"""

    @staticmethod
    def is_enabled() -> bool:
        """检查是否配置了 Supabase"""
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_ANON_KEY", "")
        return bool(url and key)

    @staticmethod
    def sign_up(email: str, password: str) -> dict:
        """用户注册"""
        client = get_supabase_client()
        if not client:
            return {"success": False, "error": "Supabase 未配置，请联系管理员"}
        try:
            response = client.auth.sign_up({"email": email, "password": password})
            user = response.user
            if user:
                return {"success": True, "user_id": str(user.id)}
            return {"success": False, "error": "注册失败"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def sign_in(email: str, password: str) -> dict:
        """用户登录"""
        client = get_supabase_client()
        if not client:
            return {"success": False, "error": "Supabase 未配置"}
        try:
            response = client.auth.sign_in_with_password({"email": email, "password": password})
            session = response.session
            if session:
                return {
                    "success": True,
                    "access_token": session.access_token,
                    "refresh_token": session.refresh_token,
                    "user_id": str(response.user.id),
                }
            return {"success": False, "error": "登录失败"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def sign_out(access_token: str) -> bool:
        """用户登出"""
        client = get_supabase_client()
        if not client:
            return False
        try:
            client.auth.set_session(access_token, "")
            client.auth.sign_out()
            return True
        except Exception:
            return False

    @staticmethod
    def get_user(access_token: str) -> Optional[dict]:
        """验证 token 并获取用户信息"""
        client = get_supabase_client()
        if not client:
            return None
        try:
            client.auth.set_session(access_token, "")
            user = client.auth.get_user()
            if user:
                return {
                    "id": str(user.user.id),
                    "email": user.user.email,
                }
        except Exception:
            pass
        return None


class SupabaseDbService:
    """Supabase 数据库服务（用户画像 + 占卜记录）"""

    @staticmethod
    def save_profile(user_id: str, profile_data: dict) -> bool:
        """保存或更新用户画像"""
        client = get_supabase_client()
        if not client:
            return False
        try:
            data = {
                "id": user_id,
                "name": profile_data.get("name", ""),
                "year": profile_data.get("year", 2000),
                "month": profile_data.get("month", 1),
                "day": profile_data.get("day", 1),
                "time_str": profile_data.get("time_str", "00:00"),
                "gender": profile_data.get("gender", "男"),
                "location": profile_data.get("location", "未知"),
                "bazi_data": profile_data.get("bazi_data", {}),
                "updated_at": "NOW()",
            }
            client.table("user_profiles").upsert(data).execute()
            return True
        except Exception as e:
            print(f"[SupabaseDb] 保存画像失败: {e}")
            return False

    @staticmethod
    def get_profile(user_id: str) -> Optional[dict]:
        """获取用户画像"""
        client = get_supabase_client()
        if not client:
            return None
        try:
            response = client.table("user_profiles").select("*").eq("id", user_id).execute()
            if response.data:
                return response.data[0]
        except Exception:
            pass
        return None

    @staticmethod
    def save_divination_record(user_id: str, record: dict) -> bool:
        """保存占卜记录"""
        client = get_supabase_client()
        if not client:
            return False
        try:
            data = {
                "user_id": user_id,
                "record_type": record.get("record_type", "daily"),
                "bazi_summary": record.get("bazi_summary", ""),
                "question": record.get("question"),
                "ai_response": record.get("ai_response", ""),
                "daily_fortune": record.get("daily_fortune", {}),
            }
            client.table("divination_records").insert(data).execute()
            return True
        except Exception as e:
            print(f"[SupabaseDb] 保存占卜记录失败: {e}")
            return False

    @staticmethod
    def get_divination_history(user_id: str, limit: int = 20) -> list:
        """获取用户占卜历史"""
        client = get_supabase_client()
        if not client:
            return []
        try:
            response = (
                client.table("divination_records")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception:
            return []
