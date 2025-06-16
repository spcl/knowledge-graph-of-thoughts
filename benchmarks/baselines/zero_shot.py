# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# authors:
# Andrea Jiang
# Lorenzo Paleari

import inspect
import logging
import os
from time import time
from typing import List, Tuple

from langchain_community.callbacks import get_openai_callback
from langchain_community.document_loaders import (
    CSVLoader,
    Docx2txtLoader,
    JSONLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredExcelLoader,
    UnstructuredPowerPointLoader,
    UnstructuredXMLLoader,
)
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from kgot.utils import UsageStatistics
from kgot.utils.llm_utils import get_model_configurations, init_llm_utils
from kgot.utils.log_and_statistics import setup_logger
from kgot.utils.utils import ensure_file_path_exists

system_prompt = """
You are a general AI assistant. I will ask you a question. Report your thoughts, and finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER].
YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.
If you are asked for a number, don’t use comma to write your number neither use units such as $ or percent sign unless specified otherwise.
If you are asked for a string, don’t use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.
If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string.
"""

def load_documents(directory_path: str, file_names: List[str]) -> List[Document]:
    docs: List[Document] = []
    for file_name in file_names:
        if file_name == "":
            continue

        print(f"File Path: {directory_path} and File Name: {file_name}")
        docs.extend(load_document(os.path.join(directory_path, file_name)))
    print(f"Docs: {docs}")
    return docs

def load_document(file_path: str):
    documents = []
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path, extract_images=True)
        documents.extend(loader.load())
    elif file_path.endswith('.docx') or file_path.endswith('.doc'):
        loader = Docx2txtLoader(file_path)
        documents.extend(loader.load())
    elif file_path.endswith('.txt') or file_path.endswith('.py'):
        loader = TextLoader(file_path)
        documents.extend(loader.load())
    elif file_path.endswith('.csv'):
        loader = CSVLoader(file_path)
        documents.extend(loader.load())
    elif file_path.endswith('.pptx'):
        loader = UnstructuredPowerPointLoader(file_path)
        documents.extend(loader.load())
    elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):  # Ok, -> extract only text, other stuff are lost see prob 36, 94
        loader = UnstructuredExcelLoader(file_path, mode="single")
        documents.extend(loader.load())
    elif file_path.endswith('.xml'):
        loader = UnstructuredXMLLoader(file_path, mode="single")
        documents.extend(loader.load())
    elif file_path.endswith('.json') or file_path.endswith('.jsonl') or file_path.endswith('.jsonld'):
        loader = JSONLoader(file_path=file_path, jq_schema=".",
                            text_content=False)
        documents.extend(loader.load())
    else:
        raise ValueError(f"File extension not supported: {file_path}")

    return documents


class ZeroShot:
    """
    Zero Shot LLM execution model for answering queries.

    Args:
        llm_execution_model (str): The LLM model to use for execution.
        llm_execution_temperature (float): The temperature setting for the LLM.
        logger_level (int): The logging level.
        logger_file_name (str): The name of the log file.
        logger_file_mode (str): The mode for the log file.
        statistics_file_name (str): The name of the statistics file.
    """
    def __init__(self,
                 llm_execution_model: str = "gpt-3.5-turbo",
                 llm_execution_temperature: float = None,
                 config_llm_path: str = "kgot/config_llms.json",
                 logger_level: int = logging.INFO,
                 logger_file_name: str = "output.log",
                 logger_file_mode: str = "a",
                 statistics_file_name: str = "llm_cost.json"):

        init_llm_utils(config_llm_path)
        model_config = get_model_configurations(llm_execution_model)

        if model_config["model_family"] == "OpenAI":
            llm = ChatOpenAI(
                model=model_config["model"],
                api_key=model_config["api_key"],
                max_tokens=model_config["max_tokens"] if "max_tokens" in model_config else None,
                organization=model_config["organization"],
                **{key: model_config[key] if llm_execution_temperature is None else llm_execution_temperature for key in 
                ["temperature"] if key in model_config},
                **{key: model_config[key] for key in 
                ["reasoning_effort"] if key in model_config},
            )
        elif model_config["model_family"] == "Ollama":
            llm = ChatOllama(
                model=model_config["model"],
                temperature=model_config["temperature"] if llm_execution_temperature is None else llm_execution_temperature,
                base_url="localhost:11434",
                num_ctx=model_config["num_ctx"],
                num_predict=model_config["num_predict"],
                num_batch=model_config["num_batch"],
                keep_alive=-1
            )
        
        self.llm_execution = llm

        # Checks if the given logs_file have an existing file_path, if not create the directories
        ensure_file_path_exists(logger_file_name)
        ensure_file_path_exists(statistics_file_name)

        self.logger = setup_logger("ZeroShot", level=logger_level,
                                   log_format="%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s",
                                   log_file=logger_file_name, log_file_mode=logger_file_mode, logger_propagate=False)

        self.usage_statistics = UsageStatistics(statistics_file_name)

        temperature_info = f"temperature '{self.llm_execution.temperature}'" if "temperature" in model_config else ""
        reasoning_effort_info = f"reasoning_effort '{self.llm_execution.reasoning_effort}'" if "reasoning_effort" in model_config else ""
        additional_info = f"{temperature_info} {reasoning_effort_info}".strip()

        self.logger.info(
            f"ZeroShot initialized with model '{model_config['model']}' and {additional_info}")

    def answer_query(self, query: str, file_path: str, file_names: List[str], *args, **kwargs) -> Tuple[str, int]:
        self.logger.info(f"Query: {query}")
        print(f"Query: {query}")

        docs: List[Document] = load_documents(file_path, file_names)

        if len(docs) >= 0:
            # Wrap each document with <doc> tags and add the attached_docs to the query
            wrapped_docs = ["<doc>\n{}\n</doc>".format(doc.page_content) for doc in docs]
            attached_docs = "\n\n".join(wrapped_docs)
            query = query + "\n<attached_docs>\n" + attached_docs + "\n</attached_docs>"

            print(f"Query with Attached Docs: {query}")

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": query
            }
        ]

        # Invoke the chain with the given query
        try:
            with get_openai_callback() as cb:
                time_before = time()
                response = self.llm_execution.invoke(messages)
                time_after = time()
                self.usage_statistics.log_statistic(inspect.currentframe().f_code.co_name,
                                                    time_before, time_after,
                                                    self.llm_execution.name if self.llm_execution.name else self.llm_execution.model_name if self.llm_execution.model_name else "",
                                                    cb.prompt_tokens, cb.completion_tokens, round(cb.total_cost, 6))
            self.logger.info(f"Finished Zero Shot. Final Result: {response}")

            final_answer_idx = response.content.find("FINAL ANSWER:")
            if final_answer_idx == -1:
                self.logger.error("No final answer found in the response.")
                raise Exception("No final answer found in the response.")
            
            # Return the final answer
            response.content = response.content[final_answer_idx + len("FINAL ANSWER:"):].strip()

            return response.content, 1
        except Exception as e:
            self.logger.error(f"Failed to execute zero shot query: {e}")
            raise Exception("Failed to execute zero shot query.")