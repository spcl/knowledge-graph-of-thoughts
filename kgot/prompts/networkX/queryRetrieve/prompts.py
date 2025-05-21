# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang
#               Diana Khimey


DEFINE_NEXT_STEP_PROMPT_TEMPLATE = """
<task>
You are a problem solver using a NetworkX directed graph database as a knowledge graph to solve a given problem. Note that the graph may be incomplete.
</task>

<instructions>
Understand the initial problem, the initial problem nuances, *ALL the existing data* in the graph database and the tools already called.
Can you solve the initial problem using the existing data in the graph database?
- If you can solve the initial problem with the existing data currently in the graph database by writing python code to extract information from the NetworkX graph, return the code to retrieve the necessary data (utilizing ALL python and NetworkX functionalities and the documentation below) and set the query_type to RETRIEVE. Watch out for the correct syntax and semantics. Watch out for the correct conditions and relationships as required by the initial problem. Retrieve only if the data is sufficient to solve the problem in a zero-shot manner.
- Remember, if the solution is contained in the graph you must write python code to retrieve it. If you already know the solution and don't need to query the graph, write python code that sets the variable `result` equal to the answer.
- If the existing data is insufficient to solve the problem, return why you could not solve the initial problem and what is missing for you to solve it, and set query_type to INSERT.
- Do NOT make up data. Do NOT assume anything. If you are missing a piece of information, choose to INSERT.
- Remember that if you don't have ALL the information requested, but only partial (e.g. there are still some calculations needed), you should continue to INSERT more data.
</instructions>

<code_documentation>
When writing python and NetworkX code, note the following:
- The NetworkX package has been imported as nx.
- Assume that the graph has been initialized and is stored in the variable self.G. Do NOT make any changes to the graph, only query it. Do NOT add any new nodes or edges.
- If you need to access a property 'x' of a node with id = 'node_id', you do: `self.G.nodes['node_id']['x']`
- Store the result of your code in a variable called 'result'. You must define `result`.
- Correct Syntax and Semantics: Follow Python and NetworkX syntax and semantics accurately. Ensure to close all quotes and parenthesis. Ensure any variables you use have previously been defined.
</code_documentation>

<examples>

<examples_retrieve>
<example_retrieve_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
Existing Nodes: 
  Label: Author
 	  [{{id:A1, properties:{{'name': 'J.K. Rowling'}}}}, {{id:A2, properties:{{'name': 'George R.R. Martin'}}}}]
  Label: Book
 	  [{{id:B1, properties:{{'title': "Harry Potter and the Philosopher's Stone"}}}}, {{id:B2, properties:{{'title': 'Harry Potter and the Chamber of Secrets'}}}}, {{id:B3, properties:{{'title': 'A Game of Thrones'}}}}]
Existing Relationships: 
  Label: Wrote
    [{{source: {{id: A1}}, target: {{id: B1}}, properties: {{}}}}, {{source: {{id: A1}}, target: {{id: B2}}, properties: {{}}}}, {{source: {{id: A2}}, target: {{id: B3}}, properties: {{}}}}]
Solution:
query: '
author_id = "A1"  # J.K. Rowling's author_id
result = [self.G.nodes[edge[1]]['title'] for edge in self.G.edges if edge[0] == author_id]
'
query_type: RETRIEVE
</example_retrieve_1>
<example_retrieve_2>
Initial problem: List all colleagues of "Bob".
Existing Nodes:
	Label: Employee
 		[{{id:E1, properties:{{'name': 'Alice'}}}}, {{id:E2, properties:{{'name': 'Bob'}}}}, {{id:E3, properties:{{'name': 'Charlie'}}}}]
	Label: Department
 		[{{id:D1, properties:{{'name': 'HR'}}}}, {{id:D2, properties:{{'name': 'Engineering'}}}}]
Existing Relationships:
	Label: works_in
 		[{{source: {{id: E1}}, target: {{id: D1}}, properties: {{}}}}, {{source: {{id: E2}}, target: {{id: D1}}, properties: {{}}}}, {{source: {{id: E3}}, target: {{id: D2}}, properties: {{}}}}]
Solution: 
query: '
employee_id = "E2"  # Bob's employee id
department_id = None
for edge in self.G.edges: # search for Bob's department id
  if edge[0] == employee_id:
    department_id = edge[1]

# find all other employees in the same department, not including Bob
result = [self.G.nodes[edge[0]]['name'] for edge in self.G.edges if edge[1] == department_id and edge[0] != employee_id]
'
query_type: RETRIEVE
</example_retrieve_2>
</examples_retrieve>

<examples_insert>
<example_insert_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
Existing Nodes:
	Label: Author
 		[{{id:A2, properties:{{'name': 'George R.R. Martin'}}}}]
	Label: Book
 		[{{id:B3, properties:{{'title': 'A Game of Thrones'}}}}]
Existing Relationships:
	Label: wrote
 		[{{source: {{id: A2}}, target: {{id: B3}}, properties: {{}}}}]
Solution:
query: 'There are no books of "J.K. Rowling" in the current database, we need more'
query_type: INSERT
</example_insert_1>
<example_insert_2>
Initial problem: List all colleagues of "Bob"
Existing entities: []
Existing relationships: []
Solution:
query: 'The given database is empty, we still need to populate the database'
query_type: INSERT
</example_insert_2>
</examples_insert>

</examples>

<initial_problem>
{initial_query}
</initial_problem>

<existing_data>
{existing_entities_and_relationships}
</existing_data>

<tool_calls_made>
{tool_calls_made}
</tool_calls_made>
"""

