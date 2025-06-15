# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Tao Zhang

import json
import logging
import os
import time
from typing import Any, Dict, Optional


# Simple utility to ensure file paths exist
def ensure_file_path_exists(file_path: str):
    """
    Check if the file's directory path exists, if not create it.
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

# Setup logger without kgot dependencies
def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_format: str = "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s",
    log_file: Optional[str] = None,
    log_file_mode: str = "a",
    logger_propagate: bool = True,
) -> logging.Logger:
    """
    Set up a logger with the given name and level, optionally logging to a file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = logger_propagate
    
    # Clear existing handlers
    for hdlr in logger.handlers[:]:  
        logger.removeHandler(hdlr)

    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if log_file is provided
    if log_file:
        ensure_file_path_exists(log_file)
        file_handler = logging.FileHandler(log_file, mode=log_file_mode)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Simple LLM configuration
_MODEL_CONFIGURATIONS = {}

def init_llm_utils(config_path: str = "llm_config.json"):
    """
    Initialize LLM configurations from a JSON file.
    """
    global _MODEL_CONFIGURATIONS
    try:
        with open(config_path, "r") as f:
            _MODEL_CONFIGURATIONS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load LLM config from {config_path}: {e}")
        _MODEL_CONFIGURATIONS = {}

def get_model_configurations(model_name: str) -> Dict[str, Any]:
    """
    Get the configuration for a given model.
    Falls back to a basic config if the model is not found in the config file.
    """
    if model_name in _MODEL_CONFIGURATIONS:
        config = _MODEL_CONFIGURATIONS[model_name].copy()
    else:
        # Default configuration
        config = {
            "model_family": "OpenAI",
            "model": model_name,
            "temperature": 0.0,
        }
    
    # Always use API keys from environment
    config["api_key"] = os.getenv("OPENAI_API_KEY")
    config["organization"] = os.getenv("OPENAI_ORG_ID")
    
    return config

# Simplified version of UsageStatistics
class UsageStatistics:
    def __init__(self, statistics_file_name: str = "llm_cost.json"):
        self.statistics_file_name = statistics_file_name
        ensure_file_path_exists(statistics_file_name)
        
        try:
            with open(statistics_file_name, "r") as f:
                self.statistics = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.statistics = []
    
    def log_statistic(self, function_name: str, time_before: float, time_after: float, 
                     model_name: str, prompt_tokens: int, completion_tokens: int, cost: float):
        """
        Log statistics about a function call.
        """
        statistic = {
            "function": function_name,
            "timestamp": time.time(),
            "execution_time": time_after - time_before,
            "model": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
        }
        self.statistics.append(statistic)
        
        # Write statistics to file
        with open(self.statistics_file_name, "w") as f:
            json.dump(self.statistics, f, indent=2)
    
    @staticmethod
    def calculate_total_cost(input_file: str, output_file: str):
        """
        Calculate the total cost of all calls in the statistics file.
        """
        try:
            with open(input_file, "r") as f:
                statistics = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            statistics = []
        
        if not statistics:
            print("No statistics available.")
            return
        
        # Calculate totals
        total_cost = sum(stat.get("cost", 0) for stat in statistics)
        total_prompt_tokens = sum(stat.get("prompt_tokens", 0) for stat in statistics)
        total_completion_tokens = sum(stat.get("completion_tokens", 0) for stat in statistics)
        total_tokens = total_prompt_tokens + total_completion_tokens
        
        # Group by model
        model_stats = {}
        for stat in statistics:
            model = stat.get("model", "unknown")
            if model not in model_stats:
                model_stats[model] = {
                    "cost": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                }
            model_stats[model]["cost"] += stat.get("cost", 0)
            model_stats[model]["prompt_tokens"] += stat.get("prompt_tokens", 0)
            model_stats[model]["completion_tokens"] += stat.get("completion_tokens", 0)
        
        # Create summary
        summary = {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "model_breakdown": model_stats,
        }
        
        # Write summary to file
        ensure_file_path_exists(output_file)
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"Total cost: ${total_cost:.4f}")
        print(f"Total tokens: {total_tokens} (Prompt: {total_prompt_tokens}, Completion: {total_completion_tokens})")
        for model, stats in model_stats.items():
            print(f"Model {model}: ${stats['cost']:.4f}, {stats['prompt_tokens'] + stats['completion_tokens']} tokens")
