import base64
import os
import uuid
from typing import List, ClassVar
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

from pydantic import BaseModel, Field

from ai import ask_ai


class ImageTag(BaseModel):
    id: int = Field(description="Image id starting from 1 - I will use this to replace the [[replace_image_X]] tags")
    prompt: str = Field(description="The short prompt for the image that I will feed to the image generation API")
    size: ClassVar[int] = 1024


class Story(BaseModel):
    file_name: str = Field(description="File name (without extension) to export this story to a html file")
    title: str = Field(description="Title of the story")
    html: str = Field(description="The story in HTML which would go inside a div (include the title)")
    images: List[ImageTag] = Field(description="The images for the story")


app = FastAPI()


@app.get("/")
async def home():
    return FileResponse('index.html')


@app.get("/story")
@lru_cache(maxsize=10)
def story(
        who: str,
        prompt: str,
        bedtime: bool = False,
        include_child: bool = True,
        generate_audio: bool = True,
        generate_images: bool = True,
):
    story = ask_ai(
        model="gpt-4o-mini",
        instructions=[
            f"Generate a imaginative and creative {'bedtime' if bedtime else 'and engaging'} story for {who}",
            "Include the child in the story also" if include_child else "No need to include the child in the story",
            "Return the story as html (which would go inside div)",
            "Also include placeholder image tags (1-2) inside the text at appropriate locations follows:",
            "<img src='[[replace_image_1]]' hidden>",
            "Return these tags separately with a short prompt (appropriate for the section in the story) that I would use an AI to generate the images",
            "I will use the [[replace_image_X]] to replace with the image urls from image generation API separately and unhide these images",
            "Ideally, I would like one image at the start to set the scene for the story and one towards the end of the story concluding it",
            "Always bring the story to a meaningful closure and end with 'THE END'"
        ],
        prompt=prompt,
        response_format=Story
    )

    def make_image(prompt: str, consistent_style_id: str):
        return ask_ai(
            model="dall-e-3",
            instructions=[f"Generate a Studio Ghibli style story book watercolor image for the given prompt"],
            prompt=prompt,
            response_format="b64_json",
            size=f"{ImageTag.size}x{ImageTag.size}",
            consistent_style_id=consistent_style_id
        )

    def make_audio():
        return ask_ai(
            model="gpt-4o-mini-tts",
            instructions=[
                "Female, 30s, friendly, motherly, soft, slow, positive",
                f"reading a {'soothing bedtime' if bedtime else 'exciting'} story to a {who}",
                "speak slowly as if lulling a child to sleep" if bedtime else "show excitement in your voice; try to engage the child",
                "Easy and clear pronunciation for a child to understand"
            ],
            prompt=re.sub(r"<.*?>", '', story.html),  # strip html tags
            voice="coral",
            speed=0.8 if bedtime else 0.9,  # slower speed for kids
        )

    with ThreadPoolExecutor() as executor:
        parallel_tasks = []

        if generate_images:
            consistent_style_id = uuid.uuid4().hex
            for image in story.images:
                task = lambda img=image: (make_image(prompt=prompt, consistent_style_id=consistent_style_id), img.id)
                parallel_tasks.append(executor.submit(task))

        if generate_audio:
            parallel_tasks.append(executor.submit(make_audio))
        else:
            audio_uri = None

        for task in parallel_tasks:
            match task.result():
                case image, id:
                    story.html = story.html.replace(
                        f"<img src='[[replace_image_{id}]]' hidden>",
                        f"<img src='{image.url}' style='max-width: 100%; height: auto; display: block; margin: auto;'>",
                    )
                case bytes() as audio:
                    audio_uri = f"data:audio/mp3;base64,{base64.b64encode(audio).decode('utf-8')}"

    return {
        "file_name": f"story_{story.file_name.lower()}.html",
        "title": story.title,
        "story": story.html,
        "audio_uri": audio_uri
    }


if os.environ.get("RENDER"):
    # see https://render.com/docs/web-services#port-binding
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT")))
