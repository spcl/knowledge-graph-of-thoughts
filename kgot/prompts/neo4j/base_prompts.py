# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang

DEFINE_REASON_TO_INSERT_PROMPT_TEMPLATE = """
<task>
You are a logic expert, your task is to determine why a given problem cannot be solved using the existing data in a Neo4j database.
</task>

<instructions>
You are provided with a list of reasons. Your job is to combine these reasons into a single, coherent paragraph, ensuring that there are no duplicates.
- Carefully review and understand each reason provided.
- Synthesize the reasons into one unified text.
</instructions>

<list_of_reasons>
{list_of_reasons}
</list_of_reasons>
"""

DEFINE_RETRIEVE_QUERY_PROMPT_TEMPLATE = """
<task>
You are a problem solver expert in using a Neo4j database as a knowledge graph. Your task is to solve a given problem by generating a correct Cypher query. You will be provided with the initial problem, existing data in the database, and a previous incorrect Cypher query that returned an empty result. Your goal is to create a new Cypher query that returns the correct results.
</task>

<instructions>
1. Understand the initial problem, the problem nuances and the existing data in the database.
2. Analyze the provided incorrect query to identify why it returned an empty result.
3. Write a new Cypher query to retrieve the necessary data from the database to solve the initial problem. You can use ALL Cypher/Neo4j functionalities.
4. Ensure the new query is accurate and follows correct Cypher syntax and semantics.
</instructions>

<examples>

<example_retrieve_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
Existing entities: Author: [{{name: "J.K. Rowling", author_id: "A1"}}, {{name: "George R.R. Martin", author_id: "A2"}}], Book: [{{title: "Harry Potter and the Philosopher's Stone", book_id: "B1"}}, {{title: "Harry Potter and the Chamber of Secrets", book_id: "B2"}}, {{title: "A Game of Thrones", book_id: "B3"}}]
Existing relationships: (A1)-[:WROTE]->(B1), (A1)-[:WROTE]->(B2), (A2)-[:WROTE]->(B3)
Incorrect query:
MATCH (b:Book)-[:WROTE]->(a:Author {{name: "J.K. Rowling"}})
RETURN b.title AS book_title
Solution:
query: 
MATCH (a:Author {{name: "J.K. Rowling"}})-[:WROTE]->(b:Book)
RETURN b.title AS book_title
</example_retrieve_1>

<example_retrieve_2>
Initial problem: List all colleagues of "Bob".
Existing entities: Employee: [{{name: "Alice", employee_id: "E1"}}, {{name: "Bob", employee_id: "E2"}}, {{name: "Charlie", employee_id: "E3"}}], Department: [{{name: "HR", department_id: "D1"}}, {{name: "Engineering", department_id: "D2"}}]
Existing relationships: (E1)-[:WORKS_IN]->(D1), (E2)-[:WORKS_IN]->(D1), (E3)-[:WORKS_IN]->(D2)
Incorrect query:
MATCH (e:Employee {{name: "Bob"}})-[:WORKS_IN]->(d:Department)<-[:WORKS_IN]-(colleague:Employee)
WHERE colleague.name <> "Alice"
RETURN colleague.name AS colleague_name
Solution: 
query:
MATCH (e:Employee {{name: "Bob"}})-[:WORKS_IN]->(d:Department)<-[:WORKS_IN]-(colleague:Employee)
WHERE colleague.name <> "Bob"
RETURN colleague.name AS colleague_name
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


DEFINE_CYPHER_QUERY_GIVEN_NEW_INFORMATION_PROMPT_TEMPLATE = """
<task>
You are a problem solver tasked with updating an incomplete Neo4j database used as a knowledge graph. You have just acquired new information that needs to be integrated into the database.
</task>

<instructions>
To update the Neo4j database with the newly acquired information, provide Cypher queries that accurately add or modify nodes, attributes, and relationships. Follow these guidelines:

