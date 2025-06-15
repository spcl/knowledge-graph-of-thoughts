# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Lorenzo Paleari
#
# Contributions: Jón Gunnar Hannesson

import logging
from pprint import pformat
from typing import List

from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field

from kgot.controller.sparql.llm_invocation_base import (
    define_sparql_query_given_new_information_base,
    define_final_solution_base,
    define_math_tool_call_base,
    define_need_for_math_before_parsing_base,
    define_retrieve_query_base,
    define_tool_calls_base,
    fix_sparql_base,
    merge_reasons_to_insert_base,
    parse_solution_with_llm_base,
)
from kgot.prompts.sparql.queryRetrieve.prompts import (
    DEFINE_FORCED_RETRIEVE_QUERY_TEMPLATE,
    DEFINE_FORCED_SOLUTION_TEMPLATE,
    DEFINE_NEXT_STEP_PROMPT_TEMPLATE,
)
from kgot.utils.llm_utils import invoke_with_retry
from kgot.utils.log_and_statistics import collect_stats

logger = logging.getLogger("Controller.LLMUtils")

@collect_stats("Controller.define_next_step")
def define_next_step(llm_planning, initial_query: str,
                     existing_entities_and_relationships: str,
                     tool_calls_made: str,
                     *args, **kwargs):
    # Define the output parser model
    class NextStepQuery(BaseModel):
        query: str = Field(description="The new SPARQL query to retrieve data")
        query_type: str = Field(description="INSERT or RETRIEVE, depending on the given query")

    prompt_template = PromptTemplate(
        input_variables=["initial_query",
                         "existing_entities_and_relationships",
                         "tool_calls_made"],
        template=DEFINE_NEXT_STEP_PROMPT_TEMPLATE,
    )

    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                               "existing_entities_and_relationships": existing_entities_and_relationships,
                                               "tool_calls_made": tool_calls_made})

    chain = llm_planning.with_structured_output(NextStepQuery, method="json_schema")

    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"New query:\n{pformat(response, width=160)}")

    query = response.query
    query_type = response.query_type

    return query, query_type


@collect_stats("Controller.merge_reasons_to_insert")
def merge_reasons_to_insert(llm_planning, list_reason_to_insert: List[str], *args, **kwargs):
    return merge_reasons_to_insert_base(
        llm_planning, list_reason_to_insert, *args, **kwargs
    )


@collect_stats("Controller.define_retrieve_query")
def define_retrieve_query(llm_planning, initial_query: str,
                          existing_entities_and_relationships: str, wrong_query: str,
                          *args, **kwargs):
    return define_retrieve_query_base(
        llm_planning, initial_query, existing_entities_and_relationships, wrong_query, *args, **kwargs
    )


@collect_stats("Controller.define_forced_retrieve_queries")
def define_forced_retrieve_queries(llm_planning, initial_query: str,
                                   existing_entities_and_relationships: str,
                                   *args, **kwargs):
    # Define the output parser model
    class RetrieveQuery(BaseModel):
        query: str = Field(description="The new SPARQL query to retrieve data")

    prompt_template = PromptTemplate(
        input_variables=["initial_query",
                         "existing_entities_and_relationships"],
        template=DEFINE_FORCED_RETRIEVE_QUERY_TEMPLATE,
    )

    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                               "existing_entities_and_relationships": existing_entities_and_relationships})

    chain = llm_planning.with_structured_output(RetrieveQuery, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"New forced query:\n{pformat(response, width=160)}")

    return response.query


@collect_stats("Controller.define_write_query_given_new_information")
def define_sparql_query_given_new_information(llm_planning, initial_query: str,
                                              existing_entities_and_relationships: str,
                                              new_information: str, missing_information: str,
                                              *args, **kwargs):
    return define_sparql_query_given_new_information_base(
        llm_planning, initial_query, existing_entities_and_relationships, new_information, missing_information, *args, **kwargs
    )


@collect_stats("Controller.define_tool_calls")
def define_tool_calls(llm_execution, initial_query: str,
                      existing_entities_and_relationships: str, missing_information: str,
                      tool_calls_made: List[str],
                      *args, **kwargs):
    return define_tool_calls_base(
        llm_execution, initial_query, existing_entities_and_relationships, missing_information, tool_calls_made, *args, **kwargs
    )


@collect_stats("Controller.define_math_tool_call")
def define_math_tool_call(llm_execution, initial_query: str,
                      solution: str, *args, **kwargs):
    return define_math_tool_call_base(
        llm_execution, initial_query, solution, *args, **kwargs
    )


@collect_stats("Controller.define_need_for_math_before_parsing")
def define_need_for_math_before_parsing(llm_planning, initial_query: str, partial_solution: str,
                                    *args, **kwargs) -> bool:
    return define_need_for_math_before_parsing_base(
        llm_planning, initial_query, partial_solution, *args, **kwargs
    )


@collect_stats("Controller.generate_forced_solution")
def generate_forced_solution(llm_planning, initial_query: str,
                             existing_entities_and_relationships: str,
                             *args, **kwargs):
    # Define the output parser model
    class ForcedSolution(BaseModel):
        solution: str = Field(description="The solution to the initial problem")

    prompt_template = PromptTemplate(
        input_variables=["initial_query",
                         "existing_entities_and_relationships"],
        template=DEFINE_FORCED_SOLUTION_TEMPLATE,
    )

    completed_prompt = prompt_template.invoke({"initial_query": initial_query,
                                               "existing_entities_and_relationships": existing_entities_and_relationships})

    chain = llm_planning.with_structured_output(ForcedSolution, method="json_schema")
    response = invoke_with_retry(chain, completed_prompt)
    logger.info(f"New forced query:\n{pformat(response, width=160)}")

    return response.solution


@collect_stats("Controller.parse_solution_with_llm")
def parse_solution_with_llm(llm_planning, initial_query: str, partial_solution: str,
                            *args, **kwargs):
    return parse_solution_with_llm_base(
        llm_planning, initial_query, partial_solution, *args, **kwargs
    )


@collect_stats("Controller.define_final_solution")
def define_final_solution(llm_planning, initial_query: str, partial_solution: str,
                          array_solutions: List[str],
                          *args, **kwargs):
    return define_final_solution_base(
        llm_planning, initial_query, partial_solution, array_solutions, *args, **kwargs
    )


@collect_stats("Controller.fix_sparql")
def fix_sparql(llm_planning, sparql_query_to_fix: str, error_log: str, *args, **kwargs):
    return fix_sparql_base(
        llm_planning, sparql_query_to_fix, error_log, *args, **kwargs
    )