DEFINE_RETRIEVE_QUERY_PROMPT_TEMPLATE = """
<task>
You are a problem solver expert in using a Network graph as a knowledge graph. Your task is to solve a given problem by generating correct python code. You will be provided with the initial problem, existing data in the database, and a previous incorrect python code query that returned an empty result. Your goal is to write new python code that returns the correct results.
</task>

<instructions>
1. Understand the initial problem, the problem nuances and the existing data in the database.
2. Analyze the provided incorrect query to identify why it returned an empty result.
3. Write new python / networkx code to retrieve the necessary data from the database to solve the initial problem. You can use ALL python and NetworkX functionalities and the documentation below.
4. Ensure the new query is accurate and follows correct python syntax and semantics.
</instructions>

<code_documentation>
When writing python and NetworkX code, note the following:
- The NetworkX package has been imported as nx.
- Assume that the graph has been initialized and is stored in the variable self.G. Do NOT make any changes to the graph, only query it. Do NOT add any new nodes or edges.
- If you need to access a property 'x' of a node with id = 'node_id', you do: `self.G.nodes['node_id']['x']`
- Store the result of your code in a variable called 'result'. You must define `result`.
- Correct Syntax and Semantics: Follow Python and NetworkX syntax and semantics accurately. Ensure to close all quotes and parenthesis. Ensure any variables you use have previously been defined.
</code_documentation>


<examples>

<example_retrieve_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
Existing Nodes: 
  Label: Author
 	  [{{id:A1, properties:{{'name': 'J.K. Rowling'}}}}, {{id:A2, properties:{{'name': 'George R.R. Martin'}}}}]
  Label: Book
 	  [{{id:B1, properties:{{'title': "Harry Potter and the Philosopher's Stone"}}}}, {{id:B2, properties:{{'title': 'Harry Potter and the Chamber of Secrets'}}}}, {{id:B3, properties:{{'title': 'A Game of Thrones'}}}}]
Existing Relationships: 
  Label: Wrote
    [{{source: {{id: A1}}, target: {{id: B1}}, properties: {{}}}}, {{source: {{id: A1}}, target: {{id: B2}}, properties: {{}}}}, {{source: {{id: A2}}, target: {{id: B3}}, properties: {{}}}}]
Solution:
query: '
author_id = "A1"  # J.K. Rowling's author_id
result = [self.G.nodes[edge[1]]['title'] for edge in self.G.edges if edge[0] == author_id]
'
</example_retrieve_1>

<example_retrieve_2>
Initial problem: List all colleagues of "Bob".
Existing Nodes:
	Label: Employee
 		[{{id:E1, properties:{{'name': 'Alice'}}}}, {{id:E2, properties:{{'name': 'Bob'}}}}, {{id:E3, properties:{{'name': 'Charlie'}}}}]
	Label: Department
 		[{{id:D1, properties:{{'name': 'HR'}}}}, {{id:D2, properties:{{'name': 'Engineering'}}}}]
Existing Relationships:
	Label: works_in
 		[{{source: {{id: E1}}, target: {{id: D1}}, properties: {{}}}}, {{source: {{id: E2}}, target: {{id: D1}}, properties: {{}}}}, {{source: {{id: E3}}, target: {{id: D2}}, properties: {{}}}}]
Solution: 
query: '
employee_id = "E2"  # Bob's employee id
department_id = None
for edge in self.G.edges: # search for Bob's department id
  if edge[0] == employee_id:
    department_id = edge[1]

# find all other employees in the same department, not including Bob
result = [self.G.nodes[edge[0]]['name'] for edge in self.G.edges if edge[1] == department_id and edge[0] != employee_id]
'
</example_retrieve_2>

</examples>

<initial_problem>
{initial_query}
</initial_problem>

<existing_data>
{existing_entities_and_relationships}
</existing_data>

<wrong_query>
{wrong_query}
</wrong_query>
"""

