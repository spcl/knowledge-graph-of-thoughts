# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang
#               Jón Gunnar Hannesson

import logging
import os
import zipfile
from typing import List, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger("Controller.ExtractZipTool")

class ZipExtractor():
    def extract_zip(self, zip_path: str) -> List[str]:
        if zip_path.endswith(('.png', '.jpg', '.jpeg', '.svg')):
            return "Cannot use extract_zip tool with images: use the image_inspector tool instead!"

        if not zip_path.endswith(".zip"):
            return "Cannot use extract_zip tool with this file: try using the inspect_file_as_text tool instead!"
        # Get the directory name without the .zip extension and with 'EXTRACTED' appended
        extract_dir = os.path.join(os.path.dirname(zip_path), os.path.basename(zip_path).replace('.zip', '_EXTRACTED'))

        extracted_files = []

        # If the directory exists, remove it
        if os.path.exists(extract_dir):
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    extracted_files.append(os.path.join(root, file))
            return f"This zip file has already been extracted. Try using the inspect_file_as_text or image_inspector tool to inspect the following extracted files {extracted_files}"

        # Create the directory
        os.makedirs(extract_dir, exist_ok=True)

        # Extract the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Get the list of all extracted files
        for root, _, files in os.walk(extract_dir):
            for file in files:
                extracted_files.append(os.path.join(root, file))

        logger.info(f"Extracted files: {extracted_files}")
        return f"""
Zip file extracted.
The extracted files have the following paths: {extracted_files}.
You can use inspect_file_as_text or image_inspector tool to inspect the extracted files.
"""


class ExtractZipSchema(BaseModel):
    zip_path: str = Field(description="The full path to the zip file to extract.")

class ExtractZipTool(BaseTool):
    name: str = "extract_zip"
    # description has a limit of 1024 chars
    description: str = """
This tool extracts the contents of a zip file to a directory named after the zip file (without the .zip extension) in the same location as the zip file. 
It returns a list of the paths of all extracted files. It does **NOT** return the content of the extracted files.
Once files have been extracted, they need to be read using a different tool such as inspect_file_as_text or image_inspector. 

This tool **ONLY** handles files with a ".zip" extension.
"""
    args_schema: Type[BaseModel] = ExtractZipSchema

    def _run(self, zip_path: str) -> List[str]:
        zip_extractor = ZipExtractor()
        return zip_extractor.extract_zip(zip_path)