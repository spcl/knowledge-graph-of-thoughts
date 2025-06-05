# RAG System for Tool Call Logs and GAIA Benchmark

This system provides a Retrieval Augmented Generation (RAG) solution for processing tool call logs and running GAIA benchmark evaluations.

## Setup

Please refer to the [main README](../../../README.md) for instructions on setting up the environment and installing dependencies.

## Project Structure

Refers to the current directory structure:

```
.
├── analysis/               # Cost analysis tools and results
│   ├── calculate_rag_costs.py  # Script to calculate RAG costs
│   └── rag_cost_analysis.json  # Stored cost analysis results
├── corpus/                  # Processed corpus files
├── vector_db/               # Vector store indices
├── results/
│
├── src/                     # Source code
│   ├── benchmark/           # Benchmark modules
│   ├── utils/               # Utility functions
│   ├── process_log.py       # Process log files to corpus
│   ├── encode_corpus.py     # Encode corpus to vector store
│   ├── corpus_rag.py        # Query corpus directly
│   └── load_corpus_index.py # Query from saved index
│
├── run_rag.py               # Main entry point
└── README.md                # This file
```

## Usage

All commands below are to be executed from the current directory. If you want to execute them from the project root, you can do so by adding `benchmarks/baselines/RAG` to the path.

```bash
cd benchmarks/baselines/RAG
```

All operations can be performed through the `run_rag.py` script, which provides a unified interface to all functionality. Make sure to activate your conda environment first:

```bash
conda activate kgot_env
```

### 1. Process Log Files to Corpus

```bash
# Process all log files
python run_rag.py process

# Process a specific number of files
python run_rag.py process 5
```

This will create a `corpus/corpus_N.txt` file where N is the number of log files processed.

### 2. Vectorize Corpus to Create Vector Store

```bash
# Create vector store from corpus
python run_rag.py vectorize corpus/corpus_file.txt

# Force recreation of vector store even if it exists
python run_rag.py vectorize corpus/corpus_file.txt --force
```

This creates vector store files in the `vector_db` directory:

- `{corpus_file}_documents.pkl`: Raw document objects
- `{corpus_file}_faiss_index/`: Directory containing FAISS index files

### 3. Query the Knowledge Base

```bash
# Query from corpus file
python run_rag.py query --corpus_path corpus/corpus_file.txt --query "Your query" --n_retrieved 3

# Query from saved vector index
python run_rag.py query --index_path vector_db/corpus_file_faiss_index --query "Your query" --n_retrieved 3
```

## GAIA Benchmark Evaluation

Compare the RAG system against the GAIA benchmark dataset:

```bash
# Activate conda environment first
conda activate kgot_env

# Run benchmark with default settings (3 questions)
python src/benchmark/rag_gaia_benchmark.py --index_path vector_db/corpus_1.txt_faiss_index --log_folder_base results/benchmark_run --gaia_file benchmarks/datasets/GAIA/validation/merged_dataset.json

# Run benchmark with all questions
python src/benchmark/rag_gaia_benchmark.py --index_path vector_db/corpus_1.txt_faiss_index --log_folder_base results/full_benchmark --max_questions 0 --gaia_file benchmarks/datasets/GAIA/validation/merged_dataset.json

# Run benchmark with async processing (faster)
python src/benchmark/rag_gaia_benchmark.py --index_path vector_db/corpus_1.txt_faiss_index --log_folder_base results/async_benchmark --async_mode --max_questions 10 --gaia_file benchmarks/datasets/GAIA/validation/merged_dataset.json
```

The benchmark will generate detailed token usage and cost statistics in the results folder:

- `llm_cost.json`: Raw token and cost data for each query
- `cost_summary.json`: Summary of total tokens and cost
- `cost_summary_detailed.json`: Detailed breakdown of costs by model

Note: For running benchmarks, it's recommended to use the benchmark scripts directly instead of the run_rag.py wrapper, as this provides more reliable argument parsing.

### Key Parameters