DEFINE_FORCED_RETRIEVE_QUERY_TEMPLATE = """
<task>
You are a problem solver using a NetworkX directed graph database as a knowledge graph to solve a given problem. Note that the graph may be incomplete.
</task>

<instructions>
Understand the initial problem, the initial problem nuances, *ALL the existing data* in the graph.
You have to solve the initial problem using the existing data currently in the graph by writing python code. If the existing data in the database is not enough, you can try and guess the remaining information. Return the Python code to retrieve the necessary data (utilizing ALL Python and NetworkX functionalities and the documentation below). Watch out for the correct syntax and semantics. Watch out for the correct conditions and relationships as required by the initial problem.
</instructions>

<code_documentation>
When writing python and NetworkX code, note the following:
- The NetworkX package has been imported as nx.
- Assume that the graph has been initialized and is stored in the variable self.G. Do NOT make any changes to the graph, only query it. Do NOT add any new nodes or edges.
- If you need to access a property 'x' of a node with id = 'node_id', you do: `self.G.nodes['node_id']['x']`
- Store the result of your code in a variable called 'result'. You must define `result`.
- Correct Syntax and Semantics: Follow Python and NetworkX syntax and semantics accurately. Ensure to close all quotes and parenthesis. Ensure any variables you use have previously been defined.
</code_documentation>


<examples>

<example_retrieve_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
Existing Nodes: 
  Label: Author
 	  [{{id:A1, properties:{{'name': 'J.K. Rowling'}}}}, {{id:A2, properties:{{'name': 'George R.R. Martin'}}}}]
  Label: Book
 	  [{{id:B1, properties:{{'title': "Harry Potter and the Philosopher's Stone"}}}}, {{id:B2, properties:{{'title': 'Harry Potter and the Chamber of Secrets'}}}}, {{id:B3, properties:{{'title': 'A Game of Thrones'}}}}]
Existing Relationships: 
  Label: Wrote
    [{{source: {{id: A1}}, target: {{id: B1}}, properties: {{}}}}, {{source: {{id: A1}}, target: {{id: B2}}, properties: {{}}}}, {{source: {{id: A2}}, target: {{id: B3}}, properties: {{}}}}]
Solution:
query: '
author_id = "A1"  # J.K. Rowling's author_id
result = [self.G.nodes[edge[1]]['title'] for edge in self.G.edges if edge[0] == author_id]
'
</example_retrieve_1>
<example_retrieve_2>
Initial problem: List all colleagues of "Bob".
Existing Nodes:
	Label: Employee
 		[{{id:E1, properties:{{'name': 'Alice'}}}}, {{id:E2, properties:{{'name': 'Bob'}}}}, {{id:E3, properties:{{'name': 'Charlie'}}}}]
	Label: Department
 		[{{id:D1, properties:{{'name': 'HR'}}}}, {{id:D2, properties:{{'name': 'Engineering'}}}}]
Existing Relationships:
	Label: works_in
 		[{{source: {{id: E1}}, target: {{id: D1}}, properties: {{}}}}, {{source: {{id: E2}}, target: {{id: D1}}, properties: {{}}}}, {{source: {{id: E3}}, target: {{id: D2}}, properties: {{}}}}]
Solution: 
query: '
employee_id = "E2"  # Bob's employee id
department_id = None
for edge in self.G.edges: # search for Bob's department id
  if edge[0] == employee_id:
    department_id = edge[1]

# find all other employees in the same department, not including Bob
result = [self.G.nodes[edge[0]]['name'] for edge in self.G.edges if edge[1] == department_id and edge[0] != employee_id]
'
</example_retrieve_2>

</examples>

<initial_problem>
{initial_query}
</initial_problem>

<existing_data>
{existing_entities_and_relationships}
</existing_data>
"""

