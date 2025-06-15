# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Tao Zhang

import argparse
import os
import time

import openai
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# Load environment variables
load_dotenv()

# Set OpenAI credentials from environment
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.organization = os.getenv("OPENAI_ORG_ID")

def load_faiss_index(index_path):
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

def query_index(index_path, query, n_retrieved=3):
    """
    Helper function to query a saved index directly, used by run_rag.py.
    
    Args:
        index_path (str): Path to the saved FAISS index directory.
        query (str): The query to retrieve documents for.
        n_retrieved (int): Number of chunks to retrieve for each query.
        
    Returns:
        list: The retrieved documents.
    """
    # Load the index
    start_time = time.time()
    vectorstore = load_faiss_index(index_path)
    load_time = time.time() - start_time
    print(f"Index loaded in {load_time:.2f} seconds")
    
    # Create retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": n_retrieved})
    
    # Test retrieval
    print(f"\nQuerying with: '{query}'")
    
    start_time = time.time()
    docs = retriever.get_relevant_documents(query)
    retrieval_time = time.time() - start_time
    print(f"Retrieval completed in {retrieval_time:.2f} seconds")
    
    # Display results
    print(f"\nRetrieved {len(docs)} documents")
    for i, doc in enumerate(docs):
        print(f"\n--- Document {i+1} (Chunk {doc.metadata.get('chunk_num', 'N/A')}) ---")
        print(doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content)
        print(f"Metadata: {doc.metadata}")
        
    return docs

def main(args):
    """
    Load a saved index and test retrieval.
    
    Args:
        args: Command line arguments.
    """
    # Use the query_index function
    query_index(args.index_path, args.query, args.n_retrieved)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load a saved FAISS index and test retrieval")
    parser.add_argument("--index_path", type=str, default="vector_db/corpus_demo.txt_faiss_index",
                        help="Path to the saved FAISS index directory")
    parser.add_argument("--query", type=str, default="What is the oldest Blu-Ray?",
                        help="Query to test retrieval")
    parser.add_argument("--n_retrieved", type=int, default=1,
                        help="Number of chunks to retrieve")
                        
    args = parser.parse_args()
    main(args)
