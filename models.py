import re
from typing import List, ClassVar

from pydantic import BaseModel, Field

from ai import ask_ai


class ImageTag(BaseModel):
    id: int = Field(description="Image id starting from 1 - I will use this to replace the [[replace_image_X]] tags")
    prompt: str = Field(description="\n".join([
        "The prompt for the image that I will feed to the image generation API",
        "Must be detailed pertaining to location in the story wrt to the image tag id"
    ]))
    size: ClassVar[int] = 1024

    def generate(self, base_image=None):
        image = ask_ai(
            mode="image",
            instructions=[
                "Generate a children's storybook image for the given prompt",
                "Use the provided base image as template to make sure to keep the same characters and style" if base_image else "",
                "Make sure that there are no texts in the generated image",
            ],
            prompt=self.prompt,
            response_format="png",
            background="transparent",
            images=[base_image] if base_image else None,
            quality="medium",
            size=f"{ImageTag.size}x{ImageTag.size}"
        )
        return self.id, image


class Story(BaseModel):
    file_name: str = Field(description="File name (without extension) to export this story to a html file")
    title: str = Field(description="Title of the story")
    html: str = Field(description="The story in HTML which would go inside a div (include the title)")
    images: List[ImageTag] = Field(description="The images for the story")

    @classmethod
    def generate(cls, prompt: str, who: str, bedtime: bool, generate_images: bool, include_child: bool):
        image_instr = [
            "Also include two placeholder image tags inside the text at appropriate locations as follows:",
            "<img src='[[replace_image_1]]' hidden>",
            "Return these tags separately with a short prompt (appropriate for the section in the story) that I would use an AI to generate the images",
            "Every image prompt must include detailed descriptions of the story characters to allow similar character generation by AI"
            "I will use the [[replace_image_X]] to replace with the image urls from image generation API separately and unhide these images",
            "Ideally, I would like one image at the start to set the scene for the story and one towards the end of the story concluding it",
        ]
        story = ask_ai(
            mode="text",
            instructions=[
                f"Generate a imaginative and creative {'bedtime' if bedtime else 'and engaging'} story for {who}",
                "Include the child in the story also" if include_child else "No need to include the child in the story",
                "Return the story as html (which would go inside div)",
                *(image_instr if generate_images else []),
                "Always bring the story to a meaningful closure and end with 'THE END'"
            ],
            prompt=prompt,
            response_format=cls
        )

        def audio_generator():
            return ask_ai(
                mode="tts",
                instructions=[
                    "Female, 30s, friendly, motherly, soft, slow, positive",
                    f"reading a {'soothing bedtime' if bedtime else 'exciting'} story to a {who}",
                    "speak slowly as if lulling a child to sleep" if bedtime else "show excitement in your voice; try to engage the child",
                    "Easy and clear pronunciation for a child to understand"
                ],
                prompt=re.sub(r"<.*?>", '', story.html),  # strip html tags
                voice="coral",
                speed=0.8 if bedtime else 0.9,  # slower speed for kids
                response_format="b64_uri"
            )

        return story, audio_generator

    def replace(self, id, image):
        self.html = self.html.replace(
            f"<img src='[[replace_image_{id}]]' hidden>",
            f"<img src='{image.url}' alt='{image.alt_text}' style='max-width: 100%; height: auto; display: block; margin: auto;'>",
        )
