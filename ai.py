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
    match model:
        case "gpt-4o-mini":
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

        case "dall-e-2" | "dall-e-3":
            consistent_style_id = kwargs.get("consistent_style_id")
            if consistent_style_id:
                del kwargs["consistent_style_id"]
                instructions.insert(0, f"Use gen id = {consistent_style_id}")
            instructions.append(prompt)
            response = client.images.generate(model=model, prompt="\n".join(instructions), **kwargs)
            return response.data[0]

        case "gpt-4o-mini-tts":
            with client.audio.speech.with_streaming_response.create(
                    model=model,
                    instructions="\n".join(instructions),
                    input=prompt,
                    **kwargs
            ) as response:
                return response.read()

        case _:
            raise Exception(f"Unknown model: {model}")
