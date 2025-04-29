import os
import base64
import re
import io
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from collections import deque

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

from models import Story
from common import log

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
        maintain_image_style: bool = False,
):
    log.info(f"{who}: {prompt} ({bedtime=}, {include_child=}, {generate_audio=}, {generate_images=}, {maintain_image_style=})")
    story, make_audio = Story.generate(prompt=prompt, who=who, bedtime=bedtime, generate_images=generate_images, include_child=include_child)

    with ThreadPoolExecutor() as executor:
        queue = deque()
        base_image = None

        def submit(job):
            queue.append(executor.submit(job))

        if generate_images and story.images:
            for image in story.images[0:1 if maintain_image_style else None]:
                submit(image.generate)

        if generate_audio:
            submit(make_audio)
        else:
            audio_uri = None

        while queue:
            match queue.popleft().result():
                case id, image:
                    story.replace(id, image)
                    if maintain_image_style and not base_image:
                        base_image = data_uri_to_file(data_uri=image.url, file_name="base_image")
                        for image in story.images[1:]:
                            submit(lambda img=image: img.generate(base_image=base_image))
                case uri:
                    audio_uri = uri

    return {
        "file_name": f"story_{story.file_name.lower()}.html",
        "title": story.title,
        "story": story.html,
        "audio_uri": audio_uri
    }


def data_uri_to_file(data_uri: str, file_name: str = "upload"):
    header, b64data = data_uri.split(",", 1)
    ext = re.search(r"data:image/(\w+);base64", header).group(1)
    data = base64.b64decode(b64data)
    buffer = io.BytesIO(data)
    buffer.name = f"{file_name}.{ext}"
    buffer.seek(0)
    return buffer


if os.environ.get("RENDER"):
    # see https://render.com/docs/web-services#port-binding
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT")))
