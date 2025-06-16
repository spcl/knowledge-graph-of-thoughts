# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Jón Gunnar Hannesson
#
# Most of the code below is from the Beating GAIA with Transformers Agents repository.
# https://github.com/aymeric-roucher/GAIA/blob/main/gaia_custom_multiagent.py
#
# Copyright 2024 Aymeric Roucher
#
# Some minor modification to adapt the code to our needs were performed

import logging
import os
from typing import Any, Optional, Type

from langchain.tools import BaseTool
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field
from transformers.agents.llm_engine import MessageRole, get_clean_message_list

from kgot.tools.tools_v2_3.ExtractZipTool import ZipExtractor
from kgot.tools.tools_v2_3.MdConverter import MarkdownConverter
from kgot.utils import UsageStatistics, llm_utils
from kgot.utils.log_and_statistics import collect_stats

logger = logging.getLogger("Controller.TextInspectorTool")


class TextInspectorQuerySchema(BaseModel):
    file_path: str = Field("The path to the file you want to read as text. Must be a '.something' file, like '.pdf'. If it is an image, use the visualizer tool instead! DO NOT USE THIS TOOL FOR A WEBPAGE: use the search tool instead!")
    question: Optional[str] = Field("Your question, as a natural language sentence. Provide as much context as possible. Do not pass this parameter if you just want to directly return the content of the file.")


class TextInspectorTool(BaseTool):
    name: str = "inspect_file_as_text"
    description: str = ("""
You cannot load files yourself: instead call this tool to read a file as markdown text and ask questions about it.
The tool is able to unzip files with the extension ".zip", in which case it will return a list of the paths to each extracted file.
The tool also supports speech recognition!
This tool handles the following file extensions: [".html", ".htm", ".xlsx", ".pptx", ".wav", ".mp3", ".flac", ".pdf", ".docx"], and all other types of text files. IT DOES NOT HANDLE IMAGES.""")

    args_schema: Type[BaseModel] = TextInspectorQuerySchema
    usage_statistics: UsageStatistics = None
    llm: Runnable = None
    md_converter: MarkdownConverter = None
    default_data_folder: str = None

    def __init__(self, model_name: str, temperature: float, usage_statistics: UsageStatistics, **kwargs: Any):
        super().__init__(**kwargs)
        
        self.usage_statistics = usage_statistics
        self.llm = llm_utils.get_llm(model_name=model_name, temperature=temperature)
        self.md_converter = MarkdownConverter(self.usage_statistics)
        self.default_data_folder = "benchmarks/datasets/GAIA/attachments/validation/"


    @collect_stats("inspect_file_as_text")
    def _run(self, file_path, question: Optional[str] = None) -> str:
        if file_path[0] == "/":
            file_path = file_path[1:]
        
        # Construct the default path
        default_path = os.path.join(self.default_data_folder, os.path.basename(file_path))
        
        # Check if the file exists in the default path, if not use the provided path
        if os.path.exists(default_path):
            file_path = default_path
        
        if ".zip" in file_path:
            zip_extractor = ZipExtractor()
            return zip_extractor.extract_zip(file_path)
        
        if file_path.endswith(('.png', '.jpg', '.jpeg', '.svg')):
            return "Cannot use inspect_file_as_text tool with images: use the image_inspector tool instead!"

        result = self.md_converter.convert(file_path)
        
        if not question:
            return result.text_content
        
        messages = [
            {
                "role": "user",
                "content": "You will have to write a short caption for this file, then answer this question:"
                + question,
            },
            {
                "role": "user",
                "content": "Here is the complete file:\n### "
                + str(result.title)
                + "\n\n"
                + result.text_content[:70000],
            },
            {
                "role": "user",
                "content": "Now answer the question below. Use these three headings: '1. Short answer', '2. Extremely detailed answer', '3. Additional Context on the document and question asked'."
                + question,
            },
        ]
        openai_role_conversions = {
            MessageRole.TOOL_RESPONSE: MessageRole.USER,
        }
        
        response = self.llm.invoke(get_clean_message_list(messages, role_conversions=openai_role_conversions))
        
        return response.content
