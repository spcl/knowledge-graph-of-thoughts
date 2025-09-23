# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Andrea Jiang
#               Lorenzo Paleari
#
# Contributions: Jón Gunnar Hannesson
#                Ales Kubicek

import importlib
import json
from typing import List, Tuple

from langchain_core.tools import BaseTool

from kgot.controller import ControllerInterface
from kgot.controller.neo4j.queryRetrieve.llm_invocation_handle import (
    define_cypher_query_given_new_information,
    define_final_solution,
    define_forced_retrieve_queries,
    define_math_tool_call,
    define_need_for_math_before_parsing,
    define_next_step,
    define_retrieve_query,
    define_tool_calls,
    fix_cypher,
    generate_forced_solution,
    merge_reasons_to_insert,
    parse_solution_with_llm,
)
from kgot.tools.PythonCodeTool import RunPythonCodeTool
from kgot.utils import State
from kgot.utils.utils import ensure_file_path_exists, is_empty_solution


class Controller(ControllerInterface):
    """
    Controller class for managing the interaction between the LLM and the Neo4j database.
    This class is responsible for executing tasks, retrieving information, and managing the state of the knowledge graph.

    The retrieve method is Cypher-based, meaning it uses Cypher queries to interact with the Neo4j database.

    Attributes:
        graph (State.knowledge_graph): The knowledge graph instance for interacting with the Neo4j database.
        usage_statistics (State.usage_statistics): The usage statistics instance for tracking usage.
        tool_manager (ToolManager): The tool manager instance for managing tools.
        tools (list[BaseTool]): The list of tools available for use.
        tool_names (dict): A dictionary mapping tool names to their corresponding tool instances.
        llm_execution (BaseTool): The LLM execution tool instance.
        llm_math_executor (BaseTool): The LLM math executor tool instance.
    
    For other attributes, see ControllerInterface.
    """

    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_pwd: str,
                 python_executor_uri: str,
                 llm_execution_model: str ,
                 llm_execution_temperature: float,
                 statistics_file_name: str,
                 db_choice: str = "neo4j",
                 tool_choice: str = "tools_v2_3",
                 *args, **kwargs) -> None:
        """
        Initializes the Controller with the specified parameters.
        Args:
            neo4j_uri (str): The URI of the Neo4j database.
            neo4j_username (str): The username for the Neo4j database.
            neo4j_pwd (str): The password for the Neo4j database.
            python_executor_uri (str): The URI of the Python tool executor.
            llm_execution_model (str): The model used for executing tasks.
            llm_execution_temperature (float): The temperature parameter for the execution model.
            statistics_file_name (str): The name of the file for storing usage statistics.
            db_choice (str): The choice of database to use.
            tool_choice (str): The choice of tool to use.
            *args: Additional arguments. See ControllerInterface for details.
            **kwargs: Additional keyword arguments. See ControllerInterface for details.
            """
        super().__init__(llm_execution_model=llm_execution_model, llm_execution_temperature=llm_execution_temperature, *args, **kwargs)

        ensure_file_path_exists(statistics_file_name)
        self.graph = State.knowledge_graph(db_choice, neo4j_uri, neo4j_username, neo4j_pwd)
        self.usage_statistics = State.usage_statistics(statistics_file_name)

        # Set up the tools
        tool_manager = importlib.import_module(f"kgot.tools.{tool_choice}").ToolManager
        self.tool_manager = tool_manager(self.usage_statistics, python_executor_uri=python_executor_uri)
        self.tools = self.tool_manager.get_tools()
        # Create a map between the tools and their names
        self.tool_names = {}
        for curr_tool in self.tools:
            self.tool_names[curr_tool.name.lower()] = curr_tool
            self.logger.info(f"Provided Tool: {curr_tool} {curr_tool.name} {curr_tool.args}")

        # Bind the LLM execution to the tools (it's the main difference with the LLM planning)
        if self.tools:
            self.llm_execution = self.llm_execution.bind_tools(self.tools, tool_choice="required")

        pythonTool = RunPythonCodeTool(try_to_fix=True,
                                                   times_to_fix=3,
                                                   model_name=llm_execution_model,
                                                   temperature=llm_execution_temperature,
                                                   python_executor_uri=python_executor_uri,
                                                   usage_statistics=self.usage_statistics)
        controller_python: list[BaseTool] = [pythonTool]
        
        self.llm_math_executor = self.llm_math_executor.bind_tools(controller_python, tool_choice="required")

    def _iterative_next_step_logic(self, problem: str, *args, **kwargs) -> Tuple[str, int]:
        solution: str = ""  # Final solution
        raw_solutions: List[str] = []
        existing_entities_and_relationships = ""
        tool_calls_made = []
        current_iteration = 0

        while current_iteration < self.max_iterations:
            retrieve_next_step = {
                "RETRIEVE": 0,
                "INSERT": 0,
                "RETRIEVE_CONTENT": [],
                "INSERT_CONTENT": []
            }
            reason_to_insert = ""
            query_type = ""
            retrieve_query = ""

            for i in range(self.num_next_steps_decision):
                retrieve_query, query_type = define_next_step(self.llm_planning, problem,
                                                              existing_entities_and_relationships, tool_calls_made,
                                                              self.usage_statistics)
                print(f"returned next step {query_type}, {retrieve_query}")
                try:
                    retrieve_next_step[query_type] += 1
                    retrieve_next_step[query_type + "_CONTENT"].append(retrieve_query)
                except KeyError:
                    self.logger.error(f"Unknown query type for next step: {query_type} at iteration {i}")

            if retrieve_next_step["RETRIEVE"] > retrieve_next_step["INSERT"]:
                raw_solutions.extend(
                    self._perform_retrieve_branch(problem, existing_entities_and_relationships,
                                                  retrieve_next_step["RETRIEVE_CONTENT"]))
                break

            reason_to_insert = retrieve_next_step["INSERT_CONTENT"][0] if retrieve_next_step["INSERT"] > 0 else ""
            if retrieve_next_step["INSERT"] > 1:
                reason_to_insert = merge_reasons_to_insert(self.llm_planning, retrieve_next_step["INSERT_CONTENT"],
                                                            self.usage_statistics)
            print(f"Reason to insert: {reason_to_insert}")

            existing_entities_and_relationships = self._insert_logic(problem, reason_to_insert, tool_calls_made,
                                   existing_entities_and_relationships)

            current_iteration += 1
            print(f"Current iteration: {current_iteration}")

        solution = self._retrieve_logic(problem, existing_entities_and_relationships, current_iteration, raw_solutions)

        return solution, current_iteration
          
    def _insert_logic(self, query: str, reason_to_insert: str, tool_calls_made: List[str], existing_entities_and_relationships: str, *args, **kwargs) -> str:
        tool_calls = define_tool_calls(self.llm_execution, query, existing_entities_and_relationships,
                                               reason_to_insert, tool_calls_made, self.usage_statistics)
        print(f"Tool_calls: {tool_calls}")

        tools_results = self._invoke_tools_after_llm_response(tool_calls)
        tool_calls_made.extend(tool_calls)
        for call, result in zip(tool_calls, tools_results):
            new_information = f"function '{call}' returned: '{result}'"

            new_information_cypher_queries = define_cypher_query_given_new_information(
                self.llm_planning,
                query,
                existing_entities_and_relationships,
                new_information,
                reason_to_insert,
                self.usage_statistics)

            for single_query in new_information_cypher_queries:
                write_response = self.graph.write_query(single_query)
                self.logger.info(f"Write query result: {write_response}")
                retry_i = 0
                while not write_response[
                    0] and retry_i < self.max_cypher_fixing_retry:  # Failed the insert query
                    retry_i += 1
                    self.logger.info(
                        f"Failed the write query. Retry number: {retry_i} out of {self.max_cypher_fixing_retry}")

                    self.logger.error(
                        f"Trying to fix error encountered when executing Cypher query: {single_query}\nError: {write_response[1]}")
                    single_query = fix_cypher(self.llm_planning, single_query, write_response[1],
                                                self.usage_statistics)
                    write_response = self.graph.write_query(single_query)
                    self.logger.info(f"Write query result after fixing: {write_response}")

            existing_entities_and_relationships = self.graph.get_current_graph_state()

            print(f"All nodes and relationships after {call}:\n {existing_entities_and_relationships}")
        
        return existing_entities_and_relationships

    def _retrieve_logic(self, query: str, existing_entities_and_relationships: str, current_iteration: int, solutions: List[str]) -> str:
        if current_iteration == self.max_iterations and len(solutions) == 0:
            self.logger.info("Maximum iterations reached without finding a solution. Forcing generation of retrieve queries.")
            print("Maximum iterations reached without finding a solution. Forcing generation of retrieve queries.")
            # Generate the forced retrieve queries
            retrieve_queries = []
            for i in range(self.num_next_steps_decision):
                retrieve_query = define_forced_retrieve_queries(self.llm_planning, query,
                                                                existing_entities_and_relationships,
                                                                self.usage_statistics)
                retrieve_queries.append(retrieve_query)
            if retrieve_queries:
                solutions.extend(
                    self._perform_retrieve_branch(query, existing_entities_and_relationships,
                                                  retrieve_queries))

        # Now, proceed to parse solutions if not empty and choose the best one
        if not is_empty_solution(solutions):
            array_parsed_solutions = []
            for sol in solutions:
                self.logger.info(f"Current partial solution for math need: {sol}")
                need_math = define_need_for_math_before_parsing(self.llm_planning, query, sol, self.usage_statistics)
                if need_math:
                    sol = self._get_math_response(query, sol)

                for i in range(self.max_final_solution_parsing):
                    array_parsed_solutions.append(
                        parse_solution_with_llm(self.llm_planning, query, sol, self.gaia_formatter, self.usage_statistics))
            # Check if all the parsed solutions are empty
            if all(not parsed_sol.strip() for parsed_sol in array_parsed_solutions if parsed_sol):
                self.logger.info("All parsed solutions are empty. Forcing generation of a solution.")
                print("All parsed solutions are empty. Forcing generation of a solution.")
                # Force generation of a solution
                forced_solution = generate_forced_solution(self.llm_planning, query, existing_entities_and_relationships, self.usage_statistics)
                solution = parse_solution_with_llm(self.llm_planning, query, forced_solution, self.gaia_formatter, self.usage_statistics)
            else:
                # We have a series of solutions, we need to choose the best one
                self.logger.info(f"Solution list for final solution choose: {str(solutions)} {str(array_parsed_solutions)}")
                solution = define_final_solution(self.llm_planning, query, str(solutions), array_parsed_solutions,
                                                 self.usage_statistics)
        else:
            # Returned empty retrieves, force generation of a (textual) solution
            self.logger.info("No solutions found after maximum iterations and forced additional retrieve attempts. Forcing generation of a solution.")
            print("No solutions found after maximum iterations and forced additional retrieve attempts. Forcing generation of a solution.")

            forced_solution = generate_forced_solution(self.llm_planning, query, existing_entities_and_relationships, self.usage_statistics)
            solution = parse_solution_with_llm(self.llm_planning, query, forced_solution, self.gaia_formatter, self.usage_statistics)

        return solution

    def _perform_retrieve_branch(self, query, existing_entities_and_relationships, retrieve_queries) -> List[str]:
        solution: str = ""  # Final solution
        solutions: List[str] = []  # List of solutions, in case we use multiple retrieves
        
        if isinstance(retrieve_queries, str):
            retrieve_queries = [retrieve_queries]

        for retrieve_query in retrieve_queries:
            # Attempt to retrieve using the initial retrieve query
            get_result = self.graph.get_query(
                retrieve_query)  # Returns a tuple (result, success_flag, exception, index_failed_query)
            self.logger.info(f"Retrieved result: {get_result}")

            # Retry the retrieve query if it fails
            retrieve_retry_i = 0
            while ((not get_result[1] or is_empty_solution(solution))
                   and retrieve_retry_i < self.max_retrieve_query_retry):
                retrieve_retry_i += 1
                self.logger.info(
                    f"Failed the retrieve query. Defining a new retrieve query. Retry number: {retrieve_retry_i} out of {self.max_retrieve_query_retry} of retrieve query retries")

                # Attempt to fix the retrieve query if retrieval fails
                # If the solution succeeded, but is empty, go to the next 'while' to generate a new query
                fix_retry_i = 0
                while not get_result[1] and not (get_result[1] and is_empty_solution(
                        solution)) and fix_retry_i < self.max_cypher_fixing_retry:
                    fix_retry_i += 1
                    self.logger.info(
                        f"Failed the retrieve query. Trying to fix the Cypher query. Retry number: {fix_retry_i} out of {self.max_cypher_fixing_retry} of Cypher query fixes")
                    self.logger.error(
                        f"Trying to fix error encountered when executing RETRIEVE Cypher query: {retrieve_query}\nError: {get_result[2]}")
                    retrieve_query = fix_cypher(self.llm_planning, retrieve_query, get_result[2],
                                                self.usage_statistics)

                    get_result = self.graph.get_query(retrieve_query)
                    self.logger.info(f"Retrieved result: {get_result}")

                # Create a new retrieve query if the fix failed and/or returned an empty solution
                solution = get_result[0]
                if not get_result[1] or is_empty_solution(solution):
                    self.logger.info("Generating a new RETRIEVE query as no answer from the previous attempts")
                    new_query = define_retrieve_query(self.llm_planning, query,
                                                      existing_entities_and_relationships,
                                                      retrieve_query, self.usage_statistics)
                    get_result = self.graph.get_query(new_query)
                    self.logger.info(f"Retrieved result after new generation: {get_result}")

            solutions.append(get_result[0])
        self.logger.info(f"Retrieved solutions: {solutions}")
        return solutions

    def _get_math_response(self, query, solution):
        python_tool_call = define_math_tool_call(self.llm_math_executor, query, solution, self.usage_statistics)
        math_solution = None
        math_solution = self._invoke_tools_after_llm_response(python_tool_call)

        self.logger.info(
            f"Retrieve solution parsing from Python math: {math_solution}")
        if len(math_solution) > 0 and math_solution[0] is not None:
            solution = f"{solution}\n In addition, this is the response given by Python after calculations. Use the numbers and the logic as you see fit. <python_math_solution>{math_solution}<\\python_math_solution>."

        return solution

    def _invoke_tools_after_llm_response(self, tool_calls):
        outputs = []

        # Iterate through each tool call and invoke the appropriate tool or answer using the cached answer
        for tool_call in tool_calls:
            self.logger.info(f"Current tool_call: {tool_call}")
            tool_name = tool_call['name'].lower()
            tool_args = tool_call['args']
            self.logger.info(f"Current tool_args: {tool_args}")

            # Create a cache key based on tool name and arguments
            tool_call_key = (tool_name, json.dumps(tool_args, sort_keys=True))

            # Check if result is in cache
            if tool_call_key in self.tool_call_results_cache:
                tool_output = self.tool_call_results_cache[tool_call_key]
                self.logger.info(f"Retrieved tool output from cache for tool '{tool_name}' with args: {tool_args}")
            else:
                selected_tool = self.tool_names.get(tool_name)
                if selected_tool:
                    tool_output = self._invoke_tool_with_retry(selected_tool, tool_args)

                    self.logger.info(f"Tool '{tool_name}' output: {tool_output}")

                    if not tool_name == 'extract_zip':
                        self.tool_call_results_cache[tool_call_key] = tool_output
                else:
                    self.logger.warning(f"Tool '{tool_name}' not found.")
                    tool_output = None

            outputs.append(tool_output)

        return outputs
