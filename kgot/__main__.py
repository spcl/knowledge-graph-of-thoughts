# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari, Ales Kubicek, Andrea Jiang

import argparse
import importlib
import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv


class CustomFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    """Custom help formatter to align default values nicely."""

    def add_usage(self, usage, actions, groups, prefix=None):
        """Add a prefix to the usage message."""
        if prefix is None:
            prefix = 'Usage: '
        return super(CustomFormatter, self).add_usage(
            usage, actions, groups, prefix)
    
    def _get_help_string(self, action):
        """Add the default value to the option help message."""

        # The function is mostly hardcoded for the specific use case of this program
        help = action.help
        if help is None:
            help = ''

        if action.metavar == "\b":
            help = "\t" + help

        if "--help" in action.option_strings:
            help = help.replace("show", "Show") + "."

        if action.default != argparse.SUPPRESS:
            if action.default is not None:
                if any(x in ["--files", "--llm-exec", "--llm-exec-temp", "--llm-plan-temp"] for x in action.option_strings):
                    help += (f'\t(default: {action.default})')
                    return help
                help += (f'\t\t(default: {action.default})')

        return help


def load_variables() -> None:
    """Load environment variables from .env file."""

    load_dotenv(override=False)
    # User specific environment variables (place in .env file if possible)


# Command Implementations
def single_command(args: Any, neo4j_uri: str, neo4j_user: str, neo4j_password: str, python_executor_uri: str, rdf4j_read_uri: str, rdf4j_write_uri: str) -> None:
    """
    Run the 'single' command to solve a single problem given a statement and optional associated files.
    
    :param args: The parsed command line arguments.
    :param neo4j_uri: The URI to the Neo4j database.
    :param neo4j_user: The username to access the Neo4j database.
    :param neo4j_password: The password to access the Neo4j database.
    :param python_executor_uri: The URI to the Python execution server.
    :param rdf4j_read_uri: The URI for the RDF4J read access.
    :param rdf4j_write_uri: The URI for the RDF4J write access.
    """
    if(args.db_choice == "rdf4j" and args.controller_choice == "directRetrieve"):
        print("\033[1;31m\033[4mDirect retrieve with a RDF4J based database has not been implemented\033[0m")
        sys.exit(1)

    for file_path in args.files:
        if not os.path.isfile(file_path):
            print(f"\033[1;31m\033[4mFile '{file_path}' does not exist\033[0m")
            sys.exit(1)

    # Create stats file path if not provided
    stats_file = args.statistics_file if args.statistics_file else "llm_cost.json"
    
    # Import the Controller dynamically based on db_choice and controller_choice
    controller_object = importlib.import_module(f"kgot.controller.{args.db_choice}.{args.controller_choice}").Controller
    
    # Initialize the controller with named parameters
    controller = controller_object(
        neo4j_uri=neo4j_uri,
        neo4j_username=neo4j_user,
        neo4j_pwd=neo4j_password,
        python_executor_uri=python_executor_uri,
        rdf4j_read_uri=rdf4j_read_uri,
        rdf4j_write_uri=rdf4j_write_uri,
        llm_planning_model=args.llm_plan,
        llm_planning_temperature=args.llm_plan_temp,
        llm_execution_model=args.llm_exec,
        llm_execution_temperature=args.llm_exec_temp,
        max_iterations=args.iterations,
        logger_level=args.logger_level,
        logger_file_mode=args.logger_file_mode,
        statistics_file_name=stats_file,  # Add statistics file parameter
        db_choice=args.db_choice,
        controller_choice=args.controller_choice,
        tool_choice=args.tool_choice,
        gaia_formatter=args.gaia_formatter,
        config_llm_path=args.config_llm_path,
        max_retrieve_query_retry=args.max_retrieve_query_retry,
        max_cypher_fixing_retry=args.max_cypher_fixing_retry,
        max_final_solution_parsing=args.max_final_solution_parsing,
        max_tool_retries=args.max_tool_retries,
        max_llm_retries=args.max_llm_retries,
        num_next_steps_decision=args.num_next_steps_decision,
    )

    # Get the first file path (only the path excluding the file name)
    file_path = ""
    file_names = []

    if len(args.files) != 0:
        file_path += os.path.dirname(args.files[0])
        file_names.extend([os.path.basename(file) for file in args.files])
        print("file path:", file_path)
        print("file name:", file_names)

    # Set a default snapshots directory if None
    snapshot_dir = args.snapshots if args.snapshots is not None else ""
    controller.run(problem=args.problem, attachments_file_path=file_path, attachments_file_names=file_names, snapshot_subdir=snapshot_dir)


