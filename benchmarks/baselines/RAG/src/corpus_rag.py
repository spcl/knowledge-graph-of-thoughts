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
from pathlib import Path

import openai
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from benchmarks.baselines.RAG.src.utils import encode_corpus_file

# Load environment variables from a .env file (e.g., OpenAI API key)
load_dotenv()

# Set OpenAI credentials from .env
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.organization = os.getenv("OPENAI_ORG_ID")


def create_vector_db(corpus_path, save_dir="vector_db", force=False):
    """
    Explicitly create a vector database from a corpus file.
    
    Args:
        corpus_path (str): Path to the corpus file.
        save_dir (str): Directory to save the vector store.
        force (bool): Force recreation of vector DB even if it exists.
        
    Returns:
        FAISS: The created vector store.
    """
    # Set default save_dir if not provided
    if save_dir is None:
        save_dir = "vector_db"

    # Create save directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Determine the expected path for the FAISS index
    corpus_name = Path(corpus_path).name
    faiss_index_path = os.path.join(save_dir, f"{corpus_name}_faiss_index")
    
    # Check if the FAISS index already exists
    if os.path.exists(faiss_index_path) and not force:
        print(f"Vector database already exists at: {faiss_index_path}")
        print("Use --force to recreate the vector database")
        
        # Load and return the existing vector store
        start_time = time.time()
        embeddings = OpenAIEmbeddings()
        try:
            vector_store = FAISS.load_local(faiss_index_path, embeddings, allow_dangerous_deserialization=True)
            load_time = time.time() - start_time
            print(f"Loaded existing vector store in {load_time:.2f} seconds")
            return vector_store
        except Exception as e:
            print(f"Error loading existing vector store: {e}")
            print("Creating new vector store...")
    
    # Create a new vector store
    print(f"Creating vector database for: {corpus_path}")
    print(f"This will be saved to: {faiss_index_path}")
    
    start_time = time.time()
    vector_store = encode_corpus_file(corpus_path, save_dir=save_dir)
    encoding_time = time.time() - start_time
    print(f"Vector database created in {encoding_time:.2f} seconds")
    
    return vector_store


class CorpusRAG:
    """
    A class to handle the RAG process using pre-chunked corpus files.
    """

    def __init__(self, corpus_path, n_retrieved=3, save_dir=None, no_vectorize=False):
        """
        Initializes the CorpusRAG by encoding the corpus file and creating the retriever.

        Args:
            corpus_path (str): Path to the corpus file to encode.
            n_retrieved (int): Number of chunks to retrieve for each query (default: 3).
            save_dir (str): Directory to save intermediate results (default: None).
            no_vectorize (bool): Don't create vector DB if it doesn't exist.
        """
        print("\n--- Initializing Corpus RAG Retriever ---")
        self.time_records = {}
        
        # Set default save_dir if not provided
        if save_dir is None:
            save_dir = "vector_db"

        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Determine the expected path for the FAISS index
        corpus_name = Path(corpus_path).name
        faiss_index_path = os.path.join(save_dir, f"{corpus_name}_faiss_index")
        
        # Check if the FAISS index already exists
        if os.path.exists(faiss_index_path):
            print(f"Loading existing vector store from: {faiss_index_path}")
            start_time = time.time()
            embeddings = OpenAIEmbeddings()
            try:
                self.vector_store = FAISS.load_local(faiss_index_path, embeddings, allow_dangerous_deserialization=True)
                self.time_records['Loading'] = time.time() - start_time
                print(f"Loading Time: {self.time_records['Loading']:.2f} seconds")
            except Exception as e:
                print(f"Error loading existing vector store: {e}")
                if no_vectorize:
                    raise ValueError(f"Could not load vector store and no_vectorize=True: {e}")
                
                print("Creating new vector store...")
                start_time = time.time()
                self.vector_store = encode_corpus_file(corpus_path, save_dir=save_dir)
                self.time_records['Encoding'] = time.time() - start_time
                print(f"Encoding Time: {self.time_records['Encoding']:.2f} seconds")
        else:
            # Vector store doesn't exist
            if no_vectorize:
                raise ValueError(f"Vector store doesn't exist at {faiss_index_path} and no_vectorize=True")
                
            # Encode the corpus file into a vector store
            print(f"Creating new vector store for: {corpus_path}")
            start_time = time.time()
            self.vector_store = encode_corpus_file(corpus_path, save_dir=save_dir)
            self.time_records['Encoding'] = time.time() - start_time
            print(f"Encoding Time: {self.time_records['Encoding']:.2f} seconds")

        # Create a retriever from the vector store
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": n_retrieved})

    def run(self, query):
        """
        Retrieves relevant documents for the given query and displays them.

        Args:
            query (str): The query to retrieve documents for.

        Returns:
            list: The retrieved documents.
        """
        # Measure time for retrieval
        start_time = time.time()
        docs = self.retriever.get_relevant_documents(query)
        self.time_records['Retrieval'] = time.time() - start_time
        print(f"Retrieval Time: {self.time_records['Retrieval']:.2f} seconds")

        # Display the retrieved documents
        print(f"\nRetrieved {len(docs)} documents for query: '{query}'")
        for i, doc in enumerate(docs):
            print(f"\n--- Document {i+1} (Chunk {doc.metadata.get('chunk_num', 'N/A')}) ---")
            print(doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content)
            print(f"Metadata: {doc.metadata}")
        
        return docs

def query_corpus(corpus_path, query, n_retrieved=3, save_dir=None, no_vectorize=False):
    """
    Helper function to query a corpus directly, used by run_rag.py.
    
    Args:
        corpus_path (str): Path to the corpus file.
        query (str): The query to retrieve documents for.
        n_retrieved (int): Number of chunks to retrieve for each query.
        save_dir (str): Directory to save/load vector store.
        no_vectorize (bool): Don't create vector DB if it doesn't exist.
        
    Returns:
        list: The retrieved documents.
    """
    corpus_rag = CorpusRAG(
        corpus_path=corpus_path,
        n_retrieved=n_retrieved,
        save_dir=save_dir,
        no_vectorize=no_vectorize
    )
    return corpus_rag.run(query)

# Function to parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Encode a corpus file and test RAG retrieval.")
    parser.add_argument("--corpus_path", type=str, default="corpus/corpus_demo.txt",
                        help="Path to the corpus file to encode.")
    parser.add_argument("--n_retrieved", type=int, default=2,
                        help="Number of chunks to retrieve for each query (default: 2).")
    parser.add_argument("--query", type=str, default="Tell me about Mercedes Sosa",
                        help="Query to test the retriever.")
    parser.add_argument("--save_dir", type=str, default="vector_db",
                        help="Directory to save/load vector store (default: vector_db).")
    parser.add_argument("--no_vectorize", action="store_true",
                       help="Don't create vector DB if it doesn't exist.")
    parser.add_argument("--vectorize_only", action="store_true",
                       help="Only create the vector DB, don't query.")
    parser.add_argument("--force", action="store_true",
                       help="Force recreation of vector DB even if it exists.")
    
    return parser.parse_args()


# Main function
def main(args):
    if args.vectorize_only:
        # Just create the vector database
        create_vector_db(args.corpus_path, args.save_dir, args.force)
        return
    
    # Initialize the CorpusRAG
    corpus_rag = CorpusRAG(
        corpus_path=args.corpus_path,
        n_retrieved=args.n_retrieved,
        save_dir=args.save_dir,
        no_vectorize=args.no_vectorize
    )

    # Retrieve documents based on the query
    corpus_rag.run(args.query)


if __name__ == '__main__':
    # Call the main function with parsed arguments
    main(parse_args())
