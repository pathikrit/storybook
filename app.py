import asyncio

import streamlit as st

from typing import List, ClassVar

from pydantic import BaseModel, Field
from litellm import image_generation, completion

class ImageTag(BaseModel):
    id: int = Field(description="Image id starting from 1 - I will use this to replace the [[replace_image_X]] tags")
    prompt: str = Field(description="The short prompt for the image that I will feed to the image generation API")

    size: ClassVar[int] = 1024

    def from_llm(self):
        return image_generation(
            model="dall-e-3",
            prompt=f"Generate a Studio Ghibli style story book image for the following prompt: {self.prompt}",
            response_format="url",
            size=f"{ImageTag.size}x{ImageTag.size}",
        )

class Story(BaseModel):
    html: str = Field(description="The story (in html that would go inside <body>)")
    images: List[ImageTag] = Field(description="The images for the story")

    @classmethod
    async def generate(cls, who: str, prompt: str, bedtime: bool):
        system_prompt = (
            f"Generate a creative {'bedtime' if bedtime else 'and engaging'} story for {who}\n"            
            "Include the child in the story also\n"
            "Return the story as html that would go inside the <body> tag\n"
            "For styles, use inline styles on the HTML elements\n"
            "Also include placeholder image tags (2-3) as follows:\n"
            f"<img src='[[replace_image_1]]' width='{ImageTag.size}' height='{ImageTag.size}'/>"
            "Return these tags separately with a short prompt that I would use an AI to generate the images"
            "I will use the [[replace_image_X]] to replace with the image urls from image generation API separately"
        )
        response = completion(
            model="gpt-4o-mini",
            response_format=cls,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        )
        story = Story.parse_raw(response.choices[0].message.content)
        for image in story.images:
            ai_image = image.from_llm()
            story.html = story.html.replace(f"[[replace_image_{image.id}]]", ai_image.data[0].url)
        return story.html


if __name__ == "__main__":
    st.title("Story Generator")
    who = st.text_input("Who:", "3-year old boy named Aidan")
    prompt = st.text_input("Prompt:", "colorful bison and a monster truck")
    bedtime = st.checkbox("Bedtime")

    if st.button("Generate Story"):
        html = asyncio.run(Story.generate(who=who, prompt=prompt, bedtime=bedtime))
        st.html(html)
