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
# Some minor modification and addition of tools to adapt the code to our needs were performed

import logging
from typing import Any, Type

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from transformers.agents import ReactJsonAgent
from transformers.agents.llm_engine import MessageRole, get_clean_message_list
from transformers.agents.prompts import DEFAULT_REACT_JSON_SYSTEM_PROMPT

from kgot.tools.tools_v2_3.Web_surfer import (
    ArchiveSearchTool,
    FinderTool,
    FindNextTool,
    FullPageSummaryTool,
    NavigationalSearchTool,
    PageDownTool,
    PageUpTool,
    SearchInformationTool,
    VisitTool,
)
from kgot.tools.tools_v2_3.WikipediaTool import HuggingFaceAgentsWikipediaTool
from kgot.utils import UsageStatistics, llm_utils
from kgot.utils.llm_utils import invoke_with_retry
from kgot.utils.log_and_statistics import collect_stats

logger = logging.getLogger("Controller.SurferTool")

class OpenAIModel:
    def __init__(self, model_name="gpt-4o", temperature=0.5, usage_statistics: UsageStatistics = None):
        self.model_name = model_name
        self.temperature = temperature
        self.usage_statistics = usage_statistics
        self.llm = llm_utils.get_llm(model_name=model_name, temperature=temperature)

    @collect_stats("SurferTool.__call__")
    def __call__(self, messages, stop_sequences=[]):
        
        openai_role_conversions = {
            MessageRole.TOOL_RESPONSE: MessageRole.USER,
        }
        messages = get_clean_message_list(messages, role_conversions=openai_role_conversions)

        # Convert messages into a list of BaseMessage if needed
        formatted_messages = [
            SystemMessage(content=msg["content"]) if msg["role"] == "system" else
            HumanMessage(content=msg["content"]) if msg["role"] == "user" else
            AIMessage(content=msg["content"])  # For AI responses
            for msg in messages
        ]

        response = invoke_with_retry(self.llm, formatted_messages, stop = stop_sequences)
        return response.content
    

class SearchToolSchema(BaseModel):
    query: str = Field("Your question, as a natural language sentence with a verb! You are talking to an human, so provide them with as much context as possible! DO NOT ASK a google-like query like 'paper about fish species 2011': instead ask a real sentence like: 'What appears on the last figure of a paper about fish species published in 2011?'")


class SearchTool(BaseTool):
    name : str = "ask_search_agent"
    description: str = ("""
This will send a message to a team member that will browse the internet to answer your question.
Ask him for all your web-search related questions, but he's unable to do problem-solving.
Provide him as much context as possible, in particular if you need to search on a specific timeframe!
And don't hesitate to provide them with a complex search task, like finding a difference between two webpages.
""")

    args_schema: Type[BaseModel] = SearchToolSchema
    surfer_agent: ReactJsonAgent = None

    def __init__(self, model_name: str, temperature: float, usage_statistics: UsageStatistics, **kwargs: Any):
        super().__init__(**kwargs)
        wikipedia_tool = HuggingFaceAgentsWikipediaTool(model_name=model_name, temperature=temperature, usage_statistics=usage_statistics)
        full_page_tool = FullPageSummaryTool(model_name=model_name, temperature=temperature, usage_statistics=usage_statistics)
        llm_engine = OpenAIModel(model_name=model_name, temperature=temperature, usage_statistics=usage_statistics)
        self.surfer_agent = ReactJsonAgent(
            llm_engine=llm_engine,
            tools=[
                SearchInformationTool(),
                NavigationalSearchTool(),
                VisitTool(),
                PageUpTool(),
                PageDownTool(),
                FinderTool(),
                FindNextTool(),
                ArchiveSearchTool(),
                full_page_tool,
                wikipedia_tool,
            ],
            max_iterations=12,
            verbose=2,
            system_prompt=DEFAULT_REACT_JSON_SYSTEM_PROMPT + "\nAdditionally, if after some searching you find out that you need more information to answer the question, you can use `final_answer` with your request for clarification as argument to request for more information.",
            planning_interval=4,
        )

    def _run(self, query: str) -> str:
        final_answer = self.surfer_agent.run(f"""
You've been submitted this request by your manager: '{query}'

You're helping your manager solve a wider task: so make sure to not provide a one-line answer, but give as much information as possible so that they have a clear understanding of the answer.

Your final_answer WILL HAVE to contain these parts:
### 1. Search outcome (short version):
### 2. Search outcome (extremely detailed version):
### 3. Additional context:

Put all these in your final_answer, everything that you do not pass as an argument to final_answer will be lost.

You can navigate to .txt or .pdf online files using your 'visit_page' tool.
If it's another format, you can return the url of the file, and your manager will handle the download and inspection from there.

And even if your search is unsuccessful, please return as much context as possible, so they can act upon this feedback.
""")
        answer = str(final_answer)
        return answer
