# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: You Wu
#               
# Contributions: Lorenzo Paleari
#                Jón Gunnar Hannesson

import ast
import re
from dataclasses import dataclass
from typing import TextIO

import pandas as pd


def load_kgot_tools(f: TextIO) -> pd.DataFrame:
    """Given a 'cmd_log.log' file, load tool usage of KGoT"""
    cats, tools = {}, {}
    current = None
    patterns = {'q': re.compile(r'^Solving question (\d+):'), 't': re.compile(r'^Tool_calls:\s*(\[.*\])')}
    
    for line in f:
        if m := patterns['q'].match(line := line.strip()): 
            current = m.group(1)
            cats[current] = set()
            tools[current] = set()
        elif current and (m := patterns['t'].match(line)):
            for call in ast.literal_eval(m.group(1)):
                if tool := call.get('name'):
                    tools[current].add(tool.casefold().strip(' .').split('. ', 1)[-1])
                    cats[current].update(ToolMapping.KGOT_TOOL_TO_GAIA_CATEGORY.get(tool, set()))
    
    result = pd.DataFrame([(k, sorted(v), sorted(tools[k])) for k, v in cats.items()], 
                       columns=['question_number', 'kgot_categories', 'kgot_tools'])
    return result


def load_reference_tools(df: pd.DataFrame) -> pd.DataFrame:
    """Given a dataframe containing the 'correct_stats.json' data, extract
    the wanted GAIA tools for each question, and store them in DataFrame 
    format with list outputs."""

    # Initialize lists to store the data
    question_numbers = []
    reference_tools_list = []
    reference_categories_list = []
    
    for _, entry in df.iterrows():
        idx = str(entry.get("question_number"))
        tools_str = entry.get("tools", "").strip()
        
        # Store question number
        question_numbers.append(idx)
        
        # No tools needed
        if not tools_str or tools_str.lower() in ["none", "no tools required"]:
            reference_tools_list.append([])
            reference_categories_list.append([])
            continue

        # Tool needed, parse tool and match it to GAIA category
        tools = [tool.casefold().strip(' .').split('. ', 1)[-1] 
                for tool in tools_str.split('\n') if tool.strip()]
        
        cats = list({cat for t in tools 
                    for cat in (set(cat for cat, tools in ToolMapping.GAIA_CATEGORY_TO_TOOLS.items() 
                                   if t in tools))})
        
        reference_tools_list.append(tools)
        reference_categories_list.append(cats)

    # Create the result DataFrame
    result_df = pd.DataFrame({
        'question_number': question_numbers,
        'reference_categories': reference_categories_list,
        'reference_tools': reference_tools_list
    })
    
    return result_df

@dataclass
class ToolMapping:
    """Mapping of tools to their categories and equivalent tools"""
    KGOT_TOOL_TO_GAIA_CATEGORY = {
        "wikipedia_search": ["search_information_tools"],
        "web_crawler": ["search_information_tools"],
        "load_documents": [
            "document_access_tools",
            "audio_tools",
            "video_tools",
            "pdf_tools",
            "spreadsheet_tools",
            "text_processing_analysis_tools"
        ],
        "load_documents_and_query": ["spreadsheet_tools"],

        # tools
        "visualizer": ["image_recognition_processing_tools"],
        "image_question": ["image_recognition_processing_tools"],
        "run_python_code": ["programming_code_tools", "calculator"],
        "llm_query": [], # no tools used
        "inspect_file_as_text": ["document_access_tools", "pdf_tools", "spreadsheet_tools", "text_processing_analysis_tools"],
        "ask_search_agent": ["search_information_tools"],
        "extract_zip": ["spreadsheet_tools", "pdf_tools", "document_access_tools"],
    }

    # GAIA categories to specific tool names mapping
    GAIA_CATEGORY_TO_TOOLS = {
        "spreadsheet_tools": [
            'microsoft excel / google sheets',
            'excel',
            'spreadsheet editor',
            'access to excel files',
            'xlsx file access',
            'microsoft excel'
        ],
        "pdf_tools": [
            'pdf reader/extracter',
            'pdf access',
            'pdf reader',
            'pdf viewer'
        ],
        "document_access_tools": [
            'word document access',
            'powerpoint viewer',
            'xml file access',
            'jsonld file access',
            'csv file access',
            'txt file access',
            'json file access'
        ],
        "text_processing_analysis_tools": [
            'word reversal tool / script',
            'natural language processor',
            'text processing/diff tool',
            'text editor',
            'google translate access',
            'file interface', 'a file interface',
            'markdown',
            'file handling'
        ],
        "search_information_tools": [
            'wikipedia',
            'access to academic journal websites',
            'google search',
            'access to internet archive, web.archive.org',
            'search engine', 'a search engine',
            'access to wikipedia',
            'web browser', 'a web browser',
            'optional web browser'
        ],
        "search_location_tools": [
            'access to google maps',
            'google maps'
        ],
        "image_recognition_processing_tools": [
            'computer vision',
            'image recognition tools',
            'image recognition/ocr',
            'tool to extract text from images',
            'image processing tools',
            'image recognition',
            'image search tools',
            'image recognition software',
            'computer vision or ocr',
            'image recognition tools (to identify and parse figure with three axes)',
            'ocr',
            'color recognition',
            'image recognition and processing tools'
        ],
        "video_tools": [
            'access to youtube',
            'youtube',
            'video processing software',
            'youtube player',
            'video parsing',
            'video capability',
            'video recognition tools'
        ],
        "audio_tools": [
            'audio processing software',
            'audio capability',
            'speech-to-text tool', 'a speech-to-text tool',
            'speech-to-text audio processing tool', 'a speech-to-text audio processing tool'
        ],
        "programming_code_tools": [
            'computer algebra system',
            'code/data analysis tools',
            'python compiler',
            'python',
            'c++ compiler',
            'python ide',
            'unlambda compiler (optional)'
        ],
        "calculator": [
            'calculator (or use excel)',
            'calculator or counting function',
            'calculator (or ability to count)',
            'calculator',
            'a calculator'
        ],
        "specialized_tools": [
            'bablyonian cuniform -> arabic legend',
            'bass note data',
            "rubik's cube model",
            'counter'
        ],
        "general_utilities": [
            'gif parsing tools',
            'graph interaction tools'
        ],
        "no_tools": [
            'none',
            'no tools required'
        ]
    }