- `--index_path`: Path to your FAISS index (default: vector_db/corpus_2.txt_faiss_index)
- `--log_folder_base`: Folder to store results (required)
- `--gaia_file`: Path to GAIA dataset (default: benchmarks/datasets/GAIA/validation/merged_dataset.json)
- `--max_questions`: Number of questions to evaluate (default: 3, use 0 for all)
- `--num_retrieved`: Number of documents to retrieve per question (default: 5)
- `--llm_model`: LLM model to use (default: gpt-4o-mini)
- `--async_mode`: Use asynchronous processing for faster execution

## GraphRAG Benchmark Evaluation

This system also includes support for running the GAIA benchmark with GraphRAG, an alternative knowledge graph-based RAG approach.

### Setup GraphRAG

1. Install GraphRAG:

   ```bash
   conda activate kgot_env
   pip install graphrag
   ```

2. Set up your data project:

   ```bash
   mkdir -p ./graphrag/ragtest/input
   # Add your corpus files to ./graphrag/ragtest/input
   ```

3. Initialize GraphRAG and run the indexing pipeline:

   ```bash
   conda activate kgot_env
   graphrag init --root ./graphrag/ragtest
   # Edit .env file to add your OpenAI API key
   graphrag index --root ./graphrag/ragtest
   ```

### Run GAIA Benchmark with GraphRAG

Use the `graphrag_gaia_benchmark.py` script to run the benchmark with token tracking:

```bash
conda activate rag_env
python src/benchmark/graphrag_gaia_benchmark.py \
  --ragtest_root ./graphrag/ragtest \
  --results_dir ./results/graphrag_benchmark \
  --gaia_file benchmarks/datasets/GAIA/validation/merged_dataset.json \
  --search_method local \
  --max_questions 10
```

### Key Parameters for GraphRAG

- `--ragtest_root`: Path to the GraphRAG data directory (required)
- `--results_dir`: Directory to store results (required)
- `--gaia_file`: Path to GAIA dataset (required)
- `--search_method`: GraphRAG search method: "local" or "global" (default: "local")
- `--max_questions`: Number of questions to evaluate (default: all)
- `--max_concurrent`: Maximum number of concurrent queries (default: 3)
- `--resume`: Resume from the last processed question
- `--llm_model`: LLM model to use for answer extraction (default: gpt-4o-mini)

### Comparing Token Usage and Costs

To compare the token usage and costs between standard RAG and GraphRAG:

```bash
conda activate kgot_env

# Run a small sample (5 questions) with both systems
python src/benchmark/rag_gaia_benchmark.py --index_path vector_db/corpus_1.txt_faiss_index --log_folder_base results/rag_cost_test --max_questions 5 --gaia_file benchmarks/datasets/GAIA/validation/merged_dataset.json

python src/benchmark/graphrag_gaia_benchmark.py --ragtest_root ./graphrag/ragtest --results_dir ./results/graphrag_cost_test --gaia_file benchmarks/datasets/GAIA/validation/merged_dataset.json --max_questions 5
```

After running both benchmarks, you can compare:

- Total tokens used (prompt + completion)
- Total cost
- Cost per question
- Performance (accuracy vs. cost)

## Tool Call Processing

The system processes tool calls based on their type:

- `ask_search_agent` and `llm_query`: Only includes the response
- `inspect_file_as_text`, `image_inspector`, and `run_python_code`: Includes both query and response
- `extract_zip`: Skipped

## Corpus Structure

Each chunk in the corpus is separated by blank lines:

```
Question: What is the title of the oldest Blu-Ray recorded in this spreadsheet?
Answer: ### 1. Short answer
The title of the oldest Blu-Ray recorded in this spreadsheet is "Time-Parking 2: Parallel Universe."
...

### 1. Search outcome (short version):
Between 2000 and 2009, Mercedes Sosa published a total of **four studio albums**:
...
```

## Troubleshooting

- If you encounter import errors, ensure you're running commands from the project root directory
- The system expects an OpenAI API key to be set in your environment variables
- For better performance with benchmarks, use the async_mode flag with a reasonable max_concurrent value (default: 5)
