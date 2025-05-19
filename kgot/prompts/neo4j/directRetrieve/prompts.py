# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang

DEFINE_NEXT_STEP_PROMPT_TEMPLATE = """
<task>
You are a problem solver using a Neo4j database as a knowledge graph to solve a given problem. Note that the database may be incomplete.
</task>

<instructions>
Understand the initial problem, the initial problem nuances, *ALL the existing data* in the database and the tools already called.
Can you solve the initial problem using the existing data in the database?
- If you can solve the initial problem with the existing data currently in the database return the final answer and set the query_type to RETRIEVE. Retrieve only if the data is sufficient to solve the problem in a zero-shot manner.
- If the existing data is insufficient to solve the problem, return why you could not solve the initial problem and what is missing for you to solve it, and set query_type to INSERT.
- Remember that if you don't have ALL the information requested, but only partial (e.g. there are still some calculations needed), you should continue to INSERT more data.
</instructions>

<examples>

<examples_retrieve>
<example_retrieve_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
Existing entities: Author: [{{name: "J.K. Rowling", author_id: "A1"}}, {{name: "George R.R. Martin", author_id: "A2"}}], Book: [{{title: "Harry Potter and the Philosopher's Stone", book_id: "B1"}}, {{title: "Harry Potter and the Chamber of Secrets", book_id: "B2"}}, {{title: "A Game of Thrones", book_id: "B3"}}]
Existing relationships: (A1)-[:WROTE]->(B1), (A1)-[:WROTE]->(B2), (A2)-[:WROTE]->(B3)
Solution:
query: '
Harry Potter and the Philosopher's Stone, Harry Potter and the Chamber of Secrets
'
query_type: RETRIEVE
</example_retrieve_1>
<example_retrieve_2>
Initial problem: List all colleagues of "Bob".
Existing entities: Employee: [{{name: "Alice", employee_id: "E1"}}, {{name: "Bob", employee_id: "E2"}}, {{name: "Charlie", employee_id: "E3"}}], Department: [{{name: "HR", department_id: "D1"}}, {{name: "Engineering", department_id: "D2"}}]
Existing relationships: (E1)-[:WORKS_IN]->(D1), (E2)-[:WORKS_IN]->(D1), (E3)-[:WORKS_IN]->(D2)
Solution: 
query: '
Alice
'
query_type: RETRIEVE
</example_retrieve_2>
</examples_retrieve>

<examples_insert>
<example_insert_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
Existing entities: {{name: "George R.R. Martin", author_id: "A2"}}], Book: [{{title: "A Game of Thrones", book_id: "B3"}}]
Existing relationships: (A2)-[:WROTE]->(B3)
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

DEFINE_FORCED_SOLUTION_TEMPLATE = """
<task>
You are given a problem and a Neo4j DB content. You are an expert in solving problems.
</task>

<instructions>
Take a deep breath, understand the initial problem, the initial problem nuances, and *ALL the existing data* in the database.
You have to solve the initial problem using the existing data currently in the database, if the existing data in the database is not enough, you can try and GUESS the remaining information. Return the final answer of the given problem.
</instructions>

<examples>

<example_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
Existing entities: Author: [{{name: "J.K. Rowling", author_id: "A1"}}, {{name: "George R.R. Martin", author_id: "A2"}}], Book: [{{title: "Harry Potter and the Philosopher's Stone", book_id: "B1"}}, {{title: "Harry Potter and the Chamber of Secrets", book_id: "B2"}}, {{title: "A Game of Thrones", book_id: "B3"}}]
Existing relationships: (A1)-[:WROTE]->(B1), (A1)-[:WROTE]->(B2), (A2)-[:WROTE]->(B3)
Solution:
"Harry Potter and the Philosopher’s Stone, Harry Potter and the Chamber of Secrets, Harry Potter and the Prisoner of Azkaban, Harry Potter and the Goblet of Fire, Harry Potter and the Order of the Phoenix, Harry Potter and the Half-Blood Prince, Harry Potter and the Deathly Hallows, Fantastic Beasts & Where to Find Them, Quidditch Through the Ages, The Tales of Beedle the Bard, Harry Potter and the Cursed Child – Parts One and Two, Fantastic Beasts and Where To Find Them, Fantastic Beasts: The Crimes of Grindelwald, Fantastic Beasts: The Secrets of Dumbledore"
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