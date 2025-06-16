# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Lorenzo Paleari

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Tuple

import httpx
import wikipedia
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from kgot.utils.llm_utils import get_llm, init_llm_utils
from kgot.utils.log_and_statistics import setup_logger
from kgot.utils.utils import ensure_file_path_exists


class ControllerInterface(ABC):
    """
    Abstract base class for all controllers.
    This class defines the interface for controllers that manage the execution of tasks
    and interactions with the LLM (Large Language Model).

    Attributes:
        max_iterations (int): The maximum number of iterations for task execution.
        logger (logging.Logger): The logger instance for logging messages.
        llm_planning (object): The LLM used for planning tasks.
        llm_execution (object): The LLM used for executing tasks.
        llm_math_executor (object): The LLM used for executing mathematical tasks.
        tool_call_results_cache (dict): Cache for storing results of tool calls.
        final_result (str): The final result of the task execution.
        num_next_steps_decision (int): Number of next steps to decide on.
        max_retrieve_query_retry (int): Maximum retries for retrieving queries.
        max_cypher_fixing_retry (int): Maximum retries for fixing Cypher queries.
        max_final_solution_parsing (int): Maximum retries for parsing final solutions.
    """

    def __init__(self,
                 llm_planning_model: str = "gpt-3.5-turbo",
                 llm_planning_temperature: float = None,
                 llm_execution_model: str = "gpt-3.5-turbo",
                 llm_execution_temperature: float = None,
                 max_iterations: int = 5,
                 logger_level: int = logging.INFO,
                 logger_file_name: str = "output.log",
                 logger_file_mode: str = "a",
                 config_llm_path: str = "kgot/config_llms.json",
                 num_next_steps_decision: int = 5,
                 max_retrieve_query_retry: int = 3,
                 max_cypher_fixing_retry: int = 3,
                 max_final_solution_parsing: int = 3,
                 max_tool_retries: int = 6,
                 max_llm_retries: int = 6,
                 gaia_formatter: bool = False,
                 *args,
                 **kwargs
                 ) -> None:
        """
        Initializes the ControllerInterface with the specified parameters.

        Args:
            llm_planning_model (str): The model used for planning tasks.
            llm_planning_temperature (float): The temperature parameter for the planning model.
            llm_execution_model (str): The model used for executing tasks.
            llm_execution_temperature (float): The temperature parameter for the execution model.
            max_iterations (int): The maximum number of iterations for task execution.
            logger_level (int): The logging level for the logger.
            logger_file_name (str): The name of the log file.
            logger_file_mode (str): The mode in which to open the log file.
            num_next_steps_decision (int): Number of next steps to decide on.
            max_retrieve_query_retry (int): Maximum retries for retrieving queries.
            max_cypher_fixing_retry (int): Maximum retries for fixing Cypher queries.
            max_final_solution_parsing (int): Maximum retries for parsing final solutions.
            max_tool_retries (int): Maximum retries for LLM invocations.
            max_llm_retries (int): Maximum retries for LLM invocations.
            gaia_formatter (bool): Whether to use the GAIA formatter.
        """
        print("LLM Planning Model: ", llm_planning_model)
        print("LLM Execution Model: ", llm_execution_model)

        if max_iterations < 1:
            raise ValueError("max_iterations must be greater than 0")
        self.max_iterations = max_iterations

        ensure_file_path_exists(logger_file_name)
        self.logger = setup_logger("Controller", level=logger_level,
                                   log_format="%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s",
                                   log_file=logger_file_name, log_file_mode=logger_file_mode, logger_propagate=False)
        
        init_llm_utils(config_llm_path, max_llm_retries)
        
        # Set up the LLMs
        self.llm_planning = get_llm(llm_planning_model, llm_planning_temperature)
        self.llm_execution = get_llm(llm_execution_model, llm_execution_temperature)
        self.llm_math_executor = get_llm(llm_execution_model, llm_execution_temperature)

        # Set up the other controller parameters
        self.tool_call_results_cache = {}  # Initialize cache for tool call results
        self.final_result: str = ""

        # Set up the parameters for the controller
        self.num_next_steps_decision = num_next_steps_decision
        self.max_retrieve_query_retry = max_retrieve_query_retry
        self.max_cypher_fixing_retry = max_cypher_fixing_retry
        self.max_final_solution_parsing = max_final_solution_parsing
        self.max_tool_retries = max_tool_retries

        self.gaia_formatter = gaia_formatter

        self.graph = None  # Placeholder for the graph database connection

    def run(self, problem: str, attachments_file_path: str, attachments_file_names: List[str], index: int = 0, snapshot_subdir: str = "", *args, **kwargs) -> Tuple[str, int]:
        """
        Run the controller with the given problem and attachments.
        This method is responsible for executing the main logic of the controller,
        including initializing the graph database, processing the problem, and
        returning the solution.

        Args:
            problem (str): The problem statement to be solved.
            attachments_file_path (str): The path to the attachments folder.
            attachments_file_names (List[str]): List of attachment file names.
            index (int): Index for the graph database initialization.
            snapshot_subdir (str): Subdirectory for storing snapshots.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[str, int]: A tuple containing the solution and the number of iterations taken.
        """
        self.logger.info("Starting execution")

        # Clean-up graph db before running the problem and create log folder
        snapshot_subdir = os.path.join(snapshot_subdir, datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        self.graph.init_db(index, snapshot_subdir)

        print(f"file_names: {attachments_file_names}")
        if (attachments_file_names is not None) and (len(attachments_file_names) > 0) and any(attachments_file_names):
            full_paths = []
            for file_name in attachments_file_names:
                if file_name == "":
                    continue

                full_paths.append(os.path.join(attachments_file_path, file_name))

            full_paths = "\n".join(full_paths)
            problem = problem + "\n<attached_file_paths>\n" + full_paths + "\n</attached_file_paths>"

        
        self.logger.info(f"Query: {problem}")
        print(f"Query: {problem}")

        solution, iterations_taken = self._iterative_next_step_logic(problem)
        print(f"Solution: {solution}")

        return solution, iterations_taken

    def _invoke_tool_with_retry(self, selected_tool, tool_args):
        self.logger.info(f"Invoking tool '{selected_tool.name}' with args: {tool_args}")
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self.max_tool_retries),
                wait=wait_random_exponential(min=1, max=60),
                reraise=True,
                retry=(
                    retry_if_exception_type(wikipedia.exceptions.WikipediaException) |
                    retry_if_exception_type(httpx.ReadTimeout) |
                    retry_if_exception_type(httpx.ConnectTimeout)
                )
            ):
                with attempt:
                    try:
                        try:
                            tool_output = selected_tool.invoke(input=tool_args)
                        except TypeError as e:
                            self.logger.info(f"Retrying using the unpacking of the arguments values. ERROR: {str(e)}")
                            tool_output = selected_tool.invoke(next(iter(tool_args.values())))
                    except wikipedia.exceptions.WikipediaException as e:
                        self.logger.error(f"Wikipedia Exception: {str(e)} - Retrying...")
                        raise
                    except httpx.ReadTimeout as e:
                        self.logger.error(f"Read Timeout Exception: {str(e)} - Retrying...")
                        raise
                    except httpx.ConnectTimeout as e:
                        self.logger.error(f"Connect Timeout Exception: {str(e)} - Retrying...")
                        raise
                    except Exception as e:
                        self.logger.error(f"Unknown error when invoking the tool: {str(e)} - Type of error: {type(e)}")
                        return "Tool invocation failed."
        except RetryError:
            return "Tool invocation failed after multiple retries."
        except Exception as e:
            self.logger.error(f"Error invoking tool: {str(e)}")
            return "Tool invocation failed after multiple retries"
        
        return tool_output
    
    @abstractmethod
    def _iterative_next_step_logic(self, problem: str, *args, **kwargs) -> Tuple[str, int]:
        """
        Abstract method to be implemented by subclasses.
        This method defines the iterative logic for processing the problem.

        Args:
            problem (str): The problem statement to be solved.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[str, int]: A tuple containing the solution and the number of iterations taken.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    @abstractmethod
    def _insert_logic(self, query: str, reason_to_insert: str, tool_calls_made: List[str], existing_entities_and_relationships: str, *args, **kwargs) -> str:
        """
        Abstract method to be implemented by subclasses.
        This method defines the logic for inserting data into the graph database.

        Args:
            query (str): The query to be executed.
            reason_to_insert (str): The reason for inserting the data.
            tool_calls_made (List[str]): List of tool calls made.
            existing_entities_and_relationships (str): Existing entities and relationships in the graph.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            str: The current state of the graph database.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    @abstractmethod
    def _retrieve_logic(self, query: str, existing_entities_and_relationships: str, current_iteration: int, solutions: List[str]) -> str:
        """
        Abstract method to be implemented by subclasses.
        This method defines the logic for retrieving data from the graph database.

        Args:
            query (str): The query to be executed.
            existing_entities_and_relationships (str): Existing entities and relationships in the graph.
            current_iteration (int): The current iteration number.
            solutions (List[str]): Solutions obtained from previous iterations.

        Returns:
            str: The solution obtained from the graph database.
        """
        raise NotImplementedError("Subclasses must implement this method.")
