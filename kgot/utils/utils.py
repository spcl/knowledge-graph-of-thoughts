# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Andrea Jiang 
#               Lorenzo Paleari

import os
from typing import Any


# Create the directories of a filepath if not existing already
def ensure_file_path_exists(logs_file: str) -> None:
    """
    Create the directories of a filepath if not existing already.

    Args:
        logs_file (str): Path to the file.
    """
    # Get the directory part of the logs_file path
    directory = os.path.dirname(logs_file)

    # Check if the directory exists
    if directory != '' and not os.path.exists(directory):
        # If the directory does not exist, create it
        os.makedirs(directory)


def is_empty_solution(solution: Any) -> bool:
    """
    Check if a solution is empty.

    Args:
        solution (Any): The solution to check.

    Returns:
        bool: True if the solution is empty, False otherwise.
    """
    # Check if the solution is empty
    if solution is None:
        return True
    
    # Check if the solution is a dictionary
    if isinstance(solution, dict):
        # Check if the dictionary is empty and if not, all its values are empty
        return not solution or all(is_empty_solution(value) for value in solution.values())
    
    # Check if the solution is a list
    if isinstance(solution, list):
        # Check if the list is empty and if not, all its elements are empty
        return not solution or all(is_empty_solution(element) for element in solution)
    
    # If the solution is not None, a dictionary, or a list, return False
    return False