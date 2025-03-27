from typing import List, ClassVar
import io

import streamlit as st

from pydantic import BaseModel, Field
import litellm

class ImageTag(BaseModel):
    id: int = Field(description="Image id starting from 1 - I will use this to replace the [[replace_image_X]] tags")
    prompt: str = Field(description="The short prompt for the image that I will feed to the image generation API")

    size: ClassVar[int] = 1024

    def generate(self):
        return litellm.image_generation(
            model="dall-e-3",
            prompt=f"Generate a Studio Ghibli style story book image for the following prompt: {self.prompt}",
            response_format="url",
            size=f"{ImageTag.size}x{ImageTag.size}",
        )


class Story(BaseModel):
    text: str = Field(description="Raw text of the story I will feed to a speech to text engine")
    html: str = Field(description="The same story (in html that would go inside <body>) to be rendered prettily")
    images: List[ImageTag] = Field(description="The images for the story")

    @classmethod
    def generate(cls, who: str, prompt: str, bedtime: bool):
        system_prompt = (
            f"Generate a creative {'bedtime' if bedtime else 'and engaging'} story for {who}\n"
            "Include the child in the story also\n"
            "Return the story as text (for audio transcription) and html that would go inside the <body> tag\n"
            "Make sure the text inside the html is same as the raw text\n"
            "For styles in the html, use inline styles on the HTML elements\n"
            "Also include placeholder image tags (2-3) in the html as follows:\n"
            f"<img src='[[replace_image_1]]' width='{ImageTag.size}' height='{ImageTag.size}'/>"
            "Return these tags separately with a short prompt that I would use an AI to generate the images"
            "I will use the [[replace_image_X]] to replace with the image urls from image generation API separately"
        )
        response = litellm.completion(
            model="gpt-4o-mini",
            response_format=cls,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        )
        story = Story.parse_raw(response.choices[0].message.content)
        for image in story.images:
            ai_image = image.generate()
            story.html = story.html.replace(f"[[replace_image_{image.id}]]", ai_image.data[0].url)
        return story

    def audio(self, who: str, bedtime: bool):
        response = litellm.speech(
            #model="gpt-4o-mini-tts",
            model="openai/tts-1",
            voice="coral",
            input=self.text,
            optional_params={
                "instructions": (
                    "Female, 30s, friendly, motherly, soft, positive\n"
                    f"reading a {"soothing bedtime" if bedtime else "exciting"} story to a {who}\n",
                    "Easy and clear pronunciation so a child can understand\n"
                )
            },
        )
        buffer = io.BytesIO()
        response.stream_to_file(buffer)
        buffer.seek(0)
        return buffer.read()


if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("Story Generator")
    who = st.text_input("Who:", "3-year old boy named Aidan")
    prompt = st.text_input("Prompt:", "colorful bison and a monster truck")
    bedtime = st.checkbox("Bedtime")

    if st.button("Generate Story"):
        story = Story.generate(who=who, prompt=prompt, bedtime=bedtime)
        st.audio(story.audio(who=who, bedtime=bedtime), format="audio/mp3")
        st.html(story.html)
