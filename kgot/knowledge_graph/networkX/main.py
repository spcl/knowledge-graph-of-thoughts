# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Diana Khimey

import json
import os
from copy import deepcopy
from typing import Tuple

import networkx as nx

from kgot.knowledge_graph.kg_interface import KnowledgeGraphInterface


class KnowledgeGraph(KnowledgeGraphInterface):
    """
    A class to manage a knowledge graph using NetworkX.

    Attributes:
        Graph (nx.DiGraph): The directed graph representing the knowledge graph.
        current_folder_name (str): The name of the current folder for storing snapshots.
        current_snapshot_id (int): The ID of the current snapshot.
    """

    def __init__(self) -> None:
        """
        Initialize the KnowledgeGraph class.
        """
        super().__init__(logger_name=f"Controller.{self.__class__.__name__}")

        self.current_folder_name = ""
        self.current_snapshot_id = 0
        
        self.G = nx.DiGraph()

    def _export_db(self) -> None:
        """
        Export the current state of the graph database to a JSON file.
        """
        export_file = f"nx_snapshot_{self.current_snapshot_id}.json"
        export_file_path = f"./kgot/knowledge_graph/_snapshots/{self.current_folder_name}/{export_file}"

        data = []

        nodes = {}
        for node, label in (self.G.nodes(data="label")):
            info = {}
            info['type'] = 'node'
            info['id'] = node
            info['labels'] = label
            node_props = {}
            for prop in self.G.nodes[node]:
                if prop != "label":
                    node_props[prop] = self.G.nodes[node][prop]
            info['properties'] = node_props
            data.append(info)
            nodes[node] = info

        for src, tgt, relation in (self.G.edges(data="relationship")):
            info = {}
            info['type'] = 'relationship'
            info['label'] = relation
            edge_props = {}
            for prop in self.G.edges[src, tgt]:
                if prop != "relationship":
                    edge_props[prop] = self.G.edges[src, tgt][prop]
            info['properties'] = edge_props
            info['start'] = nodes[src]
            info['end'] = nodes[tgt]
            data.append(info)

        with open(export_file_path, 'w+') as f:
            for line in data:
                json.dump(line, f)
                f.write('\n')

        self.logger.info(f"Exported all nx nodes to {export_file}")
        self.current_snapshot_id += 1
       
    def _create_folder(self, index: int, snapshot_subdir: str = "") -> None:
        """
        Create a folder to store the exported database.
        """
        folder_name = ""
        if snapshot_subdir != "":
            folder_name = f"{snapshot_subdir}/"
        folder_name += f"snapshot_{index}"
        self.current_folder_name = folder_name

        folder_dir = os.path.join("./containers/neo4j/snapshots", folder_name)
        if not os.path.exists(folder_dir):
            os.makedirs(folder_dir)

    def init_db(self, index: int = 0, snapshot_subdir: str = "", *args, **kwargs) -> None:
        """
        Initialise the current database by deleting all nodes
        It creates a folder to store the exported database.
        """
        # Clear the current graph
        self.G = nx.DiGraph()

        self._create_folder(index, snapshot_subdir)
        self.current_snapshot_id = 0

    def get_current_graph_state(self, *args, **kwargs) -> str:
        """
        Get the current state of the NetworkX graph. Nodes and relationships.

        Returns:
            str: The current state of the graph.
        """
        output = "This is the current state of the NetworkX Graph.\n"

        by_label = dict()
        for node, label in (self.G.nodes(data="label")):
            if label in by_label:
                by_label[label].append(node)
            else:
                by_label[label] = [node]

        output += "Existing Nodes:\n"
        for label in by_label:
            output += f"\tLabel: {label}\n \t\t["
            for node in by_label[label]:
                node_props = {}
                for prop in self.G.nodes[node]:
                    if prop != "label":
                        node_props[prop] = self.G.nodes[node][prop]
                output += f"{{id:{node}, properties:{node_props}}}, "
            output = output[:-2]
            output += "]\n"
        if not by_label:
            output += "\tNo nodes found\n"

        by_relation = dict()
        for src, tgt, relationship in (self.G.edges(data="relationship")):
            if relationship in by_relation:
                by_relation[relationship].append((src, tgt))
            else:
                by_relation[relationship] = [(src, tgt)]

        output += "Existing Relationships:\n"
        for relation in by_relation:
            output += f"\tLabel: {relation}\n \t\t["
            for src, tgt in by_relation[relation]:
                edge_props = {}
                for prop in self.G.edges[src, tgt]:
                    if prop != "relationship":
                        edge_props[prop] = self.G.edges[src, tgt][prop]
                output += f"{{source: {{id: {src}}}, target: {{id: {tgt}}}, properties: {edge_props}}}, "
            output = output[:-2]
            output += "]\n"
        if not by_relation:
            output += "\tNo relationships found\n"

        return output

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
        if query is None:
            return None, False, ValueError("Query to execute is None")

        result = None
        try:
            global_scope = {"nx": nx, "self": self}

            exec(f"""{query}""", global_scope)
            result = global_scope.get("result")
            print("global scope result: ", result)
        except Exception as e:
            print("issue executing LLM written networkX code. Error: ", e)
            return None, False, e
        if result is None:
            print("LLM written code executed, result variable was not set or is empty.")
            return None, False, NameError("variable 'result' is None, empty, or not defined. Result cannot equal a None type.")

        return result, True, None

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
        if query is None:
            return False, ValueError("Query to execute is None")
 
        graph_copy = deepcopy(self.G)
        try:
            local_scope = {"self": self}
            exec(query, {}, local_scope)

            self._export_db()
        except Exception as e:
            print("issue executing LLM written networkX code. Error: ", e)
            print("Reverting graph")
            self.G = graph_copy
            return False, e

        return True, None