# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Jón Gunnar Hannesson
#              Lorenzo Paleari
#              Peiran Ma


import argparse
import ast
import csv
import json
import math
import os
import random
import shutil

import pandas
from dotenv import load_dotenv
from huggingface_hub import snapshot_download


def download_gaia_dataset(hf_token: str, target_dir: str, split: str):
    """Download a specific split of the GAIA dataset"""
    os.makedirs(target_dir, exist_ok=True)
    snapshot_download(
        repo_id="gaia-benchmark/GAIA",
        repo_type="dataset",
        allow_patterns=[f"2023/{split}/**"],
        local_dir=target_dir,
        token=hf_token,
    )


def download_simpleqa_dataset(target_dir: str):
    df = pandas.read_csv(
            "https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv"
        )
    # Save the DataFrame to a CSV file
    df.to_csv(os.path.join(target_dir, "simple_qa_test_set.csv"), index=False)


def load_jsonl_with_index(path: str):
    """Load a .jsonl file and return a list of dicts with row indices"""
    with open(path, "r", encoding="utf-8") as f:
        return [{"row_idx": i, "row": json.loads(line)} for i, line in enumerate(f)]


def save_json(data: object, path: str):
    """Write data as formatted JSON to a given path"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def split_by_level(rows: list):
    """Group rows by their 'Level' field."""
    grouped = {}
    for item in rows:
        level = item["row"].get("Level")
        key = f"level_{level}"
        grouped.setdefault(key, []).append(item)
    return grouped


def setup_question_json(input_dir: str, split: str, with_dummy: bool = False):
    """Convert and split metadata.jsonl into full, per-level, and optional dummy datasets"""
    metadata_path = os.path.join(input_dir, "metadata.jsonl")
    rows = load_jsonl_with_index(metadata_path)

    merged_dir = os.path.join("GAIA", split)
    os.makedirs(merged_dir, exist_ok=True)
    save_json({"rows": rows}, os.path.join(merged_dir, "merged_dataset.json"))

    subsets_dir = os.path.join("GAIA", f"{split}_subsets")
    os.makedirs(subsets_dir, exist_ok=True)

    for level, group in split_by_level(rows).items():
        save_json(group, os.path.join(subsets_dir, f"{level}.json"))

    if with_dummy:
        save_json({"rows": rows[:5]}, os.path.join(subsets_dir, "dummy.json"))


def convert_csv_to_gaia_json(csv_filepath, json_filepath):
    """
    Convert a specially formatted CSV file to the GAIA-expected JSON format.

    Args:
        csv_filepath (str): Input CSV file path.
        json_filepath (str): Output JSON file path.
    """
    output_data = {"rows": []}
    row_idx_counter = 0

    try:
        with open(csv_filepath, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            if not all(col in csv_reader.fieldnames for col in ['metadata', 'problem', 'answer']):
                print("Error: CSV file must contain 'metadata', 'problem', and 'answer' columns.")
                return

            for csv_row in csv_reader:
                problem = csv_row.get('problem', '')
                final_answer = csv_row.get('answer', '')
                metadata_str = csv_row.get('metadata', '{}')

                # Parse metadata string
                # ast.literal_eval is safer than eval, used to parse Python literals
                try:
                    annotator_metadata_from_csv = ast.literal_eval(metadata_str)
                    if not isinstance(annotator_metadata_from_csv, dict):
                        print(f"Warning: Metadata on row {row_idx_counter + 1} could not be parsed as dict, using raw string: '{metadata_str}'")
                        annotator_metadata_from_csv = {"raw_metadata": metadata_str}
                except (ValueError, SyntaxError, TypeError) as e:
                    print(f"Warning: Error parsing metadata on row {row_idx_counter + 1} ('{metadata_str}'): {e}. Using raw string.")
                    annotator_metadata_from_csv = {"raw_metadata": metadata_str}

                # Build Annotator Metadata, includes metadata from CSV, and provides GAIA-specific fields with default values
                annotator_metadata_final = {
                    "Number of steps": "N/A",   # Typically not available in SimpleQA
                    "Tools": "N/A",             # Typically not available in SimpleQA
                    "Number of tools": "N/A",   # Typically not available in SimpleQA
                }
                # Merge parsed metadata from CSV into the final metadata
                annotator_metadata_final.update(annotator_metadata_from_csv)

                # Build JSON row structure
                json_row_content = {
                    "Question": problem,
                    "Final answer": final_answer,
                    "file_name": None,  # SimpleQA usually doesn't associate directly with a single file
                    "Level": "N/A",     # SimpleQA usually doesn't define a clear level, so use "N/A"
                                        # Alternatively, you could map from metadata['topic'], but "N/A" is more generic
                    "Annotator Metadata": annotator_metadata_final
                }

                output_data["rows"].append({
                    "row_idx": row_idx_counter,
                    "row": json_row_content
                })
                row_idx_counter += 1

        with open(json_filepath, mode='w', encoding='utf-8') as json_file:
            json.dump(output_data, json_file, indent=4, ensure_ascii=False)

        print(f"Successfully converted '{csv_filepath}' to '{json_filepath}'")
        print(f"Processed {row_idx_counter} rows.")

    except FileNotFoundError:
        print(f"Error: Input file '{csv_filepath}' not found.")
    except Exception as e:
        print(f"An error occurred during processing: {e}")


def create_test_set_sampler(input_filename, output_filename, sample_percentage=0.1, random_seed=123456):
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Input file '{input_filename}' is not a valid JSON format.")
        return

    if 'rows' not in data or not isinstance(data['rows'], list):
        print(f"Error: Input file '{input_filename}' does not have the expected format, 'rows' list not found.")
        return

    all_items = data['rows']
    total_items = len(all_items)

    if total_items == 0:
        print("Warning: No data items found in the input file.")
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump({"rows": []}, f, ensure_ascii=False, indent=4)
        print(f"Empty test set file '{output_filename}' created.")
        return

    random.seed(random_seed)

    sample_size = math.ceil(total_items * sample_percentage)
    if sample_size == 0 and total_items > 0 and sample_percentage > 0:
        sample_size = 1
    sample_size = min(sample_size, total_items)

    print(f"Total items: {total_items}")
    print(f"Fixed random seed: {random_seed}")
    print(f"Sampling percentage: {sample_percentage*100:.2f}%")
    print(f"Number of items to be sampled for the test set: {sample_size}")

    sampled_items = random.sample(all_items, sample_size)

    test_set_data = {"rows": sampled_items}

    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(test_set_data, f, ensure_ascii=False, indent=4)
        print(f"Successfully created test set! {sample_size} items saved to '{output_filename}'.")
    except IOError:
        print(f"Error: Could not write to output file '{output_filename}'.")


def create_dummy_set_sampler(input_filename, output_filename):
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Input file '{input_filename}' is not a valid JSON format.")
        return

    if 'rows' not in data or not isinstance(data['rows'], list):
        print(f"Error: Input file '{input_filename}' does not have the expected format, 'rows' list not found.")
        return

    all_items = data['rows']
    total_items = len(all_items)

    if total_items == 0:
        print("Warning: No data items found in the input file.")
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump({"rows": []}, f, ensure_ascii=False, indent=4)
        print(f"Empty dummy set file '{output_filename}' created.")
        return

    dummy_items = all_items[:5]  # Take the first 5 items for the dummy set

    dummy_set_data = {"rows": dummy_items}

    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(dummy_set_data, f, ensure_ascii=False, indent=4)
        print(f"Successfully created dummy set! {len(dummy_items)} items saved to '{output_filename}'.")
    except IOError:
        print(f"Error: Could not write to output file '{output_filename}'.")


def get_env_token() -> str:
    load_dotenv()
    token = os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        raise EnvironmentError("HUGGINGFACE_TOKEN not found in .env file")
    return token


def parse_args():
    parser = argparse.ArgumentParser(description="Download and process benchmarks.")
    parser.add_argument(
        "--benchmark",
        type=str,
        choices=["all", "gaia", "simpleqa"],
        default="all",
        help="Which benchmark to download and process (default: all)"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["validation", "test"],
        default="validation",
        help="Which GAIA dataset split to download and process (validation or test, default: validation)"
    )
    parser.add_argument(
        "--dummy",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether to include a dummy subset (default: True)"
    )
    parser.add_argument(
        "--random_sample",
        type=int,
        default=10,
        help="Randomly sample a percentage of the SimpleQA dataset, 0 to disable (default: 10)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=123456,
        help="Random seed for sampling (default: 123456)"
    )

    return parser.parse_args()


def main():
    args = parse_args()
    hf_token = get_env_token()

    if args.benchmark == "all" or args.benchmark == "gaia":
        split = args.dataset

        base_dir = os.path.dirname(__file__)
        tmp_dir = os.path.join(base_dir, "tmp")
        data_dir = os.path.join(tmp_dir, "2023", split)
        attachments_dir = os.path.join(base_dir, "GAIA/attachments", split)
        python_container_attachments_dir = os.path.join(base_dir, "..", "..", "containers", "python", "files", "benchmarks", "datasets", "GAIA", "attachments", split)
    
        download_gaia_dataset(hf_token, tmp_dir, split)
        setup_question_json(data_dir, split, with_dummy=args.dummy)
        shutil.copytree(data_dir, attachments_dir, dirs_exist_ok=True)                      # Copy attachments to attachments directory 
        shutil.copytree(data_dir, python_container_attachments_dir, dirs_exist_ok=True)     # Copy attachments to python directory
        shutil.rmtree(tmp_dir)

        print(f"✅ Finished processing GAIA {split} dataset.")
    
    if args.benchmark == "all" or args.benchmark == "simpleqa":
        base_dir = os.path.dirname(__file__)
        tmp_dir = os.path.join(base_dir, "tmp")
        data_dir = os.path.join(tmp_dir, "SimpleQA")
        os.makedirs(data_dir, exist_ok=True)

        download_simpleqa_dataset(data_dir)
        convert_csv_to_gaia_json(
            os.path.join(data_dir, "simple_qa_test_set.csv"),
            os.path.join(data_dir, "formatted_simpleqa.json")
        )
        if args.random_sample > 0:
            create_test_set_sampler(
                os.path.join(data_dir, "formatted_simpleqa.json"),
                os.path.join(data_dir, f"test_set_{args.random_sample}_percent_seed{args.seed}.json"),
                sample_percentage=args.random_sample / 100,
                random_seed=args.seed
            )
        if args.dummy:
            create_dummy_set_sampler(
                os.path.join(data_dir, "formatted_simpleqa.json"),
                os.path.join(data_dir, "dummy.json")
            )
        shutil.copytree(data_dir, os.path.join(base_dir, "SimpleQA"), dirs_exist_ok=True)
        shutil.rmtree(tmp_dir)

        print("✅ Finished processing SimpleQA dataset.")


if __name__ == "__main__":
    main()
