# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: You Wu
#
# Contributions: Lorenzo Paleari

from abc import abstractmethod
from typing import Any, Dict, List

import pandas as pd


class PlotOperation():
    """
    Abstract base class that defines the interface for all operations that plot data.
    """

    def __init__(self, result_dir_path: str, data_dir_path: str) -> None:
        """
        Initialize the operation.

        Args:
            result_dir_path (str): The directory path where results are stored.
            data_dir_path (str): The directory path where data files are stored.
        """
        self.result_dir_path = result_dir_path
        self.data_dir_path   = data_dir_path

    @abstractmethod
    def locate(self, dir_path: str) -> Dict[str, pd.DataFrame]:
        """
        Locate the data files in the specified directory.

        Args:
            dir_path (str): The directory path to search for data files.
        
        Returns:
            Dict[str, pd.DataFrame]: A dictionary where keys are file names and values are DataFrames.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    @abstractmethod
    def analyze(self, df_dict: dict, **kwargs) -> pd.DataFrame:
        """
        Analyze the data.

        Args:
            df_dict (dict): The data to analyze.
            **kwargs: Additional keyword arguments.

        Returns:
            pd.DataFrame: The result of the analysis.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    @abstractmethod
    def summarize(self, df_array: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Summarize the data.

        Args:
            df_array (List[pd.DataFrame]): The data to summarize.

        Returns:
            pd.DataFrame: The result of the summarization.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    @abstractmethod
    def execute(self, custom_inputs: Any = None) -> Any:
        """
        Plot the data.

        Args:
            custom_inputs (Any): Custom inputs for the plot operation.
        
        Returns:
            Any: The result of the plot operation.
        """
        raise NotImplementedError("Subclasses must implement this method.")