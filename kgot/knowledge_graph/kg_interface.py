# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Lorenzo Paleari

import logging
from abc import ABC, abstractmethod
from typing import List, Tuple


class KnowledgeGraphInterface(ABC):
    """
    Abstract class for KnowledgeGraph

    Attributes:
    logger (Logger): The logger for the class
    """

    def __init__(self, logger_name: str) -> None:
        self.logger = logging.getLogger(logger_name)

    @abstractmethod
    def init_db(self, snapshot_index: int = 0, snapshot_subdir: str = "", *args, **kwargs) -> None:
        """
        Initialize the database

        Args:
        snapshot_index (int): The index of the snapshot to be loaded
        snapshot_subdir (str): The subdirectory of the snapshot to be loaded
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_current_graph_state(self, *args, **kwargs) -> str:
        """
        Get the current DB state.
        Recommended using a graph database and returning all nodes and edges.

        Returns:
        str: The current DB state
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_query(self, query: str, *args, **kwargs) -> Tuple[str, bool, Exception]:
        """
        Extract data from the database.

        Args:
        query (str): The query to be executed

        Returns:
        Tuple[str, bool, Exception]: The result of the query
            - str: The result of the query
            - bool: True if the query was successful, False otherwise
            - Exception: The exception raised if the query was unsuccessful
        """
        raise NotImplementedError
    
    @abstractmethod
    def write_query(self, query: str, *args, **kwargs) -> Tuple[bool, Exception]:
        """
        Write data to the database.

        Args:
        query (str): The query to be executed

        Returns:
        Tuple[bool, Exception]: The result of the query
            - bool: True if the query was successful, False otherwise
            - Exception: The exception raised if the query was unsuccessful
        """
        raise NotImplementedError
    
    def get_queries(self, queries: List[str], *args, **kwargs) -> List[Tuple[str, bool, Exception]]:
        """
        Extract data from the database using get_query method.
        (Overload this method if you want to implement a more complex algorithm)

        Args:
        queries (List[str]): The queries to be executed

        Returns:
        List[Tuple[str, bool, Exception]]: The results of the queries
            - str: The result of the query
            - bool: True if the query was successful, False otherwise
            - Exception: The exception raised if the query was unsuccessful
        """
        results = []

        if isinstance(queries, str):
            queries = [queries]

        for query in queries:
            results.append(self.get_query(query, *args, **kwargs))

        return results
    
    def write_queries(self, queries: List[str], *args, **kwargs) -> List[Tuple[bool, Exception]]:
        """
        Write data to the database using write_query method.
        (Overload this method if you want to implement a more complex algorithm)

        Args:
        queries (List[str]): The queries to be executed

        Returns:
        List[Tuple[bool, Exception]]: The results of the queries
            - bool: True if the query was successful, False otherwise
            - Exception: The exception raised if the query was unsuccessful
        """
        results = []

        if isinstance(queries, str):
            queries = [queries]

        for query in queries:
            results.append(self.write_query(query, *args, **kwargs))

        return results
