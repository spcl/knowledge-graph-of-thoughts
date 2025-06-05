# Controller

The **Controller** is the central orchestrator of the KGoT system, responsible for managing the interaction between the *knowledge graph* and the *integrated tools*.
When a user submits a query, the Controller initiates the reasoning process by interpreting the task and coordinating the steps required for its resolution.

To offer fine-grained control over the KGoT control logic, the following parameters can be configured:

- `num_next_steps_decision`: Number of times to prompt an LLM on how to proceed (SOLVE/ENHANCE).
- `max_retrieve_query_retry`: Maximum retries for a SOLVE query when the initial attempt fails.
- `max_cypher_fixing_retry`: Maximum retries for fixing a Cypher query that encounter errors.
- `max_final_solution_parsing`: Maximum retries of parsing the final solution from the output of the SOLVE query.
- `max_tool_retries`: Maximum number of retries when a tool invocation fails.

Controller classes derived from the [`ControllerInterface`](controller_interface.py#L30) abstract class embed such parameters with default values defined for their class.
Users can experiment with custom parameters as well.

## Architecture

The KGoT Controller employs a dual-LLM architecture with a clear separation of roles between constructing the knowledge graph (managed by the **LLM Graph Executor**) and interacting with tools (managed by the **LLM Tool Executor**).
The following description is based on the "System Workflow" section of our paper, which we combine with specifics of our implementation.

### LLM Graph Executor

The **LLM Graph Executor** is responsible for decision making and orchestrating the knowledge graph-based task resolution workflow, leading to different solution pathways (SOLVE or ENHANCE).

- `define_next_step`: **Determine the next step.** This function is invoked up to `num_next_steps_decision` times to collect replies from an LLM, which are subsequently used with a majority vote to decide whether to retrieve information from the knowledge graph for solving the task (SOLVE) or insert new information (ENHANCE).
- `_insert_logic`: **Run ENHANCE.** Once we have successfully executed tool calls and gathered new information, the system generates the Enhance query or queries to modify the knowledge graph accordingly. Each Enhance query is executed and its output is validated.
- `_retrieve_logic`: **Run SOLVE.** If the majority vote directs the system to the SOLVE pathway, a predefined solution technique (direct or query-based retrieve) is used for the solution generation.
- `_get_math_response`: **Apply additional mathematical processing** (optional).
- `parse_solution_with_llm`: **Parse the final solution** into a suitable format and prepare it as the KGoT response.

### LLM Tool Executor

The **LLM Tool Executor** decides which tools to use as well as handling the interaction with these tools.

- `define_tool_calls`: **Define tool calls.** The system orchestrates the appropriate tool calls based on the knowledge graph state.
- `_invoke_tools_after_llm_response`, `_invoke_tool_with_retry`: **Run tool calls** w/o retry.

## Knowledge Extraction

We explore different approaches for knowledge extraction, once the knowledge graph has been sufficiently populated.
In our reference implementation, the LLM can either solve the task by either directly embedding the knowledge graph in its context, called **Direct Retrieval (DR)**, or querying the graph store for specific insights with the help of a **Graph Query**.

For the time being, we provide five control logic sets depending on the [backend type](../knowledge_graph/README.md) (Neo4j, NetworkX or SparQL) and the solution technique (DR or Graph Query).
In further versions, solution techniques could be selected and switched behind a single interface, providing more flexibility and removing code redundancy.
