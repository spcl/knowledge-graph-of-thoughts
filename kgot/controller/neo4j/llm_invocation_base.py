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

from kgot.prompts.neo4j.base_prompts import (
    DEFINE_CYPHER_QUERY_GIVEN_NEW_INFORMATION_PROMPT_TEMPLATE,
    DEFINE_MATH_TOOL_CALL_PROMPT_TEMPLATE,
    DEFINE_NEED_FOR_MATH_PROMPT_TEMPLATE,
    DEFINE_REASON_TO_INSERT_PROMPT_TEMPLATE,
    DEFINE_RETRIEVE_QUERY_PROMPT_TEMPLATE,
    DEFINE_TOOL_CALLS_PROMPT_TEMPLATE,
    FIX_CYPHER_PROMPT_TEMPLATE,
    PARSE_FINAL_SOLUTION_WITH_LLM_PROMPT_TEMPLATE,
    get_formatter,
)
from kgot.utils.llm_utils import invoke_with_retry

logger = logging.getLogger("Controller.LLMUtils")

def merge_reasons_to_insert_base(llm_planning, list_reason_to_insert: List[str], *args, **kwargs):
    # Define the output parser model
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
    logger.info(f"New Reason to Insert:\n{pformat(response, width=160)}")
    
    # logger.info(f"New Reason to Insert parsed:\n{pformat(response, width=160)}")
    return response.reason_to_insert


def define_retrieve_query_base(llm_planning, initial_query: str,
                          existing_entities_and_relationships: str, wrong_query: str,
                          *args, **kwargs):
    # Define the output parser model
    class RetrieveQuery(BaseModel):
        query: str = Field(description="The new Cypher query to retrieve data")

    prompt_template = PromptTemplate(
        input_variables=["initial_query",
                         "existing_entities_and_relationships",
                         "wrong_query"],
        template=DEFINE_RETRIEVE_QUERY_PROMPT_TEMPLATE,
    )

    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                               "existing_entities_and_relationships": existing_entities_and_relationships,
                                               "wrong_query": wrong_query})
    
    chain = llm_planning.with_structured_output(RetrieveQuery, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"New retrieve query:\n{pformat(response, width=160)}")
    # Return the wanted values
    
    query = response.query
    return query


def define_cypher_query_given_new_information_base(llm_planning, initial_query: str,
                                              existing_entities_and_relationships: str,
                                              new_information: str, missing_information: str,
                                              *args, **kwargs):
    # Define the output parser model
    class NewInformationCypherQueries(BaseModel):
        queries: list[str] = Field(description="The list of Cypher queries")

    prompt_template = PromptTemplate(
        input_variables=["initial_query",
                         "existing_entities_and_relationships", "new_information", "missing_information"],
        template=DEFINE_CYPHER_QUERY_GIVEN_NEW_INFORMATION_PROMPT_TEMPLATE,
    )

    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                              "existing_entities_and_relationships": existing_entities_and_relationships,
                                              "new_information": new_information,
                                              "missing_information": missing_information})

    chain = llm_planning.with_structured_output(NewInformationCypherQueries, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"response before parsing: {pformat(response, width=160)}")
    
    queries = response.queries
    return queries


def define_tool_calls_base(llm_execution, initial_query: str,
                      existing_entities_and_relationships: str, missing_information: str,
                      tool_calls_made: List[str],
                      *args, **kwargs):
    if tool_calls_made is None or len(tool_calls_made) == 0:
        tool_calls_made = ""
    else:
        tool_calls_made = [f"<tool_call>\n{tool_call}\n</tool_call>" for tool_call in tool_calls_made]
        tool_calls_made = "\n".join(tool_calls_made)
    prompt_template = PromptTemplate(
        input_variables=["initial_query",
                         "existing_entities_and_relationships", "missing_information",
                         "tool_calls_made"],
        template=DEFINE_TOOL_CALLS_PROMPT_TEMPLATE
    )

    # Create the chain to invoke (see RunnableSequence)
    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                               "existing_entities_and_relationships": existing_entities_and_relationships,
                                               "missing_information": missing_information,
                                               "tool_calls_made": tool_calls_made})
    logger.info(f"Tool calls made: {tool_calls_made}")

    chain = llm_execution
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"Tools to call:\n{pformat(response, width=160)}")

    # Return the wanted values
    return response.tool_calls


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


def parse_solution_with_llm_base(llm_planning, initial_query: str, partial_solution: str, gaia_formatter: bool,
                            *args, **kwargs):
    # Define the output parser model
    class Solution(BaseModel):
        final_solution: str = Field(description="The correctly formatted final solution")

    prompt_template = PromptTemplate(
        input_variables=["initial_query", "partial_solution"],
        template=get_formatter(gaia_formatter),
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


def fix_cypher_base(llm_planning, cypher_to_fix: str, error_log: str, *args, **kwargs):
    # Define the output parser model
    class CorrectJSON(BaseModel):
        cypher: str = Field(description="The corrected Cypher query")

    prompt_template = PromptTemplate(
        input_variables=["cypher_to_fix", "error_log"],
        template=FIX_CYPHER_PROMPT_TEMPLATE,
    )

    completed_prompt = prompt_template.invoke({"cypher_to_fix": cypher_to_fix,
                                               "error_log": error_log})

    # Create the chain to invoke (see RunnableSequence)
    chain = llm_planning.with_structured_output(CorrectJSON, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"Newly fixed cypher:\n{pformat(response, width=160)}")
    
    cypher = response.cypher
    return cypher
