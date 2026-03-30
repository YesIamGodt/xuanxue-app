from config import get_settings
from services.ai_provider import AIProvider

settings = get_settings()
ai_client = AIProvider.get_client()

class ComebackService:
    @staticmethod
    def generate_comeback(situation: str, intensity: str = "温和") -> str:
        """生成智能回怼话术"""

        intensity_prompts = {
            "温和": "礼貌但有力，不失风度",
            "中等": "一针见血，直击要害",
            "犀利": "犀利反击，让对方无言以对",
            "搞笑": "用幽默化解，既怼了人又不失风趣"
        }

        system_prompt = """你是一个高情商的沟通专家。根据用户描述的场景，提供既得体又有力的回怼话术。
要求：
1. 分析场景中的矛盾点
2. 提供几种不同的回怼方式供选择
3. 回怼要智慧、有水平，不是人身攻击
4. 可以适当使用幽默化解尴尬
5. 每种方式都要有具体的话术示例"""

        user_prompt = f"""场景：{situation}

请提供{intensity_prompts.get(intensity, intensity_prompts["温和"])}的回怼话术。
请给出3-5种不同的回怼方式，每种都标注特点。"""

        return ai_client.generate(system_prompt, user_prompt)
