# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               You Wu

import argparse
import contextlib
import importlib
import json
import logging
import os
import traceback

from tqdm import tqdm

from benchmarks.scorers.simple_qa_scorer import ChatCompletionSampler, grade_answer
from kgot.utils import UsageStatistics


def check_answers(solver_function, simpleqa_data, already_solved, log_folder_base, correct_stats_json_file_path, attachments_folder):
    
    # Get api key from config_llms.json
    with open("kgot/config_llms.json", 'r') as f:
        config_llms = json.load(f)
    model = config_llms['gpt-4o']
    if 'api_key' in model:
        api_key = model['api_key']
    else:
        raise ValueError("API key not found in the configuration file.")
    grader = ChatCompletionSampler(model="gpt-4o", api_key=api_key)

    # Iterate over rows using tqdm with a dynamic description
    for row in tqdm(simpleqa_data['rows'][already_solved:], desc="Processing questions", unit="question"):
        row_idx = row['row_idx']

        question = row['row']['Question']
        final_answer = row['row']['Final answer']
        file_name = row['row']['file_name']
        file_path = attachments_folder  # row['row']['file_path'] not used as attachments have been downloaded locally
        level = row['row']['Level']
        num_steps = row['row']['Annotator Metadata'].get('Number of steps', '')
        tools = row['row']['Annotator Metadata'].get('Tools', '')
        num_tools = row['row']['Annotator Metadata'].get('Number of tools', '')

        # Process the question
        print(f"\n\n\nSolving question {row_idx}:")
        try:
            # the snapshot(s) will be saved in a subfolder with the same path as log_folder_base,
            #   but from kgot/knowledge_graph/_snapshots/
            returned_answer, iterations_taken = solver_function(question,
                                              file_path,
                                              [file_name],
                                              row_idx, log_folder_base)
        except Exception as e:
            # If modifying this error code, please modify also the plot_maker.py in benchmarks
            returned_answer = f"error during execution, skipped. {e}\n{traceback.format_exc()}"
            iterations_taken = -1

        # Check if the returned answer matches the final answer
        successful = grade_answer(question, final_answer, returned_answer, grader)
        if successful == "CORRECT":
            print(f"Row {row_idx}: Correct (Expected: {final_answer}, Got: {returned_answer})", flush=True)
        elif successful == "INCORRECT":
            print(f"Row {row_idx}: Incorrect (Expected: {final_answer}, Got: {returned_answer})", flush=True)
        elif successful == "NOT_ATTEMPTED":
            print(f"Row {row_idx}: Not attempted (Expected: {final_answer}, Got: {returned_answer})", flush=True)
        else:
            print(f"Row {row_idx}: UNKNOWN (Expected: {final_answer}, Got: {returned_answer})", flush=True)

        # Append the result to the results list
        result = {
            "question_number": row_idx,
            "correct_answer": final_answer,
            "returned_answer": returned_answer,
            "successful": successful == "CORRECT",
            "not_attempted": successful == "NOT_ATTEMPTED",
            "level": level,
            "iterations_taken": iterations_taken,
            "num_steps": num_steps,
            "tools": tools,
            "num_tools": num_tools,
        }

        # Read results and add the new result
        try:
            with open(correct_stats_json_file_path, 'r') as output_file:
                results = json.load(output_file)
        except FileNotFoundError:
            results = []
        results.append(result)

        # Write the updated results back to the file
        with open(correct_stats_json_file_path, 'w') as output_file:
            json.dump(results, output_file, indent=4)

    with open(correct_stats_json_file_path, 'r') as output_file:
        results = json.load(output_file)

    total_questions = len(results)
    correct_answers = sum(1 for result in results if result['successful'])

    if total_questions > 0:
        percentage_correct = (correct_answers / total_questions) * 100
        print(f"\nTotal questions: {total_questions}")
        print(f"Correct answers: {correct_answers}")
        print(f"Percentage correct: {percentage_correct:.2f}%")
    else:
        print("No questions to evaluate based on the provided filter.")


