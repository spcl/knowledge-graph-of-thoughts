# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Jón Gunnar Hannesson

import logging
import os
from typing import Tuple

from SPARQLWrapper import GET, JSON, POST, XML, SPARQLWrapper

from kgot.knowledge_graph.kg_interface import KnowledgeGraphInterface


class KnowledgeGraph(KnowledgeGraphInterface):
    """
    A class to interact with a SPARQL graph database.

    Attributes:
        sparql (SPARQLWrapper): The SPARQL endpoint interface.
    """

    def __init__(self, sparql_read_endpoint: str, sparql_write_endpoint: str) -> None:
        """
        Initialize the KnowledgeGraph class.

        Args:
            sparql_endpoint (str): The URI of the SPARQL endpoint.
        """
        super().__init__(logger_name=f"Controller.{self.__class__.__name__}")

        # Set the logging level of the SPARQL driver to INFO
        logging.getLogger('sparql').setLevel(logging.INFO)

        # Try to connect to the database, log and raise an exception if it fails
        try:
            self.sparql_reader = SPARQLWrapper(sparql_read_endpoint)
            self.sparql_reader.setReturnFormat(XML)
            self.sparql_reader.setMethod(GET)

            self.sparql_writer = SPARQLWrapper(sparql_write_endpoint)
            self.sparql_writer.setMethod(POST)
            self._test_connection()
        except ConnectionError:
            print(
                "\n\n\033[1;31m" + "Failed to connect to SPARQL database! Be sure to have a running SPARQL database and double check the connection parameters.\n\n")
            exit(1)
        except Exception as e:
            print("\n\n\033[1;31m" + f"An error occurred while testing the connection to the SPARQL instance!: {e}\n\n")
            exit(1)

        # Create label with Id corresponding to current process id
        self.current_folder_name = ""
        self.current_snapshot_id = 0

    def _test_connection(self) -> None:
        """
        Test the connection to the SPARQL endpoint by performing a simple ASK query.

        Raises:
            ConnectionError: If the endpoint is not reachable or does not respond correctly.
        """
        try:
            self.sparql_reader.setQuery("ASK { ?s ?p ?o }")
            self.sparql_reader.setReturnFormat(JSON)
            result = self.sparql_reader.queryAndConvert()
            if 'boolean' not in result:
                raise ConnectionError("Invalid response from SPARQL endpoint.")
            self.logger.info("Connection to SPARQL endpoint successful.")
        except Exception as e:
            self.logger.error(f"Failed to connect to SPARQL endpoint: {e}")
            raise ConnectionError(f"Failed to connect to SPARQL endpoint: {e}")

    def _export_db(self) -> None:
        """
        Export all nodes with a specific label to an XML file.
        """
        export_file = f"snapshot_{self.current_snapshot_id}.xml"  # Specify the export file name
        self.sparql_reader.setReturnFormat(XML)
        self.sparql_reader.setQuery("""
            CONSTRUCT {
                ?s ?p ?o .
            }
            WHERE {
                ?s ?p ?o .
            }
        """)

        results = self.sparql_reader.queryAndConvert()

        # Export to JSON
        with open(f'{self.current_folder_name}/{export_file}', "w", encoding="utf-8") as f:
            f.write(results.serialize())
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

        folder_dir = os.path.join("./kgot/knowledge_graph/_snapshots", folder_name)
        if not os.path.exists(folder_dir):
            os.makedirs(folder_dir)

    def init_db(self, index: int = 0, snapshot_subdir: str = "", *args, **kwargs) -> None:
        """
        Initialize the current database by deleting all nodes.
        Create a folder to store the exported database.
        """
        # Delete all nodes
        self.sparql_writer.setQuery("""
            DELETE WHERE {
                ?s ?p ?o .
            }
        """)

        self.sparql_writer.query()

        self.logger.info("Deleted all nodes")

        self._create_folder(index, snapshot_subdir)
        self.current_snapshot_id = 0
    
    def get_current_graph_state(self, *args, **kwargs) -> str:
        """
        Get the current state of the RDF graph database. Subjects, predicates, and objects.

        Returns:
            str: The current state of the graph database.
        """
        self.sparql_reader.setReturnFormat(XML)
        self.sparql_reader.setQuery("""
            CONSTRUCT {
                ?s ?p ?o .
            }
            WHERE {
                ?s ?p ?o .
            }
        """)
            
        try:
            results = self.sparql_reader.queryAndConvert()
        except Exception as e:
            self.logger.error(f"SPARQL query failed: {e}")
            return f"Error fetching graph state: {e}"

        output = "This is the current state of the RDF graph database:\n"
        output += results.serialize()
        return output
    
    def get_query(self, query: str, *args, **kwargs) -> Tuple[str, bool, Exception]:
        """
        Extract data from the SPARQL endpoint.

        Args:
            query (str): The SPARQL query to be executed.

        Returns:
            Tuple[str, bool, Exception]: The result of the query.
        """
        if not query:
            return None, False, ValueError("Query to execute is None")
        self.sparql_reader.setQuery(query)
        self.sparql_reader.setReturnFormat(XML)
        
        try:
            result = self.sparql_reader.query().convert()
        except Exception as e:
            return None, False, e

        return result.toxml(), True, None
    
    def write_query(self, query: str, *args, **kwargs) -> Tuple[bool, Exception]:
        """
        Write data to the RDF graph (e.g., INSERT or DELETE).

        Args:
            query (str): The SPARQL UPDATE query to be executed.

        Returns:
            Tuple[bool, Exception]: The result of the query.
        """
        if not query:
            return False, ValueError("Query to execute is None")

        self.sparql_writer.setQuery(query)

        try:
            self.sparql_writer.query()  # No convert() needed for UPDATE
            # self._export_db()    # Optional export
        except Exception as e:
            return False, e

        return True, None
