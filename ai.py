import base64
from typing import Literal

from openai import OpenAI
from tenacity import retry, stop_after_attempt, RetryCallState

from common import log

client = OpenAI()

DEFAULT_MODELS = {
    "text": "gpt-4o-mini",
    "image": "gpt-image-1",
    "tts": "gpt-4o-mini-tts",
}


def on_retry(retry_state: RetryCallState):
    log.error(f"Retry #{retry_state.attempt_number}: {retry_state.outcome.exception()!r}")


@retry(stop=stop_after_attempt(3), before_sleep=on_retry)
def ask_ai(
        mode: Literal["text", "tts", "image"],
        instructions: list[str],
        prompt: str,
        response_format=None,
        **kwargs
):
    log.debug(f"{mode}: {instructions + [prompt]}")

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
            prompt = "\n".join(instructions + [prompt])
            if images := kwargs.pop("images"):
                kwargs.pop("background")  # not supported for edits
                response = client.images.edit(
                    model=model,
                    image=images,
                    prompt=prompt,
                    **kwargs
                )
            else:
                response = client.images.generate(
                    model=model,
                    output_format=response_format,
                    prompt=prompt,
                    **kwargs
                )
            image = response.data[0]
            image.url = image.url or f"data:image/png;base64,{image.b64_json}"
            image.alt_text = prompt
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
