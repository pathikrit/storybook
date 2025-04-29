import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from collections import deque

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

from models import Story

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
    story, make_audio = Story.generate(prompt=prompt, who=who, bedtime=bedtime, include_child=include_child)

    with ThreadPoolExecutor() as executor:
        queue = deque()

        def submit(job):
            queue.append(executor.submit(job))

        if generate_images:
            for image in story.images:
                submit(image.generate)

        if generate_audio:
            submit(make_audio)
        else:
            audio_uri = None

        while queue:
            match queue.popleft().result():
                case id, image:
                    story.replace(id, image)
                case uri:
                    audio_uri = uri

    return {
        "file_name": f"story_{story.file_name.lower()}.html",
        "title": story.title,
        "story": story.html,
        "audio_uri": audio_uri
    }


if os.environ.get("RENDER"):
    # see https://render.com/docs/web-services#port-binding
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT")))
