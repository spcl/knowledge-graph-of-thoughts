# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Tao Zhang

import argparse
import asyncio
import inspect
import json
import logging
import os

# Adjust imports for relative paths
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

import openai

# Add tiktoken for manual token counting
import tiktoken
from dotenv import load_dotenv
from langchain_community.callbacks import get_openai_callback
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Use our simplified scorer
# Use our simplified utilities
from benchmarks.baselines.RAG.src.utils.simplified_utils import (
    UsageStatistics,
    ensure_file_path_exists,
    get_model_configurations,
    init_llm_utils,
    setup_logger,
)
from benchmarks.scorers.gaia_scorer import check_close_call, question_scorer

# Load environment variables
load_dotenv()

# Set OpenAI credentials from environment
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.organization = os.getenv("OPENAI_ORG_ID")

# Similar to the system prompt in ZeroShot
system_prompt = """
You are a general AI assistant. I will ask you a question along with some relevant documents. Report your thoughts, and finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER].
YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.
If you are asked for a number, don't use comma to write your number neither use units such as $ or percent sign unless specified otherwise.
If you are asked for a string, don't use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.
If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string.
"""

def load_faiss_index(index_path: str):
    """
    Load a saved FAISS index.
    
    Args:
        index_path (str): Path to the saved FAISS index directory.
        
    Returns:
        FAISS: The loaded vector store.
    """
    print(f"Loading FAISS index from {index_path}...")
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    return vectorstore

