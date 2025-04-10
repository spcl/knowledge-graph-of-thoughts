# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang

from typing import Any, Type

from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from kgot.utils import UsageStatistics, llm_utils
from kgot.utils.log_and_statistics import collect_stats


class LLMQuerySchema(BaseModel):
    query: str = Field(description="The query string to ask the LLM.")


class LangchainLLMTool(BaseTool):
    name: str = "llm_query"
    description: str = """
This tool interfaces with a Large Language Model (LLM) to generate responses based on provided inputs. Use it for tasks such as text generation, summarization, question answering, and more. To achieve the best results, be *as specific and verbose as possible* in your query. The query is the only source of information you can pass to the LLM.

Limitations:
- The LLM might produce responses that are not factually accurate or relevant if the input is ambiguous or lacks context.
- The LLM is not great at math nor at probability related queries.
- The LLM has a knowledge cutoff date and may not be aware of recent events or advancements.

Usage examples:
1. Question Answering:
query = "What are the benefits of renewable energy?"
# print(response) = "Renewable energy sources, such as solar, wind, and hydropower, ..."

2. Summarization:
query = "Summarize the following text: 'Artificial intelligence refers to the simulation of human intelligence in...'"
# print(response) = "AI simulates human intelligence in ..."
"""
    args_schema: Type[BaseModel] = LLMQuerySchema
    llm: Runnable = None
    usage_statistics: UsageStatistics = None

    def __init__(self, model_name: str, temperature,
                 usage_statistics: UsageStatistics, **kwargs: Any):
        super().__init__(**kwargs)

        self.llm = llm_utils.get_llm(model_name=model_name, temperature=temperature)

        self.usage_statistics = usage_statistics

    @collect_stats("llm_query")
    def _run(self, query: str):
        result = self.llm.invoke(query).content

        return result