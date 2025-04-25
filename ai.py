from openai import OpenAI
from tenacity import retry, stop_after_attempt
from typing import Literal

from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

@retry(stop=stop_after_attempt(3))
def ask_ai(
        mode: Literal["text", "tts", "image"],
        instructions: list[str],
        prompt: str,
        response_format=None,
        **kwargs
):
    match mode:
        case "text":
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                response_format=response_format,
                messages=[
                    {"role": "system", "content": "\n".join(instructions)},
                    {"role": "user", "content": prompt},
                ],
                **kwargs
            )
            return response.choices[0].message.parsed

        case "image":
            instructions.append(prompt)
            response = client.images.generate(
                model="gpt-image-1",
                output_format=response_format,
                prompt="\n".join(instructions),
                **kwargs
            )
            image = response.data[0]
            image.url = image.url or f"data:image/png;base64,{image.b64_json}"
            return image

        case "tts":
            with client.audio.speech.with_streaming_response.create(
                    model="gpt-4o-mini-tts",
                    instructions="\n".join(instructions),
                    input=prompt,
                    **kwargs
            ) as response:
                return response.read()

        case _:
            raise Exception(f"Unknown mode: {mode}")
