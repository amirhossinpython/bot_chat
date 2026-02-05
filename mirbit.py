from openai import OpenAI


system_prompt = """

"""

client = OpenAI(
    base_url="https://ai.liara.ir/api/v1/<>",
    api_key="",
    
)

system_prompt_res = {"role": "system", "content": system_prompt}


class MirBotClient:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt


    async def get_response_from_chat(self, user_input: str) -> str:

        try:
            completion = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    system_prompt_res,
                    {"role": "user", "content": user_input}
                ]
            )
            reply = completion.choices[0].message.content.strip()
            return reply
        except Exception as e:
            return f"خطا در ارتباط با API: {str(e)}"
