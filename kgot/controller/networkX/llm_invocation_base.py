# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Lorenzo Paleari

import logging
from pprint import pformat
from typing import List

from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field

from kgot.prompts.networkX.base_prompts import (
    DEFINE_MATH_TOOL_CALL_PROMPT_TEMPLATE,
    DEFINE_NEED_FOR_MATH_PROMPT_TEMPLATE,
    DEFINE_REASON_TO_INSERT_PROMPT_TEMPLATE,
    PARSE_FINAL_SOLUTION_WITH_LLM_PROMPT_TEMPLATE,
    PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE,
    UPDATE_GRAPH_GIVEN_NEW_INFORMATION_PROMPT_TEMPLATE,
)
from kgot.utils.llm_utils import invoke_with_retry

logger = logging.getLogger("Controller.LLMUtils")


def merge_reasons_to_insert_base(llm_planning, list_reason_to_insert: List[str], *args, **kwargs):
    class ReasonToInsert(BaseModel):
        reason_to_insert: str = Field(description="The reason to insert more data")

    list_of_reasons = ["<reason>\n{}\n</reason>".format(reason) for reason in list_reason_to_insert]
    list_of_reasons = "\n".join(list_of_reasons)
    prompt_template = PromptTemplate(
        input_variables=["list_of_reasons"],
        template=DEFINE_REASON_TO_INSERT_PROMPT_TEMPLATE,
    )

    completed_prompt = prompt_template.invoke({"list_of_reasons": list_of_reasons})

    chain = llm_planning.with_structured_output(ReasonToInsert, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)

    return response.reason_to_insert


def define_write_query_given_new_information_base(llm_planning, initial_query: str,
                                              existing_entities_and_relationships: str,
                                              new_information: str, missing_information: str,
                                              *args, **kwargs):
    # Define the output parser model
    class NewInformationWriteQueries(BaseModel):
        queries: list[str] = Field(description="The list of write queries. If a query need more than one python command, it needs to be separated by a newline. Put every command related to the same query in the same string.")

    prompt_template = PromptTemplate(
        input_variables=["initial_query",
                         "existing_entities_and_relationships", "new_information", "missing_information"],
        template=UPDATE_GRAPH_GIVEN_NEW_INFORMATION_PROMPT_TEMPLATE,
    )

    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                              "existing_entities_and_relationships": existing_entities_and_relationships,
                                              "new_information": new_information,
                                              "missing_information": missing_information})

    chain = llm_planning.with_structured_output(NewInformationWriteQueries, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"response before parsing: {pformat(response, width=160)}")
    
    queries = response.queries
    return queries


def define_math_tool_call_base(llm_execution, initial_query: str,
                      solution: str, *args, **kwargs):
    prompt_template = PromptTemplate(
        input_variables=["initial_query",
                        "current_solution"],
        template=DEFINE_MATH_TOOL_CALL_PROMPT_TEMPLATE
    )

    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                               "current_solution": solution})
    
    chain = llm_execution
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"Tools to call:\n{pformat(response, width=160)}")

    # Return the wanted values
    return response.tool_calls


def define_need_for_math_before_parsing_base(llm_planning, initial_query: str, partial_solution: str,
                                    *args, **kwargs) -> bool:
    # Define the output parser model
    class NeedForMath(BaseModel):
        need_for_math: bool = Field(
            description="Boolean indicating whether we need further math or probability calculations")

    logger.info(
        f"Defining if we need more calculations given partial solution: {partial_solution} \nGiven the initial problem: {initial_query}")
    prompt_template = PromptTemplate(
        input_variables=["initial_query", "partial_solution"],
        template=DEFINE_NEED_FOR_MATH_PROMPT_TEMPLATE,
    )

    # Create the chain to invoke (see RunnableSequence)
    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                               "partial_solution": partial_solution})

    chain = llm_planning.with_structured_output(NeedForMath, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"Do we need more math:\n{pformat(response, width=160)}")

    return response.need_for_math


def parse_solution_with_llm_base(llm_planning, initial_query: str, partial_solution: str,
                            *args, **kwargs):
    # Define the output parser model
    class Solution(BaseModel):
        final_solution: str = Field(description="The correctly formatted final solution")

    prompt_template = PromptTemplate(
        input_variables=["initial_query", "partial_solution"],
        template=PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE,
    )

    # Create the chain to invoke (see RunnableSequence)
    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                               "partial_solution": partial_solution})

    chain = llm_planning.with_structured_output(Solution, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"Final solution:\n{pformat(response, width=160)}")

    return response.final_solution


def define_final_solution_base(llm_planning, initial_query: str, partial_solution: str,
                          array_solutions: List[str],
                          *args, **kwargs):
    # Define the output parser model
    class Solution(BaseModel):
        final_solution: str = Field(description="The correctly formatted final solution")

    # Format the solutions to be used in the prompt
    list_final_solutions = ["<solution>\n{}\n</solution>".format(solution) for solution in array_solutions]
    list_final_solutions = "\n".join(list_final_solutions)
    prompt_template = PromptTemplate(
        input_variables=["initial_query", "partial_solution", "list_final_solutions"],
        template=PARSE_FINAL_SOLUTION_WITH_LLM_PROMPT_TEMPLATE,
    )

    # Create the chain to invoke (see RunnableSequence)
    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                               "partial_solution": partial_solution,
                                               "list_final_solutions": list_final_solutions})

    chain = llm_planning.with_structured_output(Solution, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"Final returned solution:\n{pformat(response, width=160)}")

    return response.final_solution