def main(
        log_folder_base,
        simpleqa_file,
        attachments_folder: str = "",
        config_llm_path: str = "kgot/config_llms.json",
        logger_level: int = logging.INFO,
        logger_file_mode: str = "a",
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_username: str = "neo4j",
        neo4j_password: str = "password",
        python_executor_uri: str = "http://localhost:16000/run",
        max_iterations: int = 7,
        num_next_steps_decision: int = 5,
        max_retrieve_query_retry: int = 3,
        max_cypher_fixing_retry: int = 3,
        max_final_solution_parsing: int = 3,
        max_tool_retries: int = 6,
        max_llm_retries: int = 6,
        llm_planning_model: str = "gpt-4o-mini",
        llm_planning_temperature: float = 0.0,
        llm_execution_model: str = "gpt-4o-mini",
        llm_execution_temperature: float = 0.0,
        controller_choice: str = "queryRetrieve",
        tool_choice: str = "tools_v2_3",
        db_choice: str = "neo4j",
        gaia_formatter: bool = True,
    ):

    with open(simpleqa_file, 'r') as file:
        simpleqa_data = json.load(file)

    already_solved = 0
    if os.path.exists(log_folder_base):
        try:
            with open(os.path.join(log_folder_base, "correct_stats.json"), 'r') as f:
                results = json.load(f)
                already_solved = len(results)
                if already_solved == len(simpleqa_data['rows']):
                    already_solved = 0
                    print("\033[4;32m\033[1mAll questions already solved. Skipping...\033[0m")
                    exit(0)

                print(f"\033[4;32m\033[1mAlready solved {already_solved} questions. Starting from {already_solved + 1}...\033[0m")
        except FileNotFoundError:
            pass

    log_folder = log_folder_base
    os.makedirs(log_folder, exist_ok=True)

    cmd_log = os.path.join(log_folder, "cmd_log.log")
    log_file = os.path.join(log_folder, "output.log")
    log_file_correct_stats = os.path.join(log_folder, "correct_stats.json")
    llm_cost_json_file = os.path.join(log_folder, "llm_cost.json")
    llm_cost_json_file_total = os.path.join(log_folder, "llm_cost_total.json")

    with open(cmd_log, 'a') as redirected_stdout:
        with contextlib.redirect_stdout(redirected_stdout):  # redirect stdout to log file
            print("#####################################")
            print("############# Doing KGoT ############")
            print("#####################################")

            controller_object = importlib.import_module(f"kgot.controller.{db_choice}.{controller_choice}").Controller
            controller = controller_object(
                neo4j_uri=neo4j_uri,
                neo4j_username=neo4j_username,
                neo4j_pwd= neo4j_password,
                python_executor_uri=python_executor_uri,
                llm_planning_model=llm_planning_model,
                llm_planning_temperature=llm_planning_temperature,
                llm_execution_model=llm_execution_model,
                llm_execution_temperature=llm_execution_temperature,
                max_iterations=max_iterations,
                logger_level=logger_level,
                logger_file_name=log_file,
                logger_file_mode=logger_file_mode,
                statistics_file_name=llm_cost_json_file,
                db_choice=db_choice,
                controller_choice=controller_choice,
                tool_choice=tool_choice,
                gaia_formatter=gaia_formatter,
                config_llm_path=config_llm_path,
                max_retrieve_query_retry=max_retrieve_query_retry,
                max_cypher_fixing_retry=max_cypher_fixing_retry,
                max_final_solution_parsing=max_final_solution_parsing,
                max_tool_retries=max_tool_retries,
                max_llm_retries=max_llm_retries,
                num_next_steps_decision=num_next_steps_decision,
            )
            check_answers(controller.run, simpleqa_data, already_solved, log_folder_base, log_file_correct_stats, attachments_folder)
            UsageStatistics.calculate_total_cost(llm_cost_json_file, llm_cost_json_file_total)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run SimpleQA processing with customized paths.')
    parser.add_argument('--log_folder_base', type=str, required=True, help='Base folder for logging results')
    parser.add_argument('--file', type=str, required=True, help='Path to SimpleQA JSON file')
    parser.add_argument('--attachment_folder', type=str, required=False, help='Path to SimpleQA problems attachments folder', default="")

    parser.add_argument('--config_llm_path', type=str, required=False, help='Path to LLM configuration file', default="kgot/config_llms.json")
    parser.add_argument('--logger_level', type=int, required=False, help='Logging level', default=logging.INFO)
    parser.add_argument('--logger_file_mode', type=str, required=False, help='Log file mode', default="a")
    
    parser.add_argument('--neo4j_uri', type=str, required=False, help='URI for Neo4j', default="bolt://localhost:7687")
    parser.add_argument('--neo4j_username', type=str, required=False, help='Neo4j username', default="neo4j")
    parser.add_argument('--neo4j_password', type=str, required=False, help='Neo4j password', default="password")
    parser.add_argument('--python_executor_uri', type=str, required=False, help='URI for Python tool executor', default="http://localhost:16000/run")

    parser.add_argument('--max_iterations', type=int, required=False, help='Max iterations for KGoT', default=7)
    parser.add_argument('--num_next_steps_decision', type=int, required=False, help='Number of next steps decision', default=5)
    parser.add_argument('--max_retrieve_query_retry', type=int, required=False, help='Max retries for retrieve query',  default=3)
    parser.add_argument('--max_cypher_fixing_retry', type=int, required=False, help='Max retries for Cypher fixing', default=3)
    parser.add_argument('--max_final_solution_parsing', type=int, required=False, help='Max retries for final solution parsing', default=3)
    parser.add_argument('--max_tool_retries', type=int, required=False, help='Max retries for tools', default=6)
    parser.add_argument('--max_llm_retries', type=int, required=False, help='Max retries for LLM', default=6)

    parser.add_argument('--llm_planning_model', type=str, required=False, help='LLM planning model', default="gpt-4o-mini")
    parser.add_argument('--llm_planning_temperature', type=float, required=False, help='LLM planning temperature', default=0.0)
    parser.add_argument('--llm_execution_model', type=str, required=False, help='LLM execution model', default="gpt-4o-mini")
    parser.add_argument('--llm_execution_temperature', type=float, required=False, help='LLM execution temperature', default=0.0)

    parser.add_argument('--controller_choice', type=str, required=False, help='Controller choice', default="queryRetrieve")
    parser.add_argument('--db_choice', type=str, required=False, help='Database choice', default="neo4j")
    parser.add_argument('--tool_choice', type=str, required=False, help='Tool choice', default="tools_v2_3")

    parser.add_argument('--gaia_formatter', action='store_true', help='Use GAIA formatter', default="Enabled")

    args = parser.parse_args()

    main(
        log_folder_base=args.log_folder_base,
        simpleqa_file=args.file,
        attachments_folder=args.attachment_folder,
        config_llm_path=args.config_llm_path,
        logger_level=args.logger_level,
        logger_file_mode=args.logger_file_mode,
        neo4j_uri=args.neo4j_uri,
        neo4j_username=args.neo4j_username,
        neo4j_password=args.neo4j_password,
        python_executor_uri=args.python_executor_uri,
        max_iterations=args.max_iterations,
        num_next_steps_decision=args.num_next_steps_decision,
        max_retrieve_query_retry=args.max_retrieve_query_retry,
        max_cypher_fixing_retry=args.max_cypher_fixing_retry,
        max_final_solution_parsing=args.max_final_solution_parsing,
        max_tool_retries=args.max_tool_retries,
        max_llm_retries=args.max_llm_retries,
        llm_planning_model=args.llm_planning_model,
        llm_planning_temperature=args.llm_planning_temperature,
        llm_execution_model=args.llm_execution_model,
        llm_execution_temperature=args.llm_execution_temperature,
        controller_choice=args.controller_choice,
        db_choice=args.db_choice,
        tool_choice=args.tool_choice,
        gaia_formatter=args.gaia_formatter,
    )