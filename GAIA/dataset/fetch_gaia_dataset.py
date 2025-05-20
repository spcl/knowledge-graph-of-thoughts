# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Jón Gunnar Hannesson

import argparse
import json
import os
import shutil

from dotenv import load_dotenv
from huggingface_hub import snapshot_download


def download_dataset(hf_token: str, target_dir: str, split: str):
    """Download a specific split of the GAIA dataset"""
    os.makedirs(target_dir, exist_ok=True)
    snapshot_download(
        repo_id="gaia-benchmark/GAIA",
        repo_type="dataset",
        allow_patterns=[f"2023/{split}/**"],
        local_dir=target_dir,
        token=hf_token,
    )


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

    merged_dir = os.path.join(".", split)
    os.makedirs(merged_dir, exist_ok=True)
    save_json({"rows": rows}, os.path.join(merged_dir, "merged_dataset.json"))

    subsets_dir = os.path.join(".", f"{split}_subsets")
    os.makedirs(subsets_dir, exist_ok=True)

    for level, group in split_by_level(rows).items():
        save_json(group, os.path.join(subsets_dir, f"{level}.json"))

    if with_dummy:
        save_json({"rows": rows[:5]}, os.path.join(subsets_dir, "dummy.json"))


def get_env_token() -> str:
    load_dotenv()
    token = os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        raise EnvironmentError("HUGGINGFACE_TOKEN not found in .env file")
    return token


def parse_args():
    parser = argparse.ArgumentParser(description="Download and process GAIA dataset split.")
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["validation", "test"],
        default="validation",
        help="Which dataset split to download and process (validation or test, default: validation)"
    )
    parser.add_argument(
        "--dummy",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether to include a dummy subset (default: True)"
    )

    return parser.parse_args()


def main():
    args = parse_args()
    split = args.dataset
    hf_token = get_env_token()

    base_dir = os.path.dirname(__file__)
    tmp_dir = os.path.join(base_dir, "tmp")
    data_dir = os.path.join(tmp_dir, "2023", split)
    attachments_dir = os.path.join(base_dir, "attachments", split)
    python_container_attachments_dir = os.path.join(base_dir, "..", "..", "containers", "python", "files", "GAIA", "dataset", "attachments", split)
    
    download_dataset(hf_token, tmp_dir, split)
    setup_question_json(data_dir, split, with_dummy=args.dummy)
    shutil.copytree(data_dir, attachments_dir, dirs_exist_ok=True)                      # Copy attachments to attachments directory 
    shutil.copytree(data_dir, python_container_attachments_dir, dirs_exist_ok=True)     # Copy attachments to python directory
    shutil.rmtree(tmp_dir)

    print(f"✅ Finished processing GAIA {split} dataset.")


if __name__ == "__main__":
    main()
