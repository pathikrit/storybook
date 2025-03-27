from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


def ask_ai(
        model: str,
        instructions: list[str],
        prompt: str,
        response_format=None,
        **kwargs
):
    instructions = "\n".join(instructions)
    match model:
        case "gpt-4o-mini":
            response = client.beta.chat.completions.parse(
                model=model,
                response_format=response_format,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": prompt},
                ],
                **kwargs
            )
            return response.choices[0].message.parsed

        case "dall-e-3":
            response = client.images.generate(model=model, prompt=f"{instructions}: {prompt}", **kwargs)
            return response.data[0]

        case "gpt-4o-mini-tts":
            with client.audio.speech.with_streaming_response.create(
                    model=model,
                    instructions=instructions,
                    input=prompt,
                    **kwargs
            ) as response:
                return response.read()

        case _:
            raise Exception(f"Unknown model: {model}")
