import base64
from typing import Literal

from openai import OpenAI
from tenacity import retry, stop_after_attempt

from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

DEFAULT_MODELS = {
    "text": "gpt-4o-mini",
    "image": "gpt-image-1",
    "tts": "gpt-4o-mini-tts",
}

@retry(stop=stop_after_attempt(3))
def ask_ai(
        mode: Literal["text", "tts", "image"],
        instructions: list[str],
        prompt: str,
        response_format=None,
        **kwargs
):
    print(f"{mode}: {instructions + [prompt]}")
    model = kwargs.pop("model", DEFAULT_MODELS[mode])
    match mode:
        case "text":
            response = client.beta.chat.completions.parse(
                model=model,
                response_format=response_format,
                messages=[
                    {"role": "system", "content": "\n".join(instructions)},
                    {"role": "user", "content": prompt},
                ],
                **kwargs
            )
            return response.choices[0].message.parsed

        case "image":
            response = client.images.generate(
                model=model,
                output_format=response_format,
                prompt="\n".join(instructions + [prompt]),
                **kwargs
            )
            image = response.data[0]
            image.url = image.url or f"data:image/png;base64,{image.b64_json}"
            image.prompt = prompt
            return image

        case "tts":
            with client.audio.speech.with_streaming_response.create(
                    model=model,
                    instructions="\n".join(instructions),
                    input=prompt,
                    **kwargs
            ) as response:
                bytes = response.read()
                return f"data:audio/mp3;base64,{base64.b64encode(bytes).decode('utf-8')}" if response_format == "b64_uri" else bytes

        case _:
            raise Exception(f"Unknown mode: {mode}")
