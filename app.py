from turtledemo.sorting_animate import instructions1
from typing import List, ClassVar
import re

import streamlit as st

from pydantic import BaseModel, Field

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

class ImageTag(BaseModel):
    id: int = Field(description="Image id starting from 1 - I will use this to replace the [[replace_image_X]] tags")
    prompt: str = Field(description="The short prompt for the image that I will feed to the image generation API")

    size: ClassVar[int] = 1024

    def generate(self):
        return client.images.generate(
            model="dall-e-3",
            prompt=f"Generate a Studio Ghibli style story book image for the following prompt: {self.prompt}",
            size=f"{ImageTag.size}x{ImageTag.size}",
        )


class Story(BaseModel):
    html: str = Field(description="The story in HTML which would go inside a div")
    images: List[ImageTag] = Field(description="The images for the story")

    @classmethod
    def generate(cls, who: str, prompt: str, bedtime: bool):
        system_prompt = (
            f"Generate a creative {'bedtime' if bedtime else 'and engaging'} story for {who}\n"
            "Include the child in the story also\n"
            "Return the story as html (which would go inside div)\n"
            "Also include placeholder image tags (2-3) inside the text at appropriate locations follows:\n"
            f"<img src='[[replace_image_1]]' width='{ImageTag.size}' height='{ImageTag.size}'/>\n"
            "Return these tags separately with a short prompt (appropriate for the section in the story) that I would use an AI to generate the images\n"
            "I will use the [[replace_image_X]] to replace with the image urls from image generation API separately"
        )
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            response_format=cls,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        )
        return response.choices[0].message.parsed

    def audio(self, who: str, bedtime: bool):
        text = re.sub(r"<.*?>", '', self.html)  # strip html tags
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="coral",
            instructions = (
                "Female, 30s, friendly, motherly, soft, slow, positive\n"
                f"reading a {"soothing bedtime" if bedtime else "exciting"} story to a {who}\n"
                "Easy and clear pronunciation for a child to understand\n"
            ),
            input = text
        ) as response:
            bytes = b"".join(chunk for chunk in response)
        return bytes


if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("Story Generator")

    who = st.text_input("Who:", "3-year old boy named Aidan")
    prompt = st.text_area("Prompt:", "colorful bison and a monster truck")

    cols = st.columns(3)
    bedtime = cols[0].toggle("Bedtime")
    audio = cols[1].toggle("Audio", value=True)
    images = cols[2].toggle("Images", value=True)

    if st.button("Generate Story"):
        progress = 0
        progress_bar = st.progress(progress, text="Writing story ...")
        story = Story.generate(who=who, prompt=prompt, bedtime=bedtime)
        progress += 50
        progress_bar.progress(progress)
        audio_element = st.empty()
        story_element = st.html(story.html)

        if images:
            for image in story.images:
                progress += 10
                progress_bar.progress(progress, text=f"Drawing about '{image.prompt}' ...")
                ai_image = image.generate()
                story.html = story.html.replace(f"[[replace_image_{image.id}]]", ai_image.data[0].url)
                story_element.html(story.html)
        else:
            story_element.html(re.sub(r"<img.*?>", '', story.html))

        if audio:
            progress += 20
            progress_bar.progress(progress, "Reading the story ...")
            audio_element.audio(story.audio(who=who, bedtime=bedtime), format="audio/mp3")

        progress_bar.empty()
        st.balloons()
