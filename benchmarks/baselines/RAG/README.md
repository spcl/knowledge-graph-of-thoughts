# Simple RAG

## Setup

Please refer to the [main README](../../../README.md#setup-guide) for instructions on setting up the environment and installing dependencies.

### Configuring API Keys and Models

To get started make a copy of the following template file inside the `src/utils` directory:

- `src/utils/config_llms.template.json`

Then rename it as follows:

- `config_llms.template.json` → `config_llms.json`

Please update the API keys, if necessary, for the language models you intend to use in the new `src/utils/config_llms.json` file.
You can also add new models by incorporating their information into the JSON file.
The object key is the language model identifier used in KGoT, and the various attributes contain the information needed to run the model.

## Project Structure

We first provide an overview over the directory structure of the Simple RAG baseline:

```
.
├── analysis/                # Cost analysis tools
│   └── calculate_rag_costs.py
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

This system provides a simple Retrieval Augemented Generation (RAG) solution for processing tool call logs into a vector database and running the GAIA benchmark on top of that vector database.

All commands below are to be executed from the current directory. If you want to execute them from the project root, you can do so by adding `benchmarks/baselines/RAG` to the path.

```bash
cd benchmarks/baselines/RAG
```

All operations can be performed through the `run_rag.py` script, which provides a unified interface to all functionality. Please make sure to activate your Python environment (if any) first.

### 1. Process Log Files to Corpus

Simple RAG relies on the tool call logs from previous KGoT runs and expects these logs inside the `data/success_log` directory.
Their naming should follow the pattern `cmd_log_N.log`, where `N` is a non-negative integer number.
For transparency reasons, we provide the log files used during the evaluation of the paper inside that directory.

```bash
# Process all log files
python3 run_rag.py process

# Process a specific number of files, i.e. the first five log files
python3 run_rag.py process 5
```

The script will create a `corpus/corpus_N.txt` file, where N is the number of processed log files.

### 2. Vectorize Corpus to Create Vector Store

```bash
# Create vector store from corpus
python3 run_rag.py vectorize corpus/corpus_file.txt

# Force recreation of vector store even if it exists
python3 run_rag.py vectorize corpus/corpus_file.txt --force
```

The script will output vector store files in the `vector_db` directory:

- `{corpus_file}_documents.pkl`: Raw document objects
- `{corpus_file}_faiss_index/`: Directory containing FAISS index files

### 3. Query the Knowledge Base

```bash
# Run query against a corpus file
python3 run_rag.py query --corpus_path corpus/corpus_file.txt --query "Your query" --n_retrieved 3

# Run query against a vector database index
python3 run_rag.py query --index_path vector_db/corpus_file_faiss_index --query "Your query" --n_retrieved 3
```

## GAIA Benchmark Evaluation

Run the GAIA benchmark with the Simple RAG baseline:

```bash
# Run benchmark with default settings (3 questions)
python3 src/benchmark/rag_gaia_benchmark.py --index_path vector_db/corpus_1.txt_faiss_index --log_folder_base results/benchmark_run --gaia_file ../../datasets/GAIA/validation/merged_dataset.json

# Run benchmark with all questions
python3 src/benchmark/rag_gaia_benchmark.py --index_path vector_db/corpus_1.txt_faiss_index --log_folder_base results/full_benchmark --max_questions 0 --gaia_file ../../datasets/GAIA/validation/merged_dataset.json

# Run benchmark with async processing (faster)
python3 src/benchmark/rag_gaia_benchmark.py --index_path vector_db/corpus_1.txt_faiss_index --log_folder_base results/async_benchmark --async_mode --max_questions 10 --gaia_file ../../datasets/GAIA/validation/merged_dataset.json
```

The benchmark will generate detailed token usage and cost statistics in the results folder:

- `llm_cost.json`: Raw token and cost data for each query
- `cost_summary.json`: Summary of total tokens and cost
- `cost_summary_detailed.json`: Detailed breakdown of costs by model

### Key Parameters

- `--index_path`: Path to your FAISS index (default: `vector_db/corpus_2.txt_faiss_index`)
- `--log_folder_base`: Folder to store results (required)
- `--gaia_file`: Path to GAIA dataset (default: `../../datasets/GAIA/validation/merged_dataset.json`)
- `--max_questions`: Number of questions to evaluate (default: 3, use 0 for all)
- `--num_retrieved`: Number of documents to retrieve per question (default: 5)
- `--llm_model`: LLM model to use (default: gpt-4o-mini)
- `--async_mode`: Use asynchronous processing for faster execution

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

- If you encounter import errors, ensure you're running commands from the project root directory.
- For better performance with benchmarks, use the `async_mode` flag with a reasonable `max_concurrent` value (default: 5).
