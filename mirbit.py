import httpx
import asyncio
from g4f.client import Client



class MirBotClient:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.g4f_client = Client()

    async def ask_g4f(self, user_text: str, model: str = "gpt-4o-mini") -> str:
        
        try:
            full_text = f"سیستم: {self.system_prompt}\nکاربر: {user_text}"
            response = self.g4f_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": full_text}],
                web_search=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ خطا در g4f: {e}"

    async def ask_headait(
        self, user_text: str, retries: int = 3, backoff_factor: float = 1.0
    ) -> str:
       
        api_url = "https://api2.api-code.ir/gpt-4/"
        headers = {"Accept": "application/json"}
        full_text = f"سیستم: {self.system_prompt}\nکاربر: {user_text}"

        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        timeout = httpx.Timeout(15.0, connect=5.0)

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
                    response = await client.get(api_url, headers=headers, params={"text": full_text})
                    response.raise_for_status()
                    data = response.json()
                    return data.get("result") or data.get("Result") or "پاسخ نامعتبر"
            except Exception as e:
                if attempt < retries - 1:
                    wait_time = backoff_factor * (2**attempt)
                    await asyncio.sleep(wait_time)
                    continue
                return f"❌ خطا در هدایت AI: {str(e)}"

    async def generate_image(self, prompt: str, model: str = "flux") -> str:
     
        try:
            response = self.g4f_client.images.generate(
                model=model,
                prompt=prompt,
                response_format="url",
            )
            return response.data[0].url
        except Exception as e:
            return f"❌ خطا در ساخت تصویر: {e}"
    
    async def ask_gpt4(self, user_text: str) -> str:
        
       
        api_url = "https://shython-api.shayan-heidari.ir/ai"
        full_text = f"سیستم: {self.system_prompt}\nکاربر: {user_text}"

        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        timeout = httpx.Timeout(15.0, connect=5.0)

        try:
            async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
                response = await client.get(api_url, params={"prompt": full_text})
                response.raise_for_status()
                data = response.json()
                return data.get("data", "پاسخ نامعتبر")
        except Exception as e:
            return f"❌ خطا در : {str(e)}"


