# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari

import logging
import os
from typing import Any, List, Tuple

from neo4j import GraphDatabase
from neo4j.exceptions import (
    ClientError,
    CypherSyntaxError,
    CypherTypeError,
    ServiceUnavailable,
)

from kgot.knowledge_graph.kg_interface import KnowledgeGraphInterface


class KnowledgeGraph(KnowledgeGraphInterface):
    """
    A class to interact with a Neo4j graph database.

    Attributes:
        driver (GraphDatabase): The Neo4j driver.
        current_folder_name (str): The current folder name in which the database snapshots are stored.
        current_snapshot_id (int): The current snapshot id.
    """

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_pwd: str) -> None:
        """
        Initialize the KnowledgeGraph class.

        Args:
            neo4j_uri (str): The URI of the Neo4j instance.
            neo4j_user (str): The username of the Neo4j instance.
            neo4j_pwd (str): The password of the Neo4j instance.
        """
        super().__init__(logger_name=f"Controller.{self.__class__.__name__}")

        # Set the logging level of the Neo4j driver to INFO
        logging.getLogger('neo4j').setLevel(logging.INFO)
        logging.getLogger('neo4j.bolt').setLevel(logging.INFO)
        logging.getLogger('neo4j._pool').setLevel(logging.INFO)
        logging.getLogger('neo4j._util').setLevel(logging.INFO)
        logging.getLogger('neo4j._bolt_socket').setLevel(logging.INFO)

        # Try to connect to the database, log and raise an exception if it fails
        try:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pwd))
            self._test_connection()
        except ServiceUnavailable:
            print(
                "\n\n\033[1;31m" + "Failed to connect to Neo4j instance! Be sure to have a running Neo4j instance and double check the connection parameters.\n\n")
            exit(1)
        except Exception as e:
            print("\n\n\033[1;31m" + f"An error occurred while testing the connection to the Neo4j instance!: {e}\n\n")
            exit(1)

        # Create label with Id corresponding to current process id
        self.current_folder_name = ""
        self.current_snapshot_id = 0

    def _test_connection(self) -> None:
        """
        Test the connection to the Neo4j instance.
        """
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("RETURN 1")
        self.logger.info("Connection to Neo4j instance successful")

    def _export_db(self) -> None:
        """
        Export all nodes with a specific label to a JSON file using APOC.
        """
        export_file = f"snapshot_{self.current_snapshot_id}.json"  # Specify the export file name

        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                query = f"""
                    MATCH (n)
                    MATCH (k)-[r]->()
                    WITH collect(DISTINCT n) as a, collect(DISTINCT r) as b
                    CALL apoc.export.json.data(a, b, '/{self.current_folder_name}/{export_file}', {{}})
                    YIELD file, source, format, nodes, relationships, properties, time, rows, batchSize, batches, done, data
                    RETURN file, source, format, nodes, relationships, properties, time, rows, batchSize, batches, done, data
                """
                tx.run(query)

        self.logger.info(f"Exported all nodes to {export_file}")
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

    def _query_database(self, neo4j_query: str, params: Any = {}) -> List:
        """
        Query the Neo4j database without modifying it.

        Args:
            neo4j_query (str): The query to execute.
            params (Any): The parameters to pass to the query.

        Returns:
            List: The result of the query.
        """
        with self.driver.session() as session:
            result = session.run(neo4j_query, params)
            return result.data()

    def init_db(self, index: int = 0, snapshot_subdir: str = "", *args, **kwargs) -> None:
        """
        Initialise the current database by deleting all nodes
        It creates a folder to store the exported database.
        """
        # Delete all nodes
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run("MATCH (node) DETACH DELETE node")
        self.logger.info("Deleted all nodes")

        self._create_folder(index, snapshot_subdir)
        self.current_snapshot_id = 0

    def get_current_graph_state(self, *args, **kwargs) -> str:
        """
        Get the current state of the graph database. Nodes and relationships.

        Returns:
            str: The current state of the graph database.
        """
        # Get all nodes, with their labels, properties and ids
        nodes = self._query_database("""
            MATCH (n)
            WITH labels(n) AS labels, collect({properties: properties(n), id: elementId(n)}) AS nodes
            RETURN {labels: labels, nodes: nodes} AS groupedNodes
        """)
        nodes = nodes if nodes else []
        self.logger.info(f"Nodes: {nodes}")

        # Get all relationships, with their properties, source and target details
        rels = self._query_database("""
            MATCH (n)-[r]->(m)
            WITH type(r) as labels, collect({
                properties: properties(r),
                source: labels(n),
                target: labels(m),
                source_id: elementId(n),
                target_id: elementId(m)
            }) as rels
            RETURN {labels: labels, rels: rels} AS groupedRels
        """)
        rels = rels if rels else []
        self.logger.info(f"rels: {rels}")

        output = "This is the current state of the Neo4j database.\n"

        # Output nodes
        output += "Nodes:\n"
        for group in nodes:
            group = group['groupedNodes']
            label = (group['labels'] if group['labels'] else [''])[0]  # If there are no labels, set it to an empty string
            output += f"  Label: {label}\n"
            for node in group['nodes']:
                node_id = node['id']
                properties = node['properties']
                neo4j_id = node_id.split(":")[2]
                output += f"    {{neo4j_id:{neo4j_id}, properties:{properties}}}\n"
        if not nodes:
            output += "  No nodes found\n"

        # Output relationships
        output += "Relationships:\n"
        for group in rels:
            group = group['groupedRels']
            label = group['labels']
            output += f"  Label: {label}\n"
            for rel in group['rels']:
                # If label is None, set it to an empty string
                source_label = (rel['source'] if rel['source'] else [''])[0]
                source_id = rel['source_id']
                target_label = (rel['target'] if rel['target'] else [''])[0]
                target_id = rel['target_id']
                rel_properties = rel['properties']
                source_neo4j_id = source_id.split(":")[2]
                target_neo4j_id = target_id.split(":")[2]
                output += f"    {{source: {{neo4j_id: {source_neo4j_id}, label: {source_label}}}, target: {{neo4j_id: {target_neo4j_id}, label: {target_label}}}, properties: {rel_properties}}}\n"
        if not rels:
            output += "  No relationships found\n"

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

        try:
            result = self._query_database(query)
        except (ClientError, CypherSyntaxError, CypherTypeError) as e:
            return None, False, e
        except Exception as e:
            raise e

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

        try:
            with self.driver.session() as session:
                with session.begin_transaction() as tx:
                    tx.run(query)
            # Export the database after each query
            self._export_db()
        except (ClientError, CypherSyntaxError, CypherTypeError) as e:
            return False, e
        except Exception as e:
            raise e

        return True, None