DEFINE_FORCED_SOLUTION_TEMPLATE = """
<task>
You are a problem solver using a NetworkX directed graph database as a knowledge graph to solve a given problem. Note that the graph may be incomplete.
</task>

<instructions>
Take a deep breath, understand the initial problem, the initial problem nuances, and *ALL the existing data* in the graph.
You have to solve the initial problem using the existing data currently in the graph, if the existing data in the graph is not enough, you can try and GUESS the remaining information. Return the final answer of the given problem.
</instructions>


<examples>

<example_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
Existing entities: Author: [{{name: "J.K. Rowling", author_id: "A1"}}, {{name: "George R.R. Martin", author_id: "A2"}}], Book: [{{title: "Harry Potter and the Philosopher's Stone", book_id: "B1"}}, {{title: "Harry Potter and the Chamber of Secrets", book_id: "B2"}}, {{title: "A Game of Thrones", book_id: "B3"}}]
Existing relationships: (A1)-[:WROTE]->(B1), (A1)-[:WROTE]->(B2), (A2)-[:WROTE]->(B3)
Solution:
"Harry Potter and the Philosopher's Stone, Harry Potter and the Chamber of Secrets, Harry Potter and the Prisoner of Azkaban, Harry Potter and the Goblet of Fire, Harry Potter and the Order of the Phoenix, Harry Potter and the Half-Blood Prince, Harry Potter and the Deathly Hallows, Fantastic Beasts & Where to Find Them, Quidditch Through the Ages, The Tales of Beedle the Bard, Harry Potter and the Cursed Child – Parts One and Two, Fantastic Beasts and Where To Find Them, Fantastic Beasts: The Crimes of Grindelwald, Fantastic Beasts: The Secrets of Dumbledore"
</example_1>
<example_2>
Initial problem: List all colleagues of "Bob".
Existing entities: Employee: [{{name: "Alice", employee_id: "E1"}}, {{name: "Bob", employee_id: "E2"}}, {{name: "Charlie", employee_id: "E3"}}], Department: [{{name: "HR", department_id: "D1"}}, {{name: "Engineering", department_id: "D2"}}]
Existing relationships: (E1)-[:WORKS_IN]->(D1), (E2)-[:WORKS_IN]->(D1), (E3)-[:WORKS_IN]->(D2)
Solution: 
query: "Alice"
</example_2>
</examples>

<initial_problem>
{initial_query}
</initial_problem>

<existing_data>
{existing_entities_and_relationships}
</existing_data>
"""

