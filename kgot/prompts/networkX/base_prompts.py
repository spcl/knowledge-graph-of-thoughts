# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang
# 
# Contributions: Diana Khimey

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

UPDATE_GRAPH_GIVEN_NEW_INFORMATION_PROMPT_TEMPLATE = """
<task>
You are a problem solver tasked with updating an incomplete NetworkX graph database used as a knowledge graph. You have just acquired new information that needs to be integrated into the database.
</task>

<instructions>
To update the NetworkX graph database with the newly acquired information, provide Python code that accurately adds or modify nodes, attributes, and relationships. Follow these guidelines:

0. Understand the Context: Familiarize yourself with the initial problem, including the expected database schema, existing data, missing information, and the new information provided.
1. *Use Provided New Information Only*: Do not invent nor assume information nor hallucinate; use only the provided new information. Assign meaningful values when setting attributes. Add ALL the new relevant information to address the initial problem or other new information that can get us closer to the solution (e.g. new file_paths of files we can use to retrieve more information). If no new nor relevant information is given, do NOT return any query. Do not add nodes and edges that contain query metadata, add only information retrieved by the query.
2. *No Calculations*: Do not perform any calculations using the provided values. If a situation requires calculations, simply add the raw numbers as attributes to the nodes and relationships in the database without computing totals, averages, or any other derived values. Add all the necessary raw numbers.
3. Avoid Duplicates: Ensure the queries consider existing data to prevent creating duplicate nodes and duplicate relationships (If something has to be counted multiple times, add a new attribute 'counter' and increment it).
4. Assume that the graph has been initialized and is stored in the variable self.G.
5. Correct Syntax and Semantics: Follow Python and NetworkX syntax and semantics accurately. Ensure to close all quotes and parenthesis. Ensure any variables you use have previously been defined.
6. When adding nodes, a node MUST have a field called 'label' that can be referenced later. The label should describe the type of object represented by the node. Always add this field to a node
6. When adding edges between entities, make sure that a node already exists for each entity or add a new node for the entity. Edges can only be added between existing nodes.
7. Use correct Relationships: A edge can only be between entities; neither attributes nor relationships can have relationships.
9. Escape Characters: Properly escape single and double quotes and parenthesis (of all types: '(', ')', '[', ']') in the code, considering it will be decoded from JSON first and then executed.

Example code structure:

A1_attrs = {{'label': 'Author', 'name': 'J.K. Rowling'}}
self.G.add_node('A1', **A1_attrs)

B1_attrs = {{'label': 'Book', 'title': "Harry Potter and the Philosopher's Stone"}}
self.G.add_node('B1', **B1_attrs)

edge_attrs = {{'relationship': 'wrote'}}
self.G.add_edge('A1', 'B1', **edge_attrs_1)

And it should be returned as a single string, without any unnecessary string characters:

A1_attrs = {{'label': 'Author', 'name': 'J.K. Rowling'}}
self.G.add_node('A1', **A1_attrs)

B1_attrs = {{'label': 'Book', 'title': "Harry Potter and the Philosopher's Stone"}}
self.G.add_node('B1', **B1_attrs)

edge_attrs = {{'relationship': 'wrote'}}
self.G.add_edge('A1', 'B1', **edge_attrs_1)

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

PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE_DEFAULT = """
<task>
You are a linguistic expert and a skilled problem solver. Your task is to combine partial solutions from a graph database and format them according to the initial problem statement.
</task>

<instructions>
1. Understand the initial problem, the problem nuances, the desired output, and the desired output format.
2. Review the provided partial solution.
3. Integrate and elaborate on the various pieces of information from the partial solution to produce a complete solution to the initial problem. Do not invent any new information.
4. If the initial problem does not specify a format your final answer should be a concise but well structured paragraph.
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
<example_3>
Initial problem: What is the probability of rolling two sixes with two six-sided dice? Give me the full solution with all the steps.
Given partial solution:
1. We roll two six-sided dice.
2. There are 36 possible outcomes.
3. Only one outcome is made of two sixes.

Solution: The probability of rolling two sixes with two six-sided dice is 1/36. Since there are 36 possible outcomes when rolling two dice, and only one of those outcomes is a pair of sixes, the probability is calculated as follows: P(two sixes) = Number of favorable outcomes / Total number of outcomes = 1 / 36.
</example_3>
</examples>

<initial_problem>
{initial_query}
</initial_problem>

<given_partial_solution>
{partial_solution}
</given_partial_solution>
"""

PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE_GAIA_VERSION = """
<task>
You are a formatter and extractor. Your task is to combine partial solution from a graph database and format them according to the initial problem statement.
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
You are a linguistic expert and a skilled problem solver. Your role is to select the best final solution from a list of options based on an initial problem and a partial solution provided. Typically, the problem can be solved by picking the most commonly occurring answer in the list of solutions.
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

def get_formatter(gaia_formatter: bool) -> str:
    """
    This function is used to enable the gaia formatter.
    """
    if gaia_formatter:
        return PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE_GAIA_VERSION
    else:
        return PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE_DEFAULT