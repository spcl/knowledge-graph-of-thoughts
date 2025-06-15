#!/bin/bash
#==============================================================================
# SimpleQA Multiple Run Script
# Run SimpleQA with multiple configurations and generate plots
#==============================================================================

# Define the Python script path
# to be run from the Knowledge Graph of Things (KGoT) root folder
PYTHON_SCRIPT="benchmarks/simpleqa.py"

#------------------------------------------------------------------------------
# Configuration
#------------------------------------------------------------------------------

# Define an array of SimpleQA JSON file paths
simpleqa_files=(
    "benchmarks/datasets/SimpleQA/dummy.json"
)

# Define the number of runs (change this to any number you want)
num_runs=1


# Attempt to locate GNU getopt via Homebrew
GETOPT_BIN="$(brew --prefix gnu-getopt 2>/dev/null)/bin/getopt"

# Check if GETOPT_BIN is non-empty and executable; if not, use the system getopt.
if [ -n "$GETOPT_BIN" ] && [ -x "$GETOPT_BIN" ]; then
    GETOPT="$GETOPT_BIN"
else
    GETOPT="$(command -v getopt)"
fi

echo "Using getopt: $GETOPT"

#------------------------------------------------------------------------------
# Handle arguments
#------------------------------------------------------------------------------

# Handle --help flag
if [ "$1" == "--help" ]  || [ "$1" = "-h" ]; then
    echo "Usage: ./run_multiple_simpleqa.sh [OPTIONS]"
    echo ""
    echo "Optional arguments:"
    echo "  --log_folder_base              Directory where logs will be stored (default: logs/[DB_CHOICE]_[CONTROLLER_CHOICE]_[TOOL_CHOICE])"
    echo "  --attachment_folder            Path to SimpleQA problems attachments folder (default: None)"
    echo "  --config_llm_path              Path to LLM configuration file (default: kgot/config_llms.json)"
    echo "  --logger_level                 Logging level (default: 20 [INFO])"
    echo "  --logger_file_mode             Log file mode (default: a)"
    echo ""
    echo "  --neo4j_uri                    Docker URI for Neo4j (default: bolt://localhost:7687)"
    echo "  --neo4j_username               Neo4j username (default: neo4j)"
    echo "  --neo4j_password               Neo4j password (default: password)"
    echo "  --python_executor_uri          URI for Python tool executor (default: http://localhost:16000/run)"
    echo ""
    echo "  --max_iterations               Max iterations for KGoT (default: 7)"
    echo "  --num_next_steps_decision      Number of next steps decision (default: 5)"
    echo "  --max_retrieve_query_retry     Max retries for retrieve query (default: 3)"
    echo "  --max_cypher_fixing_retry      Max retries for Cypher fixing (default: 3)"
    echo "  --max_final_solution_parsing   Max retries for final solution parsing (default: 3)"
    echo "  --max_tool_retries             Max retries for tools (default: 6)"
    echo "  --max_llm_retries              Max retries for LLM (default: 6)"
    echo ""
    echo "  --llm_planning_model           LLM planning model (default: gpt-4o-mini)"
    echo "  --llm_planning_temperature     LLM planning temperature (default: 0.0)"
    echo "  --llm_execution_model          LLM execution model (default: gpt-4o-mini)"
    echo "  --llm_execution_temperature    LLM execution temperature (default: 0.0)"
    echo ""
    echo "  --controller_choice            Controller choice (options: queryRetrieve, directRetrieve; default: queryRetrieve)"
    echo "  --db_choice                    Database choice (options: neo4j, networkX; default: neo4j)"
    echo "  --tool_choice                  Tool choice (default: tools_v2_3)"
    echo "  --gaia_formatter               Use GAIA formatter"
    echo ""
    exit 0
fi


# Initialize empty vars