0. Understand the Context: Familiarize yourself with the initial problem, including the expected database schema, existing data, missing information, and the new information provided.
1. *Use Provided New Information Only*: Do not invent nor assume information nor hallucinate; use only the provided new information. Assign meaningful values when setting attributes. Add ALL the new relevant information to address the initial problem or other new information that can get us closer to the solution (e.g. new file_paths of files we can use to retrieve more information). If no new nor relevant information is given, do NOT return any query.
2. *No Calculations*: Do not perform any calculations using the provided values. If a situation requires calculations, simply add the raw numbers as attributes to the nodes and relationships in the database without computing totals, averages, or any other derived values. Add all the necessary raw numbers.
3. Avoid Duplicates: Ensure the queries consider existing data to prevent creating duplicate nodes and duplicate relationships (If something has to be counted multiple times, add a new attribute 'counter' and increment it).
4. Combine Operations with WITH Clauses: Use aliases and the WITH clause appropriately to combine sequential operations and maintain relationships, avoiding ghost nodes. Ensure every WITH clause is BOTH preceded and followed by another statement. A query CANNOT start with a WITH clause.
5. Group Related Queries: Write related operations as a single continuous query without using commas or new lines to separate them.
6. Omit RETURN Statements: Do not include RETURN statements.
7. Omit ID usage: Do not use id or neo4j_id properties to filter or match nodes.
8. Merge Existing Nodes: When merging nodes, always MATCH them with existing ones if they already exist.
9. Correct Syntax and Semantics: Follow Cypher syntax and semantics accurately.
10. Use correct Relationships: A relationship can only be between entities; neither attributes nor relationships can have relationships.
11. Escape Characters: Properly escape single and double quotes in the Cypher queries, considering they will be decoded from JSON first and then from Neo4j.

Example Cypher query structure:

MERGE (n:Label {{property: 'value'}})
WITH n
MERGE (m:OtherLabel {{property: 'value'}})
WITH n, m
CREATE (n)-[:RELATIONSHIP]->(m)

And it should be returned as a SINGLE query as:
MERGE (n:Label {{property: 'value'}}) WITH n MERGE (m:OtherLabel {{property: 'value'}}) WITH n, m CREATE (n)-[:RELATIONSHIP]->(m)

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

<new_information>
{new_information}
</new_information>
"""

DEFINE_TOOL_CALLS_PROMPT_TEMPLATE = """
<task>
You are an information retriever tasked with populating a Neo4j database with the necessary information to solve the given initial problem.
</task>

<instructions>
To complete this task, carefully follow these steps:

1. **Understand Requirements**:
    - Comprehend the missing information needed to address the initial problem.
    - Leverage existing data in the database and the initial problem description.
    - Familiarize yourself with the available tools, understanding their functionality, strengths, and weaknesses.

2. **Gather Information**:
    - Use **ONLY** the available tools to gather the missing information.
    - **Do not create or assume data**.
    - If the initial problem specifies a particular source, prioritize that source if available.
    - Integrate gathered information with existing data in the database to find the solution to the initial problem. Only proceed to other sources if necessary.

3. **Detailed Usage**:
    - When using the tools, provide detailed information from the initial problem and existing data in the database.
    - Focus the tools' usage to gather the missing information.
    - When passing arguments to a tool, highlight the specific information that is missing, if possible.
    - **Note**: The tools do **NOT** have access to the initial problem, the database, or previous calls—only the given arguments.
    - Ensure your queries are detailed and specific, focusing on relevant information directly related to the task.
    - For example, instead of making a general query, specify the context and list of entities involved to obtain precise results.
    - 'run_python_code' tool is preferred over llm_query for mathematical and statistical calculations.

4. **Utilize Existing Data**:
    - Use existing data in the database to inform your tool queries.
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

DEFINE_MATH_TOOL_CALL_PROMPT_TEMPLATE = """
<task>
You are a math and python expert tasked with solving a mathematical problem.
</task>

<instructions>
To complete this task, follow these steps:

1. **Understand the Problem**:
    - Carefully read and understand the initial problem and the partial solution.
    - Elaborate on any mathematical calculations from the partial solution that are required to solve the initial problem.

2. **Perform Calculations**:
    - Use the run_python_code Tool to perform any necessary mathematical calculations.
    - Craft Python code that accurately calculates the required values based on the partial solution and the initial problem.
    - Remember to add print statements to display the reasoning behind the calculations.
    - **ALWAYS** add print statement for the final answer.

4. **Do Not Hallucinate**:
    - **Do not invent information** that is not provided in the initial problem or the partial solution.
    - **Do not perform calculations manually**; use the run_python_code Tool for all mathematical operations.

</instructions>

<initial_problem>
{initial_query}
</initial_problem>

<partial_solution>
{current_solution}
</partial_solution>
"""

PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE = """
<task>
You are a formatter and extractor. Your task is to combine partial solution from a database and format them according to the initial problem statement.
</task>

<instructions>
1. Understand the initial problem, the problem nuances, the desired output, and the desired output format.
2. Review the provided partial solution.
3. Integrate and elaborate on the various pieces of information from the partial solution to produce a complete solution to the initial problem. Do not invent any new information.
4. Your final answer should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.
5. ADDITIONALLY, your final answer MUST adhere to any formatting instructions specified in the original question (e.g., alphabetization, sequencing, units, rounding, decimal places, etc.)
6. If you are asked for a number, express it numerically (i.e., with digits rather than words), don't use commas, do not round the number unless directly specified, and DO NOT INCLUDE UNITS such as $ or USD or percent signs unless specified otherwise.
7. If you are asked for a string, don't use articles or abbreviations (e.g. for cities), unless specified otherwise. Don't output any final sentence punctuation such as '.', '!', or '?'.
8. If you are asked for a comma separated list, apply the above rules depending on whether the elements are numbers or strings.
</instructions>

<examples>
<example_1>
Initial problem: What are the preferred ice cream flavors in the household? Sort the solution from most common to least common. Separate them using commas, and in case of a tie, sort alphabetically.
Given partial solution:
- Mom likes Cream
- Dad likes Chocolate
- Uncle likes Strawberry
- Auntie likes Strawberry
- Grandpa likes Pistachio
- Grandma likes Lemon

Solution: Strawberry, Chocolate, Cream, Lemon, Pistachio
Reasoning:
Strawberry is liked by 2 people, while the other flavors are each liked by 1 person. Therefore, Strawberry comes first, and the rest are sorted alphabetically.
</example_1>
<example_2>
Initial problem: What is the net profit for Q1 of the company? (Answer rounded to thousands of dollars)
Given partial solution:
1. Revenue:
   - January: $50000
   - February: $55000
   - March: $60000
2. Expenses:
   - January: $30000
   - February: $32000
   - March: $35000
3. Net Profit Calculation:
   - Net Profit = Revenue - Expenses

Solution: 68
Reasoning:
Using the formula Net Profit = Revenue - Expenses, the net profits for Q1 were:
- January: $20000
- February: $23000
- March: $25000

Total Net Profit for Q1: $68,000, rounded to 68 as per the requirement to round to thousands of dollars.
</example_2>
</examples>

<initial_problem>
{initial_query}
</initial_problem>

<given_partial_solution>
{partial_solution}
</given_partial_solution>
"""

