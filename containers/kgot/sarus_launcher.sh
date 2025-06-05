#!/bin/bash

# Load environment variables
set -a
source .env
set +a

KGOT=$(realpath ../../kgot)
RESULTS=$(realpath ../../results)
GAIA=$(realpath ../../GAIA)
PYPROJECT=$(realpath ../../pyproject.toml)
RUN_MULTIPLE_GAIA=$(realpath ../../run_multiple_gaia.sh)
RUN_MULTIPLE_SIMPLEQA=$(realpath ../../run_multiple_simpleqa.sh)
LICENSE=$(realpath ../../LICENSE)
README=$(realpath ../../README.md)

bash -c "
sarus run \
  --workdir=/home/knowledge_graph_of_thoughts \
  --mount=type=bind,source=$KGOT,destination=/home/knowledge_graph_of_thoughts/kgot \
  --mount=type=bind,source=$RESULTS,destination=/home/knowledge_graph_of_thoughts/results \
  --mount=type=bind,source=$GAIA,destination=/home/knowledge_graph_of_thoughts/GAIA \
  --mount=type=bind,source=$PYPROJECT,destination=/home/knowledge_graph_of_thoughts/pyproject.toml \
  --mount=type=bind,source=$RUN_MULTIPLE_GAIA,destination=/home/knowledge_graph_of_thoughts/run_multiple_gaia.sh \
  --mount=type=bind,source=$RUN_MULTIPLE_SIMPLEQA,destination=/home/knowledge_graph_of_thoughts/run_multiple_simpleqa.sh \
  --mount=type=bind,source=$LICENSE,destination=/home/knowledge_graph_of_thoughts/LICENSE \
  --mount=type=bind,source=$README,destination=/home/knowledge_graph_of_thoughts/README.md \
  spcleth/kgot:latest \
  bash -c \"python3.11 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -e . && \
    playwright install && \
    chmod +x run_multiple* && \
    ./${FILE_TO_EXECUTE} --log_folder_base '${LOG_FOLDER_BASE}' --attachment_folder '${ATTACHMENT_FOLDER}' --config_llm_path '${CONFIG_LLM_PATH}' --logger_level ${LOGGER_LEVEL} --logger_file_mode '${LOGGER_FILE_MODE}' --neo4j_uri '${SARUS_NEO4J_URI}' --neo4j_username '${NEO4J_USERNAME}' --neo4j_password '${NEO4J_PASSWORD}' --python_executor_uri '${SARUS_PYTHON_URI}' --max_iterations ${MAX_ITERATIONS} --num_next_steps_decision ${NUM_NEXT_STEPS_DECISION} --max_retrieve_query_retry ${MAX_RETRIEVE_QUERY_RETRY} --max_cypher_fixing_retry ${MAX_CYPHER_FIXING_RETRY} --max_final_solution_parsing ${MAX_FINAL_SOLUTION_PARSING} --max_tool_retries ${MAX_TOOL_RETRIES} --max_llm_retries ${MAX_LLM_RETRIES} --llm_planning_model '${LLM_PLANNING_MODEL}' --llm_planning_temperature ${LLM_PLANNING_TEMPERATURE} --llm_execution_model '${LLM_EXECUTION_MODEL}' --llm_execution_temperature ${LLM_EXECUTION_TEMPERATURE} --controller_choice '${CONTROLLER_CHOICE}' --db_choice '${DB_CHOICE}' --tool_choice '${TOOL_CHOICE}' --sparql_read_uri '${SARUS_SPARQL_READ_URI}' --sparql_write_uri '${SARUS_SPARQL_WRITE_URI}' '${ZERO_SHOT}' '${GAIA_FORMATTER}'\"
"