# Defaults matching the Python script (excepting log_folder_base and simpleqa_file)
CONTROLLER_CHOICE_DEFAULT="queryRetrieve"
DB_CHOICE_DEFAULT="neo4j"
TOOL_CHOICE_DEFAULT="tools_v2_3"
MAX_ITERATIONS_DEFAULT=7
NEO4J_URI_DEFAULT="bolt://localhost:7687"
PYTHON_EXECUTOR_URI_DEFAULT="http://localhost:16000/run"
LLM_EXECUTION_MODEL_DEFAULT="gpt-4o-mini"
LLM_EXECUTION_TEMPERATURE_DEFAULT=0.0

# Track values
LOG_FOLDER_BASE=""
CONTROLLER_CHOICE=""
DB_CHOICE=""
TOOL_CHOICE=""
MAX_ITERATIONS=""
NEO4J_URI=""
PYTHON_EXECUTOR_URI=""
GAIA_FORMATTER=false
LLM_EXECUTION_MODEL=""
LLM_EXECUTION_TEMPERATURE=""

# Parse CLI arguments
OPTS=$($GETOPT -o "" \
  --long log_folder_base:,attachment_folder:,config_llm_path:,logger_level:,logger_file_mode:,\
neo4j_uri:,neo4j_username:,neo4j_password:,python_executor_uri:,\
max_iterations:,num_next_steps_decision:,max_retrieve_query_retry:,max_cypher_fixing_retry:,\
max_final_solution_parsing:,max_tool_retries:,max_llm_retries:,\
llm_planning_model:,llm_planning_temperature:,llm_execution_model:,llm_execution_temperature:,\
controller_choice:,db_choice:,tool_choice:,gaia_formatter \
  -n 'run_multiple_simpleqa.sh' -- "$@")

if [ $? != 0 ]; then
    echo "Failed to parse options." >&2
    exit 1
fi

eval set -- "$OPTS"

ARGS=()

while true; do
    case "$1" in
        --log_folder_base) LOG_FOLDER_BASE="$2"; shift 2 ;;
        --controller_choice) CONTROLLER_CHOICE="$2"; shift 2 ;;
        --db_choice) DB_CHOICE="$2"; shift 2 ;;
        --tool_choice) TOOL_CHOICE="$2"; shift 2 ;;
        --max_iterations) MAX_ITERATIONS="$2"; shift 2 ;;
        --neo4j_uri) NEO4J_URI="$2"; shift 2 ;;
        --python_executor_uri) PYTHON_EXECUTOR_URI="$2"; shift 2 ;;
        --llm_execution_model) LLM_EXECUTION_MODEL="$2"; shift 2 ;;
        --llm_execution_temperature) LLM_EXECUTION_TEMPERATURE="$2"; shift 2 ;;
        --gaia_formatter) GAIA_FORMATTER=true; shift ;;
        --) shift; break ;;
        *)
            # For all other options, if set, add to ARGS
            if [[ -n "$2" && "$2" != --* ]]; then
                ARGS+=("$1" "$2"); shift 2
            else
                shift
            fi
            ;;
    esac
done

# Add gaia_formatter flag if set
if [ "$GAIA_FORMATTER" = true ]; then
    ARGS+=("--gaia_formatter")
fi


# Use defaults if not explicitly provided
: "${MAX_ITERATIONS:=$MAX_ITERATIONS_DEFAULT}"
: "${CONTROLLER_CHOICE:=$CONTROLLER_CHOICE_DEFAULT}"
: "${DB_CHOICE:=$DB_CHOICE_DEFAULT}"
: "${TOOL_CHOICE:=$TOOL_CHOICE_DEFAULT}"
: "${NEO4J_URI:=$NEO4J_URI_DEFAULT}"
: "${PYTHON_EXECUTOR_URI:=$PYTHON_EXECUTOR_URI_DEFAULT}"
: "${LLM_EXECUTION_MODEL:=$LLM_EXECUTION_MODEL_DEFAULT}"
: "${LLM_EXECUTION_TEMPERATURE:=$LLM_EXECUTION_TEMPERATURE_DEFAULT}"

# Set log_folder_base default
LOG_FOLDER_BASE_DEFAULT="logs/${DB_CHOICE}_${CONTROLLER_CHOICE}_${TOOL_CHOICE}"
# If Zero_shot is true use another default name
if [ "$ZERO_SHOT" = true ]; then
    LOG_FOLDER_BASE_DEFAULT="logs/${LLM_EXECUTION_MODEL}_${LLM_EXECUTION_TEMPERATURE}_zero_shot"
fi
# Use log_folder_base default if not explicitly provided
: "${LOG_FOLDER_BASE:=$LOG_FOLDER_BASE_DEFAULT}"

echo "KGoT Run Configuration:"
echo "  log_folder_base:     $LOG_FOLDER_BASE"
echo "  controller_choice:   $CONTROLLER_CHOICE"
echo "  db_choice:           $DB_CHOICE"
echo "  tool_choice:         $TOOL_CHOICE"
echo "  gaia_formatter:      $GAIA_FORMATTER"
echo

#------------------------------------------------------------------------------
# Main Script
#------------------------------------------------------------------------------

# Outer loop for the number of runs
for ((run=1; run<=num_runs; run++)); do
    echo "Iteration: $run/$num_runs"

    # Set up log folders for the run based on root folder
    if [[ $num_runs -gt 1 ]]; then
        run_log_folder="${LOG_FOLDER_BASE}/run_${run}"
    else
        run_log_folder="$LOG_FOLDER_BASE"
    fi
    log_folders=()
    categories=()
    for i in "${!simpleqa_files[@]}"; do
        category=$(basename "${simpleqa_files[$i]}" .json)
        categories+=("$category")
        log_folders+=("${run_log_folder}/${category}")
    done

    # Inner loop to iterate over the arrays in parallel
    for i in "${!simpleqa_files[@]}"; do
        simpleqa_file=${simpleqa_files[$i]}
        log_folder=${log_folders[$i]}

        # Extract the base name from the SimpleQA file path to construct the output file name
        base_name=$(basename "$simpleqa_file" .json)

        echo "Running with SimpleQA file: $simpleqa_file and log folder: $log_folder and it is the [$i-th/${#simpleqa_files[@]}] elements"
        echo "Output will be saved into the log folder in the cmd_log.log file"
        echo
        # Build the Python script command with all arguments
        SCRIPT="$PYTHON_SCRIPT --log_folder_base $log_folder \
        --file $simpleqa_file \
        --neo4j_uri $NEO4J_URI \
        --python_executor_uri $PYTHON_EXECUTOR_URI \
        --controller_choice $CONTROLLER_CHOICE \
        --db_choice $DB_CHOICE \
        --tool_choice $TOOL_CHOICE \
        --max_iterations $MAX_ITERATIONS \
        --llm_execution_model $LLM_EXECUTION_MODEL \
        --llm_execution_temperature $LLM_EXECUTION_TEMPERATURE "

        # Add additional arguments from the ARGS array
        SCRIPT="$SCRIPT ${ARGS[@]}"

        echo "Running script:"
        echo $SCRIPT
        echo
        
        # Change the Python version if needed and run the script
        python3 $SCRIPT
    done

    # Create plots for this run
    python3 benchmarks/plotters/plot_maker.py --root_directory "$run_log_folder" --categories "${categories[@]}" --max_iterations "$MAX_ITERATIONS" --benchmark "simpleqa"
done

#------------------------------------------------------------------------------
# Post-Processing
#------------------------------------------------------------------------------

# Move the snapshots to the log folder
if [ "$ZERO_SHOT" = false ]; then
    mv kgot/knowledge_graph/_snapshots/$LOG_FOLDER_BASE $LOG_FOLDER_BASE/snapshots
fi
