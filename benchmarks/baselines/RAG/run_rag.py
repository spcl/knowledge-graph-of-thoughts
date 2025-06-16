# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Tao Zhang

#!/usr/bin/env python3
"""
Main entry point for RAG functions.
Provides easy access to key functionality from a single script.
"""

import argparse
import sys

from benchmarks.baselines.RAG.src.utils.simplified_utils import init_llm_utils


def main():
    parser = argparse.ArgumentParser(description="RAG System for Tool Call Logs and GAIA Benchmark")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Process logs command
    process_parser = subparsers.add_parser("process", help="Process log files to corpus")
    process_parser.add_argument("num_files", nargs="?", type=int, default=None, 
                              help="Number of files to process (optional)")
    
    # Encode corpus command
    encode_parser = subparsers.add_parser("encode", help="Encode corpus to vector store")
    encode_parser.add_argument("corpus_path", help="Path to corpus file")
    encode_parser.add_argument("--save_dir", default="vector_db", help="Directory to save vector store")
    
    # Vectorize corpus command (dedicated command to create vector DB)
    vectorize_parser = subparsers.add_parser("vectorize", help="Explicitly create vector database from corpus")
    vectorize_parser.add_argument("corpus_path", help="Path to corpus file")
    vectorize_parser.add_argument("--save_dir", default="vector_db", help="Directory to save vector store")
    vectorize_parser.add_argument("--force", action="store_true", help="Force recreation of vector DB even if it exists")
    
    # Query corpus command
    query_parser = subparsers.add_parser("query", help="Query the knowledge base")
    query_parser.add_argument("--corpus_path", help="Path to corpus file for direct query")
    query_parser.add_argument("--index_path", help="Path to saved FAISS index")
    query_parser.add_argument("--query", required=True, help="Query to run")
    query_parser.add_argument("--n_retrieved", type=int, default=3, help="Number of documents to retrieve")
    query_parser.add_argument("--save_dir", default="vector_db", help="Directory to save/load vector store")
    query_parser.add_argument("--no_vectorize", action="store_true", 
                            help="Don't create vector DB if it doesn't exist (will raise error)")
    
    init_llm_utils('src/utils/config_llms.json')
    args = parser.parse_args()
    
    if args.command == "process":
        from benchmarks.baselines.RAG.src.process_log import process_logs
        process_logs(args.num_files)
    
    elif args.command == "encode":
        from benchmarks.baselines.RAG.src.encode_corpus import encode_corpus
        encode_corpus(args.corpus_path, args.save_dir)
    
    elif args.command == "vectorize":
        from benchmarks.baselines.RAG.src.corpus_rag import create_vector_db
        create_vector_db(args.corpus_path, args.save_dir, args.force)
    
    elif args.command == "query":
        if args.corpus_path:
            from benchmarks.baselines.RAG.src.corpus_rag import query_corpus
            query_corpus(args.corpus_path, args.query, args.n_retrieved, args.save_dir, args.no_vectorize)
        elif args.index_path:
            from benchmarks.baselines.RAG.src.load_corpus_index import query_index
            query_index(args.index_path, args.query, args.n_retrieved)
        else:
            print("Error: Either --corpus_path or --index_path must be provided")
            return 1
    
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