class RAGBenchmark:
    """
    RAG-based execution model for answering queries in the GAIA benchmark.
    Now with async support for concurrent processing.
    
    Args:
        index_path (str): Path to the FAISS index directory.
        llm_model (str): The LLM model to use.
        llm_temperature (float): The temperature setting for the LLM.
        num_retrieved (int): Number of documents to retrieve.
        config_llm_path (str): Path to the LLM configuration file.
        logger_level (int): The logging level.
        logger_file_name (str): The name of the log file.
        logger_file_mode (str): The mode for the log file.
        statistics_file_name (str): The name of the statistics file.
        max_concurrent (int): Maximum number of concurrent queries.
    """
    def __init__(self,
                 index_path: str = "vector_db/corpus_2.txt_faiss_index",
                 llm_model: str = "gpt-4o-mini",
                 llm_temperature: float = None,
                 num_retrieved: int = 5,
                 config_llm_path: str = "llm_config.json",
                 logger_level: int = logging.INFO,
                 logger_file_name: str = "output.log",
                 logger_file_mode: str = "a",
                 statistics_file_name: str = "llm_cost.json",
                 max_concurrent: int = 5):
        
        # Initialize the vector store
        self.vectorstore = load_faiss_index(index_path)
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": num_retrieved})
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Initialize tokenizer for manual token counting
        self.tokenizer = tiktoken.encoding_for_model(llm_model)
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0
        
        # Set cost per token based on model
        self.cost_per_1k_input_tokens = 0.0005  # Default for gpt-4o-mini
        self.cost_per_1k_output_tokens = 0.0015  # Default for gpt-4o-mini
        if "gpt-4" in llm_model and "o" not in llm_model:
            self.cost_per_1k_input_tokens = 0.01  
            self.cost_per_1k_output_tokens = 0.03
        elif "gpt-4o" in llm_model and "mini" not in llm_model:
            self.cost_per_1k_input_tokens = 0.005
            self.cost_per_1k_output_tokens = 0.015
        
        # Initialize LLM
        init_llm_utils(config_llm_path)
        model_config = get_model_configurations(llm_model)
        
        if model_config["model_family"] == "OpenAI":
            self.llm = ChatOpenAI(
                model=model_config["model"],
                api_key=model_config["api_key"],
                max_tokens=model_config["max_tokens"] if "max_tokens" in model_config else None,
                organization=model_config["organization"],
                **{key: model_config[key] if llm_temperature is None else llm_temperature for key in 
                ["temperature"] if key in model_config},
                **{key: model_config[key] for key in 
                ["reasoning_effort"] if key in model_config},
            )
        
        # Setup logging and statistics tracking
        ensure_file_path_exists(logger_file_name)
        ensure_file_path_exists(statistics_file_name)
        
        self.logger = setup_logger("RAGBenchmark", level=logger_level,
                                 log_format="%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s",
                                 log_file=logger_file_name, log_file_mode=logger_file_mode, logger_propagate=False)
        
        self.usage_statistics = UsageStatistics(statistics_file_name)
        
        temperature_info = f"temperature '{self.llm.temperature}'" if "temperature" in model_config else ""
        reasoning_effort_info = f"reasoning_effort '{self.llm.reasoning_effort}'" if "reasoning_effort" in model_config else ""
        additional_info = f"{temperature_info} {reasoning_effort_info}".strip()
        
        self.logger.info(
            f"RAG Benchmark initialized with model '{model_config['model']}', {additional_info}, {num_retrieved} retrieved documents, and {max_concurrent} concurrent requests"
        )
        
        # Create thread pool for CPU-bound tasks
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
    
    async def _retrieve_documents(self, query: str):
        """
        Retrieve documents for a query using ThreadPoolExecutor to avoid blocking.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.retriever.get_relevant_documents, query)
    
    def answer_query_sync(self, query: str, file_path: str, file_names: List[str], *args, **kwargs) -> Tuple[str, int]:
        """
        Synchronous version of answer_query for backward compatibility.
        """
        return asyncio.run(self.answer_query(query, file_path, file_names, *args, **kwargs))
    
    async def answer_query(self, query: str, file_path: str, file_names: List[str], *args, **kwargs) -> Tuple[str, int]:
        """
        Process a query using RAG and return the answer asynchronously.
        
        Args:
            query (str): The question to answer.
            file_path (str): The path to attached documents (not used in RAG approach).
            file_names (List[str]): List of filenames (not used in RAG approach).
            
        Returns:
            Tuple[str, int]: The answer and number of iterations taken (always 1 for RAG).
        """
        async with self.semaphore:  # Limit concurrent operations
            self.logger.info(f"Processing query: {query}")
            
            try:
                with get_openai_callback() as cb:
                    time_before = time.time()
                    
                    # Retrieve documents for the query asynchronously
                    docs = await self._retrieve_documents(query)
                    
                    # Format the retrieved documents
                    retrieved_docs_text = ""
                    if docs:
                        wrapped_docs = ["<doc>\n{}\n</doc>".format(doc.page_content) for doc in docs]
                        retrieved_docs_text = "\n\n".join(wrapped_docs)
                    
                    # Create the final prompt with retrieved documents
                    final_query = query
                    if retrieved_docs_text:
                        final_query = query + "\n<retrieved_docs>\n" + retrieved_docs_text + "\n</retrieved_docs>"
                    
                    messages = [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": final_query
                        }
                    ]
                    
                    # Count tokens manually using tiktoken
                    prompt_tokens = 0
                    for message in messages:
                        prompt_tokens += len(self.tokenizer.encode(message["content"]))
                        # Add tokens for message formatting (~4 per message)
                        prompt_tokens += 4
                    
                    # Generate response - run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        self.executor, 
                        lambda: self.llm.invoke(messages)
                    )
                    
                    # Count completion tokens manually
                    completion_tokens = len(self.tokenizer.encode(response.content))
                    
                    # Calculate cost
                    cost = (prompt_tokens / 1000 * self.cost_per_1k_input_tokens) + \
                           (completion_tokens / 1000 * self.cost_per_1k_output_tokens)
                    
                    # Update totals
                    self.total_prompt_tokens += prompt_tokens
                    self.total_completion_tokens += completion_tokens
                    self.total_cost += cost
                    
                    time_after = time.time()
                    
                    # Print token usage for debugging
                    print(f"\nToken usage for query: {query[:50]}...")
                    print(f"  - Prompt tokens: {prompt_tokens}")
                    print(f"  - Completion tokens: {completion_tokens}")
                    print(f"  - Total tokens: {prompt_tokens + completion_tokens}")
                    print(f"  - Cost: ${cost:.6f}")
                    
                    # Log to statistics
                    self.usage_statistics.log_statistic(
                        inspect.currentframe().f_code.co_name,
                        time_before, time_after,
                        self.llm.name if hasattr(self.llm, 'name') and self.llm.name else self.llm.model_name if hasattr(self.llm, 'model_name') else "",
                        prompt_tokens, completion_tokens, round(cost, 6)
                    )
                    
                    # Extract final answer
                    final_answer_idx = response.content.find("FINAL ANSWER:")
                    if final_answer_idx == -1:
                        self.logger.error("No final answer found in the response.")
                        raise Exception("No final answer found in the response.")
                    
                    # Return the final answer
                    answer = response.content[final_answer_idx + len("FINAL ANSWER:"):].strip()
                    self.logger.info(f"Finished RAG. Final Result: {answer}")
                    
                    return answer, 1
                    
            except Exception as e:
                self.logger.error(f"Failed to execute RAG query: {e}")
                raise Exception(f"Failed to execute RAG query: {e}")

async def process_question(
    rag_benchmark,
    row,
    attachments_folder,
    log_folder_base,
    results_lock,
    correct_stats_json_file_path
):
    """Process a single question asynchronously and save results."""
    import traceback
    
    row_idx = row['row_idx']
    row_data = row['row']
    
    # Handle different case formats in the dataset - some may have 'Question', others 'question'
    if 'Question' in row_data:
        question = row_data['Question']
    elif 'question' in row_data:
        question = row_data['question']
    else:
        question = "No question found in the data"
        print(f"Warning: No question found for row {row_idx}. Available keys: {list(row_data.keys())}")
    
    # Handle different formats for the expected answer
    if 'Final answer' in row_data:
        final_answer = row_data['Final answer']
    elif 'final_answer' in row_data:
        final_answer = row_data['final_answer']
    elif 'Final Answer' in row_data:
        final_answer = row_data['Final Answer']
    else:
        final_answer = "No answer available"
        print(f"Warning: No answer found for row {row_idx}. Available keys: {list(row_data.keys())}")
    
    # Get metadata if available
    file_name = row_data.get('file_name', '')
    file_path = attachments_folder
    level = row_data.get('Level', row_data.get('level', 'Unknown'))
    
    # Get additional metadata if available
    metadata = row_data.get('Annotator Metadata', row_data.get('annotator_metadata', {}))
    num_steps = metadata.get('Number of steps', metadata.get('number_of_steps', ''))
    tools = metadata.get('Tools', metadata.get('tools', ''))
    num_tools = metadata.get('Number of tools', metadata.get('number_of_tools', ''))

    print(f"\nProcessing question {row_idx}...")
    
    try:
        # Store token usage before the query
        prompt_tokens_before = rag_benchmark.total_prompt_tokens
        completion_tokens_before = rag_benchmark.total_completion_tokens
        cost_before = rag_benchmark.total_cost
        
        returned_answer, iterations_taken = await rag_benchmark.answer_query(
            question,
            file_path,
            [file_name],
            row_idx, 
            log_folder_base
        )
        
        # Calculate token usage for this question
        prompt_tokens = rag_benchmark.total_prompt_tokens - prompt_tokens_before
        completion_tokens = rag_benchmark.total_completion_tokens - completion_tokens_before
        cost = rag_benchmark.total_cost - cost_before
        
    except Exception as e:
        returned_answer = f"error during execution, skipped. {e}\n{traceback.format_exc()}"
        iterations_taken = -1
        prompt_tokens = 0
        completion_tokens = 0
        cost = 0

    # Check if the returned answer matches the final answer
    successful = question_scorer(returned_answer, final_answer)
    close_call = check_close_call(returned_answer, final_answer, successful)
    
    if successful:
        print(f"Row {row_idx}: Correct (Expected: {final_answer}, Got: {returned_answer})", flush=True)
    elif close_call:
        print(f"Row {row_idx}: Close Call (Expected: {final_answer}, Got: {returned_answer})", flush=True)
    else:
        print(f"Row {row_idx}: Incorrect (Expected: {final_answer}, Got: {returned_answer})", flush=True)

    # Append the result to the results list
    result = {
        "question_number": row_idx,
        "question": question,
        "correct_answer": final_answer,
        "returned_answer": returned_answer,
        "successful": successful,
        "close_call": close_call,
        "level": level,
        "iterations_taken": iterations_taken,
        "num_steps": num_steps,
        "tools": tools,
        "num_tools": num_tools,
        "token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost": cost
        }
    }

    # Thread-safe update of results file
    async with results_lock:
        try:
            with open(correct_stats_json_file_path, 'r') as output_file:
                results = json.load(output_file)
        except FileNotFoundError:
            results = []
        
        results.append(result)
        
        with open(correct_stats_json_file_path, 'w') as output_file:
            json.dump(results, output_file, indent=4)
    
    return result

async def run_gaia_benchmark_async(
    rag_benchmark,
    gaia_data,
    already_solved,
    log_folder_base,
    correct_stats_json_file_path,
    attachments_folder,
    max_questions=None
):
    """Run the benchmark asynchronously."""
    
    # Clean and verify paths
    if os.path.exists(correct_stats_json_file_path):
        with open(correct_stats_json_file_path, "r") as f:
            correct_stats = json.load(f)
    else:
        correct_stats = []
    
    # Debug: Print structure information
    print("\nDEBUG: GAIA data structure:")
    if isinstance(gaia_data, dict):
        print(f"  - Type: dict with keys: {list(gaia_data.keys())}")
        if "rows" in gaia_data:
            print(f"  - 'rows' is a {type(gaia_data['rows'])} with {len(gaia_data['rows'])} items")
            if len(gaia_data['rows']) > 0:
                print(f"  - First row keys: {list(gaia_data['rows'][0].keys())}")
                if 'row' in gaia_data['rows'][0]:
                    print(f"  - First row['row'] keys: {list(gaia_data['rows'][0]['row'].keys())}")
    elif isinstance(gaia_data, list):
        print(f"  - Type: list with {len(gaia_data)} items")
        if len(gaia_data) > 0:
            print(f"  - First item keys: {list(gaia_data[0].keys())}")
    
    # Extract actual row data, handling nested structure
    if isinstance(gaia_data, dict) and "rows" in gaia_data:
        # The data is in format: {"rows": [{"row_idx": 0, "row": {...actual data...}}, ...]}
        # We need to get the actual data from "row"
        benchmark_data = []
        for i, item in enumerate(gaia_data["rows"]):
            if i in already_solved:
                continue
            if "row" in item:
                benchmark_data.append({"row_idx": i, "row": item["row"]})
            else:
                benchmark_data.append({"row_idx": i, "row": item})
            if max_questions is not None and max_questions > 0 and len(benchmark_data) >= max_questions:
                break
    
    # Debug: Print benchmark data structure
    if len(benchmark_data) > 0:
        print("\nDEBUG: Benchmark data structure:")
        print(f"  - First benchmark_data item keys: {list(benchmark_data[0].keys())}")
        if 'row' in benchmark_data[0]:
            print(f"  - First benchmark_data['row'] keys: {list(benchmark_data[0]['row'].keys())}")
    
    total_questions = len(benchmark_data)
    print(f"About to process {total_questions} questions.")
    
    results_lock = asyncio.Lock()
    tasks = []
    
    for row in benchmark_data:
        tasks.append(process_question(rag_benchmark, row, attachments_folder, log_folder_base, results_lock, correct_stats_json_file_path))
    
    await asyncio.gather(*tasks)
    
    # Calculate success statistics
    if os.path.exists(correct_stats_json_file_path):
        with open(correct_stats_json_file_path, "r") as f:
            correct_stats = json.load(f)
            
        total = len(correct_stats)
        if total > 0:
            success_count = sum(1 for item in correct_stats if item["successful"])
            close_call_count = sum(1 for item in correct_stats if item["close_call"])
            
            print(f"\n{'='*20} FINAL RESULTS {'='*20}")
            print(f"Total questions: {total}")
            print(f"Correct: {success_count} ({success_count/total*100:.2f}%)")
            print(f"Close calls: {close_call_count} ({close_call_count/total*100:.2f}%)")
            print(f"Combined correct+close: {(success_count+close_call_count)/total*100:.2f}%")
            
            # Group by difficulty level
            by_level = {}
            for item in correct_stats:
                level = item.get("level", "Unknown")
                if level not in by_level:
                    by_level[level] = {"total": 0, "success": 0, "close": 0}
                by_level[level]["total"] += 1
                if item.get("successful"):
                    by_level[level]["success"] += 1
                if item.get("close_call"):
                    by_level[level]["close"] += 1
            
            print("\nResults by difficulty level:")
            for level, stats in by_level.items():
                if stats["total"] > 0:
                    success_rate = stats["success"] / stats["total"] * 100
                    close_rate = stats["close"] / stats["total"] * 100
                    print(f"  {level}: {stats['success']}/{stats['total']} correct ({success_rate:.2f}%), {stats['close']} close calls ({close_rate:.2f}%)")
            
            # Add token and cost summary - use the RAGBenchmark's tracking
            print("\nToken Usage and Cost Summary:")
            print(f"  Total tokens: {rag_benchmark.total_prompt_tokens + rag_benchmark.total_completion_tokens:,}")
            print(f"  Prompt tokens: {rag_benchmark.total_prompt_tokens:,}")
            print(f"  Completion tokens: {rag_benchmark.total_completion_tokens:,}")
            print(f"  Total cost: ${rag_benchmark.total_cost:.4f}")
            print(f"  Average cost per question: ${rag_benchmark.total_cost/total:.4f}")
            
            # Generate a cost summary file - use the instance's tracking which is more reliable
            cost_summary = {
                "total_tokens": rag_benchmark.total_prompt_tokens + rag_benchmark.total_completion_tokens,
                "prompt_tokens": rag_benchmark.total_prompt_tokens,
                "completion_tokens": rag_benchmark.total_completion_tokens,
                "total_cost": rag_benchmark.total_cost,
                "cost_per_question": rag_benchmark.total_cost/total,
                "model": rag_benchmark.llm.model_name if hasattr(rag_benchmark.llm, 'model_name') else "unknown",
                "num_questions": total,
                "success_rate": success_count/total
            }
            
            cost_summary_file = os.path.join(os.path.dirname(correct_stats_json_file_path), "cost_summary.json")
            with open(cost_summary_file, "w") as f:
                json.dump(cost_summary, f, indent=2)
    
    return correct_stats

# Keep the original run_gaia_benchmark function for backwards compatibility
def run_gaia_benchmark(
        rag_benchmark,
        gaia_data,
        already_solved,
        log_folder_base,
        correct_stats_json_file_path,
        attachments_folder,
        max_questions=None
    ):
    """
    Run the GAIA benchmark using the RAG approach (synchronous version).
    This function is kept for backwards compatibility.
    For better performance, use the async version instead.
    """
    return asyncio.run(run_gaia_benchmark_async(
        rag_benchmark,
        gaia_data,
        already_solved,
        log_folder_base,
        correct_stats_json_file_path,
        attachments_folder,
        max_questions
    ))

async def main_async():
    parser = argparse.ArgumentParser(description='Run GAIA benchmark with RAG approach (async)')
    parser.add_argument('--index_path', type=str, default="vector_db/corpus_2.txt_faiss_index",
                        help='Path to the FAISS index')
    parser.add_argument('--log_folder_base', type=str, required=True,
                        help='Base folder for logging results')
    parser.add_argument('--gaia_file', type=str, default="merged_dataset.json",
                        help='Path to GAIA JSON file')
    parser.add_argument('--attachments_folder', type=str, default="attachments",
                        help='Path to GAIA problems attachments folder')
    parser.add_argument('--llm_model', type=str, default="gpt-4o-mini",
                        help='LLM model to use')
    parser.add_argument('--llm_temperature', type=float, default=0.0,
                        help='LLM temperature')
    parser.add_argument('--num_retrieved', type=int, default=5,
                        help='Number of documents to retrieve')
    parser.add_argument('--config_llm_path', type=str, default="llm_config.json",
                        help='Path to LLM configuration file')
    parser.add_argument('--max_questions', type=int, default=3,
                        help='Maximum number of questions to process (default: 3, use 0 for all)')
    parser.add_argument('--max_concurrent', type=int, default=5,
                        help='Maximum number of concurrent queries (default: 5)')
                        
    args = parser.parse_args()
    
    # Convert max_questions=0 to None (process all questions)
    max_questions = None if args.max_questions == 0 else args.max_questions
    
    # Create log directory
    log_folder = args.log_folder_base
    os.makedirs(log_folder, exist_ok=True)
    
    log_file = os.path.join(log_folder, "output.log")
    log_file_correct_stats = os.path.join(log_folder, "correct_stats.json")
    llm_cost_json_file = os.path.join(log_folder, "llm_cost.json")
    llm_cost_json_file_total = os.path.join(log_folder, "llm_cost_total.json")
    
    # Load GAIA data
    with open(args.gaia_file, 'r') as file:
        gaia_data = json.load(file)
    
    # Check for already solved questions
    already_solved = 0
    if os.path.exists(log_folder):
        try:
            with open(os.path.join(log_folder, "correct_stats.json"), 'r') as f:
                results = json.load(f)
                already_solved = len(results)
                if already_solved == len(gaia_data['rows']):
                    already_solved = 0
                    print("\033[4;32m\033[1mAll questions already solved. Skipping...\033[0m")
                    return
                
                print(f"\033[4;32m\033[1mAlready solved {already_solved} questions. Starting from {already_solved + 1}...\033[0m")
        except FileNotFoundError:
            pass
    
    # Initialize RAG benchmark
    rag = RAGBenchmark(
        index_path=args.index_path,
        llm_model=args.llm_model,
        llm_temperature=args.llm_temperature,
        num_retrieved=args.num_retrieved,
        config_llm_path=args.config_llm_path,
        logger_level=logging.INFO,
        logger_file_name=log_file,
        logger_file_mode="a",
        statistics_file_name=llm_cost_json_file,
        max_concurrent=args.max_concurrent
    )
    
    # Run the benchmark
    print("#####################################")
    print("##### Running Async RAG Benchmark ###")
    print("#####################################")
    print(f"Processing up to {max_questions if max_questions else 'all'} questions with {args.max_concurrent} concurrent tasks")
    
    await run_gaia_benchmark_async(
        rag,
        gaia_data,
        already_solved,
        log_folder,
        log_file_correct_stats,
        args.attachments_folder,
        max_questions
    )
    
    # Calculate total cost
    UsageStatistics.calculate_total_cost(llm_cost_json_file, llm_cost_json_file_total)

def main():
    parser = argparse.ArgumentParser(description='RAG GAIA Benchmark')
    
    # Required parameters
    parser.add_argument('--log_folder_base', type=str, required=True, help='Folder to store logs')
    
    # Optional parameters with defaults
    parser.add_argument('--gaia_file', type=str, default='../../../../datasets/GAIA/validation/merged_dataset.json', help='GAIA dataset file')
    parser.add_argument('--attachments_folder', type=str, default='../../../../datasets/GAIA/attachments/validation', help='Folder containing problem attachments')
    parser.add_argument('--index_path', type=str, default='vector_db/corpus_2.txt_faiss_index', help='Path to FAISS index for RAG')
    parser.add_argument('--llm_model', type=str, default='gpt-4o-mini', help='LLM model to use')
    parser.add_argument('--max_questions', type=int, default=3, help='Maximum number of questions to evaluate (0 for all)')
    parser.add_argument('--num_retrieved', type=int, default=5, help='Number of documents to retrieve for each question')
    parser.add_argument('--async_mode', action='store_true', help='Use async mode for faster processing')
    parser.add_argument('--max_concurrent', type=int, default=5, help='Maximum number of concurrent requests in async mode')
    
    args = parser.parse_args()
    
    # Setup paths
    run_id = int(time.time())
    log_folder = os.path.join(args.log_folder_base, f"{args.llm_model}_{run_id}")
    os.makedirs(log_folder, exist_ok=True)
    logger_file_name = os.path.join(log_folder, "output.log")
    statistics_file_name = os.path.join(log_folder, "llm_cost.json")
    correct_stats_json_file_path = os.path.join(log_folder, "correct_stats.json")
    
    # Initialize benchmark
    rag_benchmark = RAGBenchmark(
        index_path=args.index_path,
        llm_model=args.llm_model,
        num_retrieved=args.num_retrieved,
        logger_file_name=logger_file_name,
        statistics_file_name=statistics_file_name,
        max_concurrent=args.max_concurrent
    )
    
    # Load GAIA dataset
    with open(args.gaia_file, "r") as f:
        gaia_data = json.load(f)
    
    # Check for already solved problems
    already_solved = []
    if os.path.exists(correct_stats_json_file_path):
        with open(correct_stats_json_file_path, "r") as f:
            correct_stats = json.load(f)
            already_solved = [item.get("question_number") for item in correct_stats]
    
    # Run benchmark
    if args.async_mode:
        print("Running in async mode...")
        asyncio.run(run_gaia_benchmark_async(
            rag_benchmark, gaia_data, already_solved,
            log_folder, correct_stats_json_file_path, args.attachments_folder,
            args.max_questions
        ))
    else:
        print("Running in synchronous mode...")
        run_gaia_benchmark(
            rag_benchmark, gaia_data, already_solved,
            log_folder, correct_stats_json_file_path, args.attachments_folder,
            args.max_questions
        )
    
    # Generate a cost report at the end
    print("\nGenerating final cost report...")
    try:
        UsageStatistics.calculate_total_cost(
            statistics_file_name,
            os.path.join(log_folder, "cost_summary_detailed.json")
        )
    except Exception as e:
        print(f"Error generating detailed cost report: {e}")
    
    print(f"\nResults saved to {log_folder}")
    print(f"Detailed logs are in {logger_file_name}")
    print(f"Cost statistics are in {statistics_file_name}")

if __name__ == "__main__":
    main()
