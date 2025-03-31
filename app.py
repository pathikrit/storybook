import base64
import uuid
from typing import List, ClassVar
import re
from concurrent.futures import ThreadPoolExecutor

from mako.template import Template

from pydantic import BaseModel, Field

from ai import ask_ai


class ImageTag(BaseModel):
    id: int = Field(description="Image id starting from 1 - I will use this to replace the [[replace_image_X]] tags")
    prompt: str = Field(description="The short prompt for the image that I will feed to the image generation API")

    size: ClassVar[int] = 1024

    def generate(self, consistent_style_id):
        return ask_ai(
            model="dall-e-3",
            instructions=[f"Generate a Studio Ghibli style story book watercolor image for the given prompt"],
            prompt=self.prompt,
            response_format="b64_json",
            size=f"{ImageTag.size}x{ImageTag.size}",
            consistent_style_id=consistent_style_id
        )


class Story(BaseModel):
    file_name: str = Field(
        description="File name (without extension) to export this story to a html file like [story_{file_name}.html]")
    title: str = Field(description="Title of the story")
    html: str = Field(description="The story in HTML which would go inside a div")
    images: List[ImageTag] = Field(description="The images for the story")

    @classmethod
    def generate(cls, who: str, prompt: str, bedtime: bool, include_child: bool):
        return ask_ai(
            model="gpt-4o-mini",
            instructions=[
                f"Generate a imaginative and creative {'bedtime' if bedtime else 'and engaging'} story for {who}",
                "Include the child in the story also" if include_child else "No need to include the child in the story",
                "Return the story as html (which would go inside div)",
                "Also include placeholder image tags (1-2) inside the text at appropriate locations follows:",
                "<img src='[[replace_image_1]]' hidden>"
                "Return these tags separately with a short prompt (appropriate for the section in the story) that I would use an AI to generate the images",
                "I will use the [[replace_image_X]] to replace with the image urls from image generation API separately and unhide these images"
                "Always bring the story to a meaningful closure and end with 'THE END'"
            ],
            prompt=prompt,
            response_format=cls
        )

    def audio(self, who: str, bedtime: bool):
        return ask_ai(
            model="gpt-4o-mini-tts",
            instructions=[
                "Female, 30s, friendly, motherly, soft, slow, positive",
                f"reading a {'soothing bedtime' if bedtime else 'exciting'} story to a {who}",
                "speak slowly as if lulling a child to sleep" if bedtime else "show excitement in your voice; try to engage the child",
                "Easy and clear pronunciation for a child to understand"
            ],
            prompt=re.sub(r"<.*?>", '', self.html),  # strip html tags
            voice="coral",
            speed=0.8 if bedtime else 0.9,  # slower speed for kids
        )

def streamlit_app():
    import streamlit as st

    export = Template(filename='download.html')
    st.set_page_config(layout="wide")
    st.title("Story Generator")

    who = st.text_input("Who:", "3-year old boy named Aidan")
    prompt = st.text_area("Prompt:", "colorful bison and a monster truck")

    c1, c2, c3, c4 = st.columns(4)
    bedtime = c1.toggle("Bedtime mode (calm voice)")
    include_child = c2.toggle("Include child in story", value=True)
    generate_audio = c3.toggle("Read story aloud", value=True)
    generate_images = c4.toggle("Include images in story", value=True)

    if st.button("Make Story"):
        with st.status(label="Writing story ...", expanded=False) as status:
            story = Story.generate(who=who, prompt=prompt, bedtime=bedtime, include_child=include_child)
            audio_element = st.empty()
            download_element = st.empty()
            story_element = st.html(story.html)

            with ThreadPoolExecutor() as executor:
                parallel_tasks = []

                if generate_images:
                    consistent_style_id = uuid.uuid4().hex
                    for image in story.images:
                        status.update(label=f"Drawing {image.prompt} ...")
                        task = lambda img=image: (img.generate(consistent_style_id=consistent_style_id), img.id)
                        parallel_tasks.append(executor.submit(task))

                if generate_audio:
                    status.update(label=f"Recording the story about {story.title} ...")
                    parallel_tasks.append(executor.submit(story.audio, who=who, bedtime=bedtime))
                else:
                    audio = None

                for task in parallel_tasks:
                    match task.result():
                        case image, id:
                            story.html = story.html.replace(
                                f"<img src='[[replace_image_{id}]]' hidden>",
                                f"<img src='{image.url}' style='max-width: 100%; height: auto; display: block; margin: auto;'>",
                            )
                            story_element.html(story.html)
                        case bytes() as audio:
                            audio_element.audio(audio, format="audio/mp3", autoplay=True)
                            status.update(label="Reading story ...", expanded=True)

            download_element.download_button(
                label="Download Story",
                on_click="ignore",  # keep the rest of the app running
                mime="text/html",
                file_name=f"story_{story.file_name}.html",
                data=export.render(
                    story=story,
                    b64_audio=base64.b64encode(audio).decode('utf-8') if audio else None
                ),
            )

            status.update(label="Story is ready!", state="complete", expanded=True)
            st.balloons()

if __name__ == "__main__":
    streamlit_app()