DEFINE_NEED_FOR_MATH_PROMPT_TEMPLATE = """
<task>
You are an expert in identifying the need for mathematical or probabilistic calculations in problem-solving scenarios. Given an initial query and a partial solution, your task is to determine whether the partial solution requires further mathematical or probabilistic calculations to arrive at a complete solution. You will return a boolean value: True if additional calculations are needed and False if they are not.
</task>

<instructions>
- Analyze the initial query and the provided partial solution.
- Identify any elements in the query and partial solution that suggest the further need for numerical analysis, calculations, or probabilistic reasoning.
- Consider if the partial solution includes all necessary numerical results or if there are unresolved numerical aspects.
- Return true if the completion of the solution requires more calculations, otherwise return false.
- Focus on the necessity for calculations rather than the nature of the math or probability involved.
</instructions>

<examples>
<examples>
<example_1>
Input:
{{
  "initial_query": "Calculate the total cost after a 20% discount on a $100 item.",
  "partial_solution": "'costs': 100, 'discount_percentage': 20"
}}
Output: true
Explanation: The partial solution identifies the discount percentage but does not calculate the discounted amount.
</example_1>

<example_2>
Input:
{{
  "initial_query": "What is the area of a triangle with a base of 5 cm and a height of 10 cm?",
  "partial_solution": "'base': 5, 'height': 10"
}}
Output: true
Explanation: The partial solution provides the necessary dimensions but does not calculate the area.
</example_2>

<example_3>
Input:
{{
  "initial_query": "How many people lived in Switzerland in 2022?",
  "partial_solution": "population: 8,766 million"
}}
Output: false
Explanation: The partial solution already contains that the population of Switzerland in 2022 was of 8,766 million people.
</example_3>

<example_3>
Input:
{{
  "initial_query": "What is the probability of rolling at two six with two six-sided dice?",
  "partial_solution": "We roll two six-sided dice. There are 36 possible outcomes. and only one is made by two six"
}}
Output: false
Explanation: The partial solution already contains that the probability is 1/36.
</example_3>

<example_4>
Input:
{{
  "initial_query": "List the steps to set up a new email account.",
  "partial_solution": "Go to the website, click on 'Create an account', fill out the form, and submit."
}}
Output: false
Explanation: The task is procedural and does not require mathematical calculations.
</example_4>

<example_5>
Input:
{{
  "initial_query": "Explain the causes of World War I.",
  "partial_solution": "World War I was caused by ..."
}}
Output: false
Explanation: The query is historical and explanatory, with no need for mathematical calculations.
</example_5>
</examples>

<initial_problem>
{initial_query}
</initial_problem>

<partial_solution>
{partial_solution}
</partial_solution>
"""

PARSE_FINAL_SOLUTION_WITH_LLM_PROMPT_TEMPLATE = """
<task>
You are a linguistic expert and a skilled problem solver. Your role is to select the best final solution from a list of options based on an initial problem and a partial solution provided.
</task>

<instructions>
1. Analyze the initial problem, its nuances, and the desired output format.
2. Review the partial solutions and the list of final formatted solutions.
3. Choose the most appropriate final solution.
</instructions>

<examples>
<example_1>
Initial problem: What is the preferred ice cream flavor in the household? Sort the solution from most common to least common. Separate them using commas, and in case of a tie, sort alphabetically.
Partial solution:
- Mom likes Cream
- Dad likes Chocolate
- Uncle likes Strawberry
- Auntie likes Strawberry
- Grandpa likes Pistachio
- Grandma likes Lemon

List of final solutions:
solution 1: Strawberry, Chocolate, Cream, Lemon, Pistachio
solution 2: Strawberry, Cream, Chocolate, Lemon, Pistachio
solution 3: Strawberry, Chocolate, Cream, Lemon, Pistachio

Reasoning:
The correct solution is "Strawberry, Chocolate, Cream, Lemon, Pistachio" because it aligns with the requirement to list flavors from most to least common, resolving ties alphabetically. While solution 2 is not alphabetically sorted.
</example_1>

<example_2>
Initial problem: What is the net profit for Q1 of the company? (Answer rounded to thousands of dollars)
Partial solutions:
1. Revenue:
   - January: $50000
   - February: $55000
   - March: $60000
2. Expenses:
   - January: $30000
   - February: $32000
   - March: $35000
3. Net Profit Calculation:
   - Net Profit = Revenue - Expenses

List of final solutions: 
solution 1: 50
solution 2: 100
solution 3: 68

Reasoning:
Using the formula Net Profit = Revenue - Expenses, the net profits for Q1 were:
- January: $20000
- February: $23000
- March: $25000
Total Net Profit for Q1: $68,000, rounded to 68 as per the requirement to round to thousands of dollars.
</example_2>
</examples>

<initial_problem>
{initial_query}
</initial_problem>

<partial_solution>
{partial_solution}
</partial_solution>

<list_final_solutions>
{list_final_solutions}
</list_final_solutions>
"""

FIX_CYPHER_PROMPT_TEMPLATE = """
<task>
You are a Cypher expert, and you need to fix the syntax and semantic of a given incorrect Cypher query.
</task>

<instructions>
Given the incorrect Cypher and the error log:
1. Understand the source of the error (especially look out for wrongly escaped/not escaped characters).
2. Correct the Cypher query
3. Return the corrected Cypher query.
</instructions>

<wrong_cypher>
{cypher_to_fix}
</wrong_cypher>

<error_log>
{error_log}
</error_log>
"""