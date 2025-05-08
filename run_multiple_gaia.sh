#!/bin/bash
#==============================================================================
# GAIA Multiple Run Script
# Run GAIA with multiple configurations and generate plots
#==============================================================================

# Define the Python script path
# to be run from the Knowledge Graph of Things (KGoT) root folder
PYTHON_SCRIPT="GAIA/gaia.py"

#------------------------------------------------------------------------------
# Configuration
#------------------------------------------------------------------------------

# Define an array of GAIA JSON file paths
gaia_files=(
    "GAIA/dataset/validation_subsets/dummy.json"
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
    echo "Usage: ./run_multiple_gaia.sh [OPTIONS]"
    echo ""
    echo "Optional arguments:"
    echo "  --log_folder_base              Directory where logs will be stored (default: logs/[DB_CHOICE]_[CONTROLLER_CHOICE]_[TOOL_CHOICE])"
    echo "  --attachment_folder            Path to GAIA problems attachments folder (default: GAIA/dataset/attachments/validation)"
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
    echo "  --zero_shot                    Use zero-shot mode"
    echo ""
    exit 0
fi


# Initialize empty vars

# Defaults matching the Python script (excepting log_folder_base and gaia_file)
ATTACHMENT_FOLDER_DEFAULT="GAIA/dataset/attachments/validation"
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
ATTACHMENT_FOLDER=""
CONTROLLER_CHOICE=""
DB_CHOICE=""
TOOL_CHOICE=""
MAX_ITERATIONS=""
NEO4J_URI=""
PYTHON_EXECUTOR_URI=""
LLM_EXECUTION_MODEL=""
LLM_EXECUTION_TEMPERATURE=""
ZERO_SHOT=false

# Parse CLI arguments
OPTS=$($GETOPT -o "" \
  --long log_folder_base:,attachment_folder:,config_llm_path:,logger_level:,logger_file_mode:,\
neo4j_uri:,neo4j_username:,neo4j_password:,python_executor_uri:,\
max_iterations:,num_next_steps_decision:,max_retrieve_query_retry:,max_cypher_fixing_retry:,\
max_final_solution_parsing:,max_tool_retries:,max_llm_retries:,\
llm_planning_model:,llm_planning_temperature:,llm_execution_model:,llm_execution_temperature:,\
controller_choice:,db_choice:,tool_choice:,zero_shot \
  -n 'run_multiple_gaia.sh' -- "$@")

if [ $? != 0 ]; then
    echo "Failed to parse options." >&2
    exit 1
fi

eval set -- "$OPTS"

ARGS=()

while true; do
    case "$1" in
        --log_folder_base) LOG_FOLDER_BASE="$2"; shift 2 ;;
        --attachment_folder) ATTACHMENT_FOLDER="$2"; shift 2 ;;
        --controller_choice) CONTROLLER_CHOICE="$2"; shift 2 ;;
        --db_choice) DB_CHOICE="$2"; shift 2 ;;
        --tool_choice) TOOL_CHOICE="$2"; shift 2 ;;
        --max_iterations) MAX_ITERATIONS="$2"; shift 2 ;;
        --neo4j_uri) NEO4J_URI="$2"; shift 2 ;;
        --python_executor_uri) PYTHON_EXECUTOR_URI="$2"; shift 2 ;;
        --llm_execution_model) LLM_EXECUTION_MODEL="$2"; shift 2 ;;
        --llm_execution_temperature) LLM_EXECUTION_TEMPERATURE="$2"; shift 2 ;;
        --zero_shot) ZERO_SHOT=true; shift ;;
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

# Add zero_shot flag if set
if [ "$ZERO_SHOT" = true ]; then
    ARGS+=("--zero_shot")
fi


# Use defaults if not explicitly provided
: "${MAX_ITERATIONS:=$MAX_ITERATIONS_DEFAULT}"
: "${ATTACHMENT_FOLDER:=$ATTACHMENT_FOLDER_DEFAULT}"
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
echo "  attachment_folder:   $ATTACHMENT_FOLDER"
echo "  controller_choice:   $CONTROLLER_CHOICE"
echo "  db_choice:           $DB_CHOICE"
echo "  tool_choice:         $TOOL_CHOICE"
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
    for i in "${!gaia_files[@]}"; do
        category=$(basename "${gaia_files[$i]}" .json)
        categories+=("$category")
        log_folders+=("${run_log_folder}/${category}")
    done

    # Inner loop to iterate over the arrays in parallel
    for i in "${!gaia_files[@]}"; do
        gaia_file=${gaia_files[$i]}
        log_folder=${log_folders[$i]}

        # Extract the base name from the GAIA file path to construct the output file name
        base_name=$(basename "$gaia_file" .json)
        # output_file="$log_folder/output_${base_name}_${iteration}.txt" # Note that this output file will be overwritten as it does NOT include the time

        echo "Running with GAIA file: $gaia_file and log folder: $log_folder and it is the [$i-th/${#gaia_files[@]}] elements"
        echo "Output will be saved into the log folder in the cmd_log.log file"
        echo
        # Build the Python script command with all arguments
        SCRIPT="$PYTHON_SCRIPT --log_folder_base $log_folder \
        --gaia_file $gaia_file \
        --attachment_folder $ATTACHMENT_FOLDER \
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
    python3 GAIA/plotters/plot_maker.py --root_directory "$run_log_folder" --categories "${categories[@]}" --max_iterations "$MAX_ITERATIONS"
done

#------------------------------------------------------------------------------
# Post-Processing
#------------------------------------------------------------------------------

# Move the snapshots to the log folder
if [ "$ZERO_SHOT" = false ]; then
    mv docker_instances/neo4j_docker/snapshots/$LOG_FOLDER_BASE $LOG_FOLDER_BASE/snapshots
fi