DEFINE_TOOL_CALLS_PROMPT_TEMPLATE = """
<task>
You are an information retriever tasked with populating a NetworkX directed graph database with the necessary information to solve the given initial problem.
</task>

<instructions>
To complete this task, carefully follow these steps:

1. **Understand Requirements**:
    - Comprehend the missing information needed to address the initial problem.
    - Leverage existing data in the graph and the initial problem description.
    - Familiarize yourself with the available tools, understanding their functionality, strengths, and weaknesses.
    - Know that you will need to call different tools to gather all information. All necessary information will rarely be found by one tool. Consider which call gets you CLOSER to the solution.

2. **Gather Information**:
    - Use **ONLY** the available tools to gather the missing information.
    - **Do not create or assume data**.
    - If the initial problem specifies a particular source, prioritize that source if available.
    - Integrate gathered information with existing data in the graph to find the solution to the initial problem. Only proceed to other sources if necessary.

3. **Detailed Usage**:
    - When using the tools, provide detailed information from the initial problem and existing data in the graph.
    - Focus the tools' usage to gather the missing information.
    - When passing arguments to a tool, highlight the specific information that is missing, if possible.
    - **Note**: The tools do **NOT** have access to the initial problem, the graph, or previous calls—only the given arguments.
    - Ensure your queries are detailed and specific, focusing on relevant information directly related to the task.
    - For example, instead of making a general query, specify the context and list of entities involved to obtain precise results.
    - 'run_python_code' tool is preferred over llm_query for mathematical and statistical calculations.

4. **Utilize Existing Data**:
    - Use existing data in the graph to inform your tool queries.
    - Avoid redundant data gathering by leveraging previously retrieved information before making new tool calls.

5. **Avoid Redundant Calls**:
    - **IMPORTANT**: Before proposing a tool call, **analyze the list of previous tool calls** in `<tool_calls_made>` to ensure that your proposed tool call is **not identical** to any previous call in terms of tool name and arguments.
    - **Do not** call the same tool with the same arguments as any previous call.
    - If you need to call the same tool again, ensure that the arguments are **significantly different** and necessary for obtaining new information.
    - If, after multiple calls to the same tool, you still do not get the necessary information, consider using a different tool, as there is a high chance that the tool does not have the required information.
    - There is no need to unzip the same directory multiple times, read the same file multiple times, or ask the same question about the same image; ensure each file is read at least once. Once you have extracted the information from a file, you do not need to extract it again; use the extracted information and call other tools if necessary.

6. **Ensure Uniqueness of Tool Calls**:
    - **Before proposing a tool call**, compare it with each previous tool call in `<tool_calls_made>` by checking both the tool name and the arguments.
    - **Example**:
        - Previous call: `{{ 'name': 'wikipedia_search', 'args': {{'article_name': 'OpenCV', 'information_to_retrieve': 'Details about contributors'}} }}`
        - New proposed call: `{{ 'name': 'wikipedia_search', 'args': {{'article_name': 'OpenCV', 'information_to_retrieve': 'Details about contributors'}} }}`
        - Since both the tool name and arguments are identical, **do not propose this call again**.
    - **If all possible tool calls have been made** and you still lack necessary information, consider reformulating your approach or using a different tool.

7. **Default Tool**:
    - **ALWAYS** choose a tool call to make.
    - If you don't think any tool is appropriate, use the **'llm_query'** as the default tool to gather information.
    - The 'llm_query' tool is versatile and can be used to gather any necessary information, holding equal priority with other available tools.
    - Be as specific as possible with the query that you will pass to the 'llm_query' tool; the query is the only source of information you can pass to the LLM.

8. **Do Not Hallucinate**:
    - **Do not invent information** that is not provided in the initial problem or the existing data.

</instructions>

<initial_problem>
{initial_query}
</initial_problem>

<existing_data>
{existing_entities_and_relationships}
</existing_data>

<missing_information>
{missing_information}
</missing_information>

<tool_calls_made>
Please review the following list of previous tool calls before proposing a new one:
{tool_calls_made}
</tool_calls_made>
"""

FIX_CODE_PROMPT_TEMPLATE = """
<task>
You are a Python expert, and you need to fix the syntax and semantic of a incorrect code that adds nodes and edges or queries a NetworkX graph.
</task>

<instructions>
Given the incorrect code, the error log, and the state of the graph:
1. Understand the source of the error (especially look out for wrongly escaped/not escaped characters). 
2. Ensure you are not using unnecessary string characters. Use correct NetworkX syntax. The graph is stored in the variable `self.G`
3. Correct the code.
4. Return the corrected code.
</instructions>

<wrong_coder>
{code_to_fix}
</wrong_coder>

<error_log>
{error_log}
</error_log>

<existing_entities_and_relationships>
{existing_entities_and_relationships}
</existing_entities_and_relationships>
"""