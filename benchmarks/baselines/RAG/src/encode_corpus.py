# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Tao Zhang

import argparse
import os

from dotenv import load_dotenv

# Update the import to use the correct path
from benchmarks.baselines.RAG.src.utils import encode_corpus_file


def encode_corpus(corpus_file_path, save_dir="vector_db"):
    """
    Encode a corpus file into a vector store.
    
    Args:
        corpus_file_path: Path to the corpus file
        save_dir: Directory to save the vector store
    
    Returns:
        Path to the saved vector store directory
    """
    # Make sure the corpus file exists
    if not os.path.exists(corpus_file_path):
        print(f"Error: Corpus file {corpus_file_path} not found.")
        return None
    
    # Create absolute path for save directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_dir_path = os.path.join(project_root, save_dir)
    os.makedirs(save_dir_path, exist_ok=True)
    
    print(f"Encoding corpus file: {corpus_file_path}")
    print(f"Saving results to: {save_dir_path}")
    
    # Encode the corpus file
    vectorstore = encode_corpus_file(corpus_file_path, save_dir=save_dir_path)
    
    print(f"Successfully encoded {corpus_file_path} into a vector store")
    print(f"Vector store contains {len(vectorstore.docstore._dict.keys())} documents")
    
    # Return the path to the vector store directory
    corpus_name = os.path.basename(corpus_file_path)
    vector_store_path = os.path.join(save_dir_path, f"{corpus_name}_faiss_index")
    return vector_store_path

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Encode a corpus file into a vector store')
    parser.add_argument('corpus_file', help='Path to the corpus file (e.g., corpus_4.txt)')
    parser.add_argument('--save_dir', default='vector_db', help='Directory to save intermediate results')
    
    args = parser.parse_args()
    
    encode_corpus(args.corpus_file, args.save_dir)

if __name__ == "__main__":
    main() 