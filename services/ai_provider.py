import anthropic
import openai
import httpx
import base64
import asyncio
from config import get_settings

settings = get_settings()

class AIProvider:
    """统一的AI服务接口，支持多种提供商"""

    @staticmethod
    def get_client():
        """获取对应的AI客户端"""
        provider = settings.ai_provider.lower()

        if provider == "anthropic":
            return AnthropicClient()
        elif provider == "openai" or provider == "custom":
            return OpenAICompatibleClient()
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

class AnthropicClient:
    """Anthropic Claude API 客户端"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    def generate(self, system_prompt: str, user_prompt: str, image_data: bytes = None, image_type: str = None) -> str:
        """生成文本内容（支持图片）"""
        messages = []

        if image_data:
            # 处理图片
            base64_image = base64.b64encode(image_data).decode('utf-8')
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_type or "image/jpeg",
                            "data": base64_image
                        }
                    },
                    {"type": "text", "text": user_prompt}
                ]
            })
        else:
            messages.append({"role": "user", "content": user_prompt})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text

    async def generate_async(self, system_prompt: str, user_prompt: str,
                              temperature: float = None, max_tokens: int = None,
                              image_data: bytes = None, image_type: str = None) -> str:
        """异步生成文本内容（直接同步调用，因为是I/O密集型）"""
        return self.generate(system_prompt, user_prompt, image_data, image_type)

class OpenAICompatibleClient:
    """OpenAI兼容API客户端（支持火山引擎、Kimi等）"""

    def __init__(self):
        # 使用openai库进行调用
        if settings.is_custom_provider and settings.custom_api_url:
            # 自定义API（火山引擎等）
            self.client = openai.OpenAI(
                api_key=settings.custom_api_key,
                base_url=settings.custom_api_url.replace("/chat/completions", "")
            )
            self.model = settings.custom_model
        else:
            # 标准OpenAI
            self.client = openai.OpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model

    def generate(self, system_prompt: str, user_prompt: str, image_data: bytes = None, image_type: str = None) -> str:
        """生成文本内容（支持图片）"""
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        if image_data:
            # 处理图片
            base64_image = base64.b64encode(image_data).decode('utf-8')
            mime_type = image_type or "image/jpeg"

            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            })
        else:
            messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature
        )

        return response.choices[0].message.content

    async def generate_async(self, system_prompt: str, user_prompt: str,
                              temperature: float = None, max_tokens: int = None,
                              image_data: bytes = None, image_type: str = None) -> str:
        """异步生成文本内容（直接同步调用，因为是I/O密集型）"""
        return self.generate(system_prompt, user_prompt, image_data, image_type)

    async def generate_stream_async(self, system_prompt: str, user_prompt: str,
                                     temperature: float = None, max_tokens: int = None):
        """异步流式生成 - 在线程池中运行同步流，同步迭代器直接转为异步"""
        import concurrent.futures
        from functools import partial

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or settings.max_tokens,
            "temperature": temperature if temperature is not None else settings.temperature,
            "stream": True,
        }

        def _sync_stream():
            try:
                for chunk in self.client.chat.completions.create(**params):
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
            except Exception as e:
                yield f"[ERROR: {e}]"

        loop = asyncio.get_event_loop()
        sync_iter = _sync_stream()

        def _sync_next():
            try:
                return next(sync_iter)
            except StopIteration:
                return None
            except Exception as e:
                return None

        while True:
            chunk = await loop.run_in_executor(None, _sync_next)
            if chunk is None:
                break
            yield chunk
