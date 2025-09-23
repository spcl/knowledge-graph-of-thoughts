# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang
#               Jón Gunnar Hannesson

import base64
import logging
from time import time
from typing import Any, Type

import requests
from cairosvg import svg2png
from langchain.schema.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from PIL import Image
from pydantic import BaseModel, Field

from kgot.utils import UsageStatistics, llm_utils
from kgot.utils.log_and_statistics import collect_stats

logger = logging.getLogger("Controller.ImageQuestionTool")


class ImageQuestionSchema(BaseModel):
    question: str = Field(description="The question to ask about the image.")
    full_path_to_image: str = Field(description="The full path to the image file.")


def is_url(file_path):
    return file_path.startswith("http://") or file_path.startswith("https://")


class ImageQuestionTool(BaseTool):
    name: str = "image_inspector"
    # description has a limit of 1024 chars
    description: str = """
    You cannot inspect images yourself: instead call this tool to inspect an image by providing a local image file path or an image URI and ask questions about it.
    This tool handles the following file extensions: [".jpeg", ".jpg", ".png", ".svg"] it does **NOT** handle .mp3 files 

    **Usage examples:**

    1. **General inquiry with a local image:**
    ```python
    question = "What animal is depicted in this picture?"
    image_source = "/path/to/image1.jpg"
"""

    args_schema: Type[BaseModel] = ImageQuestionSchema
    image_llm: Runnable = None
    usage_statistics: UsageStatistics = None

    def __init__(self, model_name: str, temperature: float,
                 usage_statistics: UsageStatistics, **kwargs: Any):
        super().__init__(**kwargs)
        self.image_llm = llm_utils.get_llm(model_name=model_name, temperature=temperature)

        self.usage_statistics = usage_statistics

    def encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # Returns the image format (JPEG, PNG, etc.)
    def get_image_type(self, file_path):
        with Image.open(file_path) as img:
            return img.format

    @collect_stats("image_inspector")
    def _run(self, question: str, full_path_to_image: str) -> str:
        url = full_path_to_image  # If the image is from a URL, it doesn't need to be decoded https://platform.openai.com/docs/guides/vision

        if full_path_to_image.endswith('.mp3'):
            return "Cannot use image_question tool with .mp3 files: use inspect_file_as_text instead!"

        if not question:
            question = "Please write a detailed caption for this image"
            
        is_img_local = True
        if is_url(full_path_to_image):
            # Check if the URL is valid, if not return an error
            is_img_local = False
            try:
                response = requests.get(full_path_to_image)
                if response.status_code != 200:
                    return "The URL provided is not valid."

                # OpenAI does NOT support svg, therefore convert to png
                # Check the content type to determine if it's an SVG
                content_type = response.headers.get('Content-Type', '')
                if 'image/svg+xml' in content_type:
                    # Handle SVG image
                    try:
                        full_path_to_image = f"/tmp/temp_image_{int(time())}.png"  # Save as PNG
                        svg2png(bytestring=response.content, write_to=full_path_to_image)
                        logger.info(f"Downloaded and converted SVG to PNG in ImageQuestion: {full_path_to_image}")
                        is_img_local = True
                    except Exception as e:
                        logger.error(f"Failed to convert SVG to PNG in ImageQuestion from URL: {full_path_to_image}. Error: {e}")
                        return "Failed to convert SVG to PNG."
            except Exception as e:
                logger.error(f"Failed to download image from URL: {full_path_to_image}. Error: {e}")
                return "Failed to download image from URL."
        # Case not URL or SVG file downloaded locally
        if is_img_local:
            # In case the image is not a URL but is local, encode it to base64 to process it
            try:
                image_format = self.get_image_type(full_path_to_image).lower()  # Usually PNG or JPEG, but need png or jpeg
                # print(f"Image format: {image_format}")
                if not image_format:
                    image_format = "png"  # Default to png

                image_base64 = self.encode_image(full_path_to_image)
                url = f"data:image/{image_format};base64,{image_base64}"
            except Exception as e:
                logger.error(f"Failed to open image from path: {full_path_to_image}. Error: {e}")
                return "Failed to open the file as an image, try using inspect_file_as_text instead!"

        result = self.image_llm.invoke([
            SystemMessage(
                content="""You are an expert in image analysis, reading and extraction. You will be given an image along with a specific question related to that image.
                            Give an in-depth description of what is found in the image. Give an in-depth answer to the question.
                            If you are unable to answer the question, give a detailed description of the items in the image which could help someone else answer the question. 
                            Do not add any information that is not present in the image. If the image includes any code, text or numbers, transcribe it after the answer."
                            """
            ),
            HumanMessage(
                content=[
                    {"type": "text", "text": f"{question} Take a deep breath and do this step-by-step."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": url,
                            "detail": "high"
                        },
                    },
                ]
            )
        ])

        logger.info(f"ImageQuestionTool result: {result}")
        return result.content
