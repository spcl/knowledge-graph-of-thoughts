# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Andrea Jiang
#               Lorenzo Paleari
#               Ales Kubicek

import functools
import importlib
import json
import logging
from collections import defaultdict
from functools import wraps
from time import time
from typing import Callable

import pandas as pd
from langchain_community.callbacks import get_openai_callback

from kgot.knowledge_graph import KnowledgeGraphInterface


class UsageStatistics:
    """
    Class to track the tool usage statistics (duration, tokens, cost).
    """

    def __init__(self, file_name: str = "llm_cost.json"):
        """
        Initialize the usage statistics.
        
        Args:
            file_name (str): Name of the statistics file. Defaults to "llm_cost.json".
        """
        self.statistics_file_name = file_name
        self.stats_df = pd.DataFrame(
            columns=['FunctionName', 'StartTime', 'EndTime', 'Model', 'PromptTokens', 'CompletionTokens', 'Cost'])

    def log_statistic(self, function_name: str, start_time: float, end_time: float, model: str = None, prompt_tokens: int = None,
                      completion_tokens: int = None, cost: float = None):
        """
        Log a statistic entry.

        Args:
            function_name (str): Name of the function.
            start_time (float): Start time.
            end_time (float): End time.
            model (str): Model name.
            prompt_tokens (int): Number of prompt tokens.
            completion_tokens (int): Number of completion tokens.
            cost (float): Cost.
        """
        
        cost = ({
            'FunctionName': function_name,
            'StartTime': start_time,
            'EndTime': end_time,
            'Model': model,
            'PromptTokens': prompt_tokens,
            'CompletionTokens': completion_tokens,
            'Cost': cost
        })

        with open(self.statistics_file_name, 'a') as f:
            # Write the statistic entry to the file
            f.write(json.dumps(cost) + '\n')

    @staticmethod
    def calculate_total_cost(input_log_file: str = "llm_cost.json", output_log_file: str = "total_cost.json"):
        """
        Calculate the total cost from the usage statistics.

        Args:
            input_log_file (str): Path to the input JSON file. Defaults to "llm_cost.json".
            output_log_file (str): Path to the output JSON file. Defaults to "total_cost.json".
        """
        with open(input_log_file, 'r') as f:
            data = [json.loads(line) for line in f]

        # Initialize a defaultdict for aggregating totals by function name
        totals = defaultdict(lambda: {
            "TotalPromptTokens": 0,
            "TotalCompletionTokens": 0,
            "TotalCost": 0.0,
            "TotalDuration": 0.0
        })

        final_total = {
            "TotalPromptTokens": 0,
            "TotalCompletionTokens": 0,
            "TotalCost": 0.0,
            "TotalDuration": 0.0
        }

        # Iterate through each entry in the data
        for entry in data:
            function_name = entry["FunctionName"]
            totals[function_name]["TotalPromptTokens"] += entry["PromptTokens"]
            totals[function_name]["TotalCompletionTokens"] += entry["CompletionTokens"]
            totals[function_name]["TotalCost"] += entry["Cost"]
            totals[function_name]["TotalDuration"] += entry["EndTime"] - entry["StartTime"]

            final_total["TotalPromptTokens"] += entry["PromptTokens"]
            final_total["TotalCompletionTokens"] += entry["CompletionTokens"]
            final_total["TotalCost"] += entry["Cost"]
            final_total["TotalDuration"] += entry["EndTime"] - entry["StartTime"]

        # Convert totals to a regular dictionary for JSON serialization
        totals = {function_name: dict(totals_data) for function_name, totals_data in totals.items()}
        totals["FinalTotal"] = final_total

        # Write the totals to the output JSON file
        with open(output_log_file, 'w') as f:
            json.dump(totals, f, indent=4)

        print(f"Totals have been written to {output_log_file}")


class State:
    """
    Global class to store the state of the knowledge graph and usage statistics.
    """

    @classmethod
    @functools.cache
    def knowledge_graph(cls, db_choice: str, *args, **kwargs) -> KnowledgeGraphInterface:
        """
        Get the knowledge graph instance.
        
        Returns:
            KnowledgeGraph: The knowledge graph instance.
        """
        kg = importlib.import_module(f"kgot.knowledge_graph.{db_choice}").KnowledgeGraph
        return kg(*args, **kwargs)

    @classmethod
    @functools.cache
    def usage_statistics(cls, file_name) -> UsageStatistics:
        """
        Get the usage statistics instance.

        Args:
            file_name (str): Name of the statistics file.

        Returns:
            UsageStatistics: The usage statistics instance.
        """
        return UsageStatistics(file_name)
    

# Macro for statistics
def collect_stats(func_name=None) -> Callable:
    """Decorator for collecting LLM execution statistics, dynamically renaming the function."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get model name from first argument (assumed to be LLM object)
            possible_object = args[0]
            if isinstance(possible_object, object):
                llm = possible_object.llm if hasattr(possible_object, 'llm') else None
                usage_statistics = possible_object.usage_statistics if hasattr(possible_object, 'usage_statistics') else None

                if llm is not None:
                    model_name = llm.model_name if hasattr(llm, 'model_name') else llm.model if hasattr(llm, 'model') else 'unknown_model'
                else:
                    model_name = possible_object.model_name if hasattr(possible_object, 'model_name') else possible_object.model if hasattr(possible_object, 'model') else 'unknown_model'
            else:
                model_name = args[0] if isinstance(args[0], str) else 'unknown_model'
            
            if usage_statistics is None:
                usage_statistics = args[-1] if isinstance(args[-1], UsageStatistics) else kwargs.get('usage_statistics', None)
                if usage_statistics is None:
                    usage_statistics = State.usage_statistics(file_name='llm_cost.json')
            
            if not isinstance(model_name, str):
                model_name = model_name.model_name if hasattr(args[0], 'model_name') else model_name.model if hasattr(args[0], 'model') else 'unknown_model'

            with get_openai_callback() as cb:
                time_before = time()
                response = func(*args, **kwargs)  # Enforce the argument
                time_after = time()

                # Log statistics
                usage_statistics.log_statistic(
                    func_name,
                    time_before,
                    time_after,
                    model_name,
                    cb.prompt_tokens,
                    cb.completion_tokens,
                    round(cb.total_cost, 6)
                )
            return response
        return wrapper
    return decorator


# Set up a custom logger
def setup_logger(name: str, level: int = logging.INFO, log_file: str = None, log_file_mode: str = 'a',
                 log_format: str = None, logger_propagate: bool = True) -> logging.Logger:
    """
    Set up a custom logger with a file handler and a console handler.

    Args:
        name (str): Name of the logger.
        level (int): Logging level. Defaults to logging.INFO.
        log_file (str): Path to log file.
        log_file_mode (str): Mode to open the log file in. Defaults to 'a'.
        log_format (str): Log format.
        logger_propagate (bool): Whether the logger should propagate. Defaults to True.

    Returns:
        logging.Logger: The configured logger.
    """
    # Create a custom logger
    logger = logging.getLogger(name)

    # Set the logger
    logger.setLevel(level)
    logger.propagate = logger_propagate
    
    # Create a list of handlers
    handlers = []
    if log_file:
        # Add File Handler for the logger
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode=log_file_mode)
        handlers.append(file_handler)
    else:
        # Add Console handler
        console_handler = logging.StreamHandler()
        handlers.append(console_handler)

    # Create formatter and add it to the handlers
    if log_format:
        formatter = logging.Formatter(log_format)
        for handler in handlers:
            handler.setFormatter(formatter)

    # Add the handlers to the logger
    for handler in handlers:
        logger.addHandler(handler)

    return logger
