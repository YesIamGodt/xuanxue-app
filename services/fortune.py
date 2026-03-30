from config import get_settings
from services.ai_provider import AIProvider

settings = get_settings()
ai_client = AIProvider.get_client()

class FortuneService:
    @staticmethod
    def tell_fortune(name: str, birthday: str, question: str = None) -> str:
        """AI算命服务"""

        system_prompt = """你是一位神秘但亲切的命理师。根据用户提供的姓名和生日，结合星座、生肖等元素，为用户进行有趣的命运解读。
要求：
1. 语言要神秘但温暖，给人希望
2. 分析性格特点
3. 预测近期运势（事业、感情、财运）
4. 给出温馨的建议
5. 可以适当结合星座、生肖等元素增加趣味性
6. 如果用户有具体问题，重点解答
7. 注意：这只是娱乐性质的解读，要提醒用户命运掌握在自己手中"""

        question_part = f"\n用户具体问题：{question}" if question else ""

        user_prompt = f"""姓名：{name}
生日：{birthday}{question_part}

请为这位用户进行命理解读。注意语气要神秘但温暖，最后要提醒这只是娱乐解读。"""

        return ai_client.generate(system_prompt, user_prompt)
