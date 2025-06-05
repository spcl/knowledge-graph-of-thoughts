# GAIA

The [GAIA](https://arxiv.org/abs/2311.12983) benchmark can be used for rigorously testing LLM-driven agent architectures across a diverse set of tasks.

## Installing the GAIA Dataset

A script has been provided to fetch the GAIA benchmark dataset.
Please refer to the [README](./dataset/README.md) inside the [dataset](./dataset) directory for installation instructions.

## Evaluate KGoT on GAIA

To evaluate KGoT on the GAIA dataset, use the following command from the **root folder**. There are two required arguments:

- `--log_folder_base`: The base folder where the logs will be stored.
- `--gaia_file`: The path to the GAIA dataset file. To use different subsets extracted from the GAIA dataset, modify
  this argument. Note that the subsets should have the same format as the original GAIA dataset.

```bash
python3 GAIA/gaia.py --log_folder_base log --gaia_file [path_to_json]
```

The full command line interface has the following options:

```bash
python3 GAIA/gaia.py --help
usage: gaia.py [-h] --log_folder_base LOG_FOLDER_BASE --gaia_file GAIA_FILE
               [--attachment_folder ATTACHMENT_FOLDER] [--config_llm_path CONFIG_LLM_PATH]
               [--logger_level LOGGER_LEVEL] [--logger_file_mode LOGGER_FILE_MODE]
               [--neo4j_uri NEO4J_URI] [--neo4j_username NEO4J_USERNAME]
               [--neo4j_password NEO4J_PASSWORD] [--python_executor_uri PYTHON_EXECUTOR_URI]
               [--max_iterations MAX_ITERATIONS]
               [--num_next_steps_decision NUM_NEXT_STEPS_DECISION]
               [--max_retrieve_query_retry MAX_RETRIEVE_QUERY_RETRY]
               [--max_cypher_fixing_retry MAX_CYPHER_FIXING_RETRY]
               [--max_final_solution_parsing MAX_FINAL_SOLUTION_PARSING]
               [--max_tool_retries MAX_TOOL_RETRIES] [--max_llm_retries MAX_LLM_RETRIES]
               [--llm_planning_model LLM_PLANNING_MODEL]
               [--llm_planning_temperature LLM_PLANNING_TEMPERATURE]
               [--llm_execution_model LLM_EXECUTION_MODEL]
               [--llm_execution_temperature LLM_EXECUTION_TEMPERATURE]
               [--controller_choice CONTROLLER_CHOICE] [--db_choice DB_CHOICE]
               [--tool_choice TOOL_CHOICE] [--zero_shot]

Run GAIA processing with customized paths.

options:
  -h, --help            show this help message and exit
  --log_folder_base LOG_FOLDER_BASE
                        Base folder for logging results
  --gaia_file GAIA_FILE
                        Path to GAIA JSON file
  --attachment_folder ATTACHMENT_FOLDER
                        Path to GAIA problems attachments folder
  --config_llm_path CONFIG_LLM_PATH
                        Path to LLM configuration file
  --logger_level LOGGER_LEVEL
                        Logging level
  --logger_file_mode LOGGER_FILE_MODE
                        Log file mode
  --neo4j_uri NEO4J_URI
                        Docker URI for Neo4j
  --neo4j_username NEO4J_USERNAME
                        Neo4j username
  --neo4j_password NEO4J_PASSWORD
                        Neo4j password
  --python_executor_uri PYTHON_EXECUTOR_URI
                        URI for Python tool executor
  --max_iterations MAX_ITERATIONS
                        Max iterations for KGoT
  --num_next_steps_decision NUM_NEXT_STEPS_DECISION
                        Number of next steps decision
  --max_retrieve_query_retry MAX_RETRIEVE_QUERY_RETRY
                        Max retries for retrieve query
  --max_cypher_fixing_retry MAX_CYPHER_FIXING_RETRY
                        Max retries for Cypher fixing
  --max_final_solution_parsing MAX_FINAL_SOLUTION_PARSING
                        Max retries for final solution parsing
  --max_tool_retries MAX_TOOL_RETRIES
                        Max retries for tools
  --max_llm_retries MAX_LLM_RETRIES
                        Max retries for LLM
  --llm_planning_model LLM_PLANNING_MODEL
                        LLM planning model
  --llm_planning_temperature LLM_PLANNING_TEMPERATURE
                        LLM planning temperature
  --llm_execution_model LLM_EXECUTION_MODEL
                        LLM execution model
  --llm_execution_temperature LLM_EXECUTION_TEMPERATURE
                        LLM execution temperature
  --controller_choice CONTROLLER_CHOICE
                        Controller choice
  --db_choice DB_CHOICE
                        Database choice
  --tool_choice TOOL_CHOICE
                        Tool choice
  --zero_shot           Use zero-shot mode
```

## Evaluating Multiple Subsets

To run different subsets of the GAIA dataset, we provide a bash script in the main directory.
You should execute the script from the **root folder**:

```bash
./run_multiple_gaia.sh
```

This bash script will run the `gaia.py` Python script on all provided GAIA subsets and will store the respective results in the corresponding log folder as defined in the script.

By default, the output of each `gaia.py` script execution will be stored in the respective log folder in the file `cmd_log.log`.

To modify the number of times a given dataset is evaluated, please update the `num_runs` variable in the bash script, which defaults to 1.

## Results

The logs will be stored inside a newly generated subfolder with the timestamp of the run.

The directory will contain the following files:

- `{current_time}/cmd_log.log`: Contains the higher-level overview of the run.
- `{current_time}/output.log`: Contains the detailed logs of the run.
- `{current_time}/llm_cost.json`: Contains the costs of the language model and tools calls.
- `{current_time}/llm_cost_total.json`: Contains the sum of the costs of the language model and tools calls.

To modify the output directory, update the `--log_folder_base` argument.

Additionally, we provide a comprehensive set of automatic analysis scripts for plotting answer correctness, tool usage as well as the costs regarding the usage of language models.
These metrics are automatically evaluated and visualized using the `GAIA/plotters/plot_maker.py` script for understanding the framework's performance.