def main() -> None:
    """
    Main function to parse command line arguments and run the appropriate version.
    """
    load_variables()
    # Default environment variables for help message
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    python_executor_uri = os.getenv('PYTHON_EXECUTOR_URI', 'http://localhost:16000/run')
    rdf4j_read_uri = os.getenv('RDF4J_READ_URI', 'http://localhost:8080/rdf4j-server/repositories/kgot')
    rdf4j_write_uri = os.getenv('RDF4J_WRITE_URI', 'http://localhost:8080/rdf4j-server/repositories/kgot/statements')
    epilog_text = (
        "Environment Variables:\n"
        f"  NEO4J_URI             Neo4j database URI.\t\t(current: {neo4j_uri})\n"
        f"  NEO4J_USER            Neo4j database user.\t\t(current: {neo4j_user})\n"
        f"  NEO4J_PASSWORD        Neo4j database password.\t(current: {neo4j_password})\n"
        f"  PYTHON_EXECUTOR_URI   Python execution server URI.\t(current: {python_executor_uri})\n\n"
        f"  RDF4J_READ_URI        RDF4J read endpoint URI.\t(current: {rdf4j_read_uri})\n\n"
        f"  RDF4J_WRITE_URI       RDF4J write endpoint URI.\t(current: {rdf4j_write_uri})\n\n"
        "Note: You can set these variables in a .env file in the current directory.\n"
        "For more details, refer to the official documentation at:\n"
        "https://github.com/spcl/knowledge-graph-of-thoughts"
    )

    parser = argparse.ArgumentParser(
        prog="kgot",
        description="Integrates LLM reasoning with dynamically constructed knowledge graphs.",
        epilog=epilog_text
    )

    parser._optionals.title = "Options"

    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s 1.0', help="Show program's version number and exit.")
    parser.add_argument('-i', '--iterations', metavar='\b', type=int, default=7,
                            help="Maximum number of iterations to run.")
    parser.add_argument("-s", "--snapshots", metavar='\b', type=str,
                            help="Subfolder path to store snapshots.")

    parser.add_argument('--config_llm_path', metavar='\b', type=str, required=False, help='Path to LLM configuration file', default="kgot/config_llms.json")
    parser.add_argument('--logger_level', metavar='\b', type=int, required=False, help='Logging level', default=logging.INFO)
    parser.add_argument('--logger_file_mode', metavar='\b', type=str, required=False, help='Log file mode', default="a")
    parser.add_argument('--statistics_file', metavar='\b', type=str, required=False, help='Path to store LLM usage statistics', default="llm_cost.json")
    
    parser.add_argument("--num_next_steps_decision", metavar='\b', type=int, default=5,
                            help="Number of next steps decision.")
    parser.add_argument("--max_retrieve_query_retry", metavar='\b', type=int, default=3,
                            help="Maximum number of retries for retrieve query.")
    parser.add_argument("--max_cypher_fixing_retry", metavar='\b', type=int, default=3,
                            help="Maximum number of retries for Cypher fixing.")
    parser.add_argument("--max_final_solution_parsing", metavar='\b', type=int, default=3,
                            help="Maximum number of retries for final solution parsing.")
    parser.add_argument("--max_tool_retries", metavar='\b', type=int, default=6,
                            help="Maximum number of retries for tools.")
    parser.add_argument("--max_llm_retries", metavar='\b', type=int, default=6,
                            help="Maximum number of retries for LLM.")
    
    parser.add_argument("--llm-plan", metavar='\b', type=str, default="gpt-4o-mini",
                            help="LLM model used for the controller.")
    parser.add_argument("--llm-plan-temp", metavar='\b', type=float, default=0.0,
                            help="Temperature for the controller LLM model.")
    parser.add_argument("--llm-exec", metavar='\b', type=str, default="gpt-4o-mini",
                            help="LLM model used for tool execution calls.")
    parser.add_argument("--llm-exec-temp", metavar='\b', type=float, default=0.0,
                            help="Temperature for the tool execution LLM model.")
    
    parser.add_argument("--controller_choice", metavar='\b', type=str, default="queryRetrieve",
                            help="Controller choice for the agent.")
    parser.add_argument("--db_choice", metavar='\b', type=str, default="neo4j",
                            help="Database choice for the agent.")
    parser.add_argument("--tool_choice", metavar='\b', type=str, default="tools_v2_3",
                            help="Tool choice for the agent.")
    parser.add_argument("--gaia_formatter", action="store_true",
                            help="Use GAIA formatter instead of the default one. GAIA formatter is used to output GAIA benchmark compatible results, which consist in the final solution in a numeric, list or string format, no paragraph or other text.")

    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    single_parser = subparsers.add_parser(
        "single",
        description="Solve a single problem given a statement and optional associated files.",
        help="Solve a single problem.",
        formatter_class=CustomFormatter
    )
    single_parser.set_defaults(func=single_command)
    single_parser.add_argument("-p", "--problem", metavar="", type=str, help="The problem statement to solve.", required=True)
    single_parser.add_argument("--files", metavar="FILE", type=str, nargs="*", default=[],
                               help="List of file paths associated with the problem.")

    if len(sys.argv) == 1:
        print("\033[1;31m\033[4mNo arguments provided. At least one command is required.\033[0m\n\n")
        parser.print_help(sys.stderr)
    else:
        args = parser.parse_args()
        args.func(args, neo4j_uri, neo4j_user, neo4j_password, python_executor_uri, rdf4j_read_uri, rdf4j_write_uri)


if __name__ == "__main__":
    main()
