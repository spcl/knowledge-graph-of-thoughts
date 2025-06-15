# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang
#               Jón Gunnar Hannesson

from kgot.prompts.sparql.base_prompts import (
    DEFINE_SPARQL_QUERY_GIVEN_NEW_INFORMATION_PROMPT_TEMPLATE,
    DEFINE_MATH_TOOL_CALL_PROMPT_TEMPLATE,
    DEFINE_NEED_FOR_MATH_PROMPT_TEMPLATE,
    DEFINE_REASON_TO_INSERT_PROMPT_TEMPLATE,
    DEFINE_RETRIEVE_QUERY_PROMPT_TEMPLATE,
    DEFINE_TOOL_CALLS_PROMPT_TEMPLATE,
    FIX_SPARQL_PROMPT_TEMPLATE,
    PARSE_FINAL_SOLUTION_WITH_LLM_PROMPT_TEMPLATE,
    PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE,
)

DEFINE_NEXT_STEP_PROMPT_TEMPLATE = """
<task>
You are a problem solver using a RDF knowledge graph to solve a given problem. Note that the database may be incomplete.
</task>

<instructions>
Understand the initial problem, the initial problem nuances, *ALL the existing data* in the database and the tools already called.
Can you solve the initial problem using the existing data in the database?
- If you can solve the initial problem with the existing data currently in the database by using a standard SPARQL 1.1 query, return the SPARQL 1.1 query to retrieve the necessary data (utilizing ONLY standard SPARQL 1.1 and RDF4J functionality) and set the query_type to RETRIEVE. Watch out for the correct syntax and semantics. Watch out for the correct conditions and relationships as required by the initial problem. Retrieve ONLY if the database contains the answer to the problem.
- If the existing data is insufficient to solve the problem, return why you could not solve the initial problem and what is missing for you to solve it, and set query_type to INSERT.
- Remember that if the database *does not contain the answer*, but only partial (e.g. there are still some calculations needed), you should continue to INSERT more data.
</instructions>

<examples>

<examples_retrieve>
<example_retrieve_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
This is the current state of the RDF database:
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:ex="http://example.org/">

  <rdf:Description rdf:about="http://example.org/A1">
    <rdf:type rdf:resource="http://example.org/Author"/>
    <ex:name>J.K. Rowling</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A2">
    <rdf:type rdf:resource="http://example.org/Author"/>
    <ex:name>George R.R. Martin</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B1">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>Harry Potter and the Philosopher's Stone</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B2">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>Harry Potter and the Chamber of Secrets</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B3">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>A Game of Thrones</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A1">
    <ex:wrote rdf:resource="http://example.org/B1"/>
    <ex:wrote rdf:resource="http://example.org/B2"/>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A2">
    <ex:wrote rdf:resource="http://example.org/B3"/>
  </rdf:Description>

</rdf:RDF>
Solution:
query: '
PREFIX ex: <http://example.org/>

SELECT ?book_title
WHERE {{
  ?book ex:title ?book_title .
  ?author ex:name "J.K. Rowling" .
  ?author ex:wrote ?book .
}}
'
query_type: RETRIEVE
</example_retrieve_1>
<example_retrieve_2>
Initial problem: List all colleagues of "Bob".
This is the current state of the RDF database:
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:ex="http://example.org/">

  <rdf:Description rdf:about="http://example.org/E1">
    <rdf:type rdf:resource="http://example.org/Employee"/>
    <ex:name>Alice</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E2">
    <rdf:type rdf:resource="http://example.org/Employee"/>
    <ex:name>Bob</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E3">
    <rdf:type rdf:resource="http://example.org/Employee"/>
    <ex:name>Charlie</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/D1">
    <rdf:type rdf:resource="http://example.org/Department"/>
    <ex:name>HR</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/D2">
    <rdf:type rdf:resource="http://example.org/Department"/>
    <ex:name>Engineering</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E1">
    <ex:worksIn rdf:resource="http://example.org/D1"/>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E2">
    <ex:worksIn rdf:resource="http://example.org/D1"/>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E3">
    <ex:worksIn rdf:resource="http://example.org/D2"/>
  </rdf:Description>

</rdf:RDF>Solution: 
query: '
PREFIX ex: <http://example.org/>

SELECT ?colleague_name
WHERE {{
  ?bob a ex:Employee ;
       ex:name "Bob" ;
       ex:worksIn ?dept .
       
  ?colleague a ex:Employee ;
             ex:worksIn ?dept ;
             ex:name ?colleague_name .
  
  FILTER(?colleague_name != "Bob")
}}
'
query_type: RETRIEVE
</example_retrieve_2>
</examples_retrieve>

<examples_insert>
<example_insert_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
This is the current state of the RDF database:
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:ex="http://example.org/">

  <rdf:Description rdf:about="http://example.org/A1">
    <rdf:type rdf:resource="http://example.org/Author"/>
    <ex:name>George R.R. Martin</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B1">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>A Game of Thrones</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A1">
    <ex:wrote rdf:resource="http://example.org/B3"/>
  </rdf:Description>

</rdf:RDF>
Solution:
query: 'There are no books by "J.K. Rowling" in the current database, we need more data'
query_type: INSERT
</example_insert_1>
<example_insert_2>
Initial problem: List all colleagues of "Bob"
This is the current state of the RDF database:
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

DEFINE_REASON_TO_INSERT_PROMPT_TEMPLATE = DEFINE_REASON_TO_INSERT_PROMPT_TEMPLATE

DEFINE_RETRIEVE_QUERY_PROMPT_TEMPLATE = DEFINE_RETRIEVE_QUERY_PROMPT_TEMPLATE

DEFINE_FORCED_RETRIEVE_QUERY_TEMPLATE = """
<task>
You are a problem solver using a RDF knowledge graph to solve a given problem. Note that the database may be incomplete.
</task>

<instructions>
Understand the initial problem, the initial problem nuances, *ALL the existing data* in the database.
You have to solve the initial problem using the existing data currently in the database by using a stabdard SPARQL 1.1 query, if the existing data in the database is not enough, you can try and guess the remaining information. return the SPARQL query to retrieve the necessary data (utilizing ONLY standard SPARQL 1.1 and RDF4J functionalities). Watch out for the correct syntax and semantics. Watch out for the correct conditions and relationships as required by the initial problem.
</instructions>

<examples>

<example_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
This is the current state of the RDF database:
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:ex="http://example.org/">

  <rdf:Description rdf:about="http://example.org/A1">
    <rdf:type rdf:resource="http://example.org/Author"/>
    <ex:name>J.K. Rowling</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A2">
    <rdf:type rdf:resource="http://example.org/Author"/>
    <ex:name>George R.R. Martin</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B1">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>Harry Potter and the Philosopher's Stone</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B2">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>Harry Potter and the Chamber of Secrets</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B3">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>A Game of Thrones</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A1">
    <ex:wrote rdf:resource="http://example.org/B1"/>
    <ex:wrote rdf:resource="http://example.org/B2"/>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A2">
    <ex:wrote rdf:resource="http://example.org/B3"/>
  </rdf:Description>

</rdf:RDF>
Solution:
query: '
PREFIX ex: <http://example.org/>

SELECT ?book_title
WHERE {{
  ?book ex:title ?book_title .
  ?author ex:name "J.K. Rowling" .
  ?author ex:wrote ?book .
}}
'
query_type: RETRIEVE
</example_1>
<example_2>
Initial problem: List all colleagues of "Bob".
This is the current state of the RDF database:
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:ex="http://example.org/">

  <rdf:Description rdf:about="http://example.org/E1">
    <rdf:type rdf:resource="http://example.org/Employee"/>
    <ex:name>Alice</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E2">
    <rdf:type rdf:resource="http://example.org/Employee"/>
    <ex:name>Bob</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E3">
    <rdf:type rdf:resource="http://example.org/Employee"/>
    <ex:name>Charlie</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/D1">
    <rdf:type rdf:resource="http://example.org/Department"/>
    <ex:name>HR</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/D2">
    <rdf:type rdf:resource="http://example.org/Department"/>
    <ex:name>Engineering</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E1">
    <ex:worksIn rdf:resource="http://example.org/D1"/>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E2">
    <ex:worksIn rdf:resource="http://example.org/D1"/>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E3">
    <ex:worksIn rdf:resource="http://example.org/D2"/>
  </rdf:Description>

</rdf:RDF>Solution: 
query: '
PREFIX ex: <http://example.org/>

SELECT ?colleague_name
WHERE {{
  ?bob a ex:Employee ;
       ex:name "Bob" ;
       ex:worksIn ?dept .
       
  ?colleague a ex:Employee ;
             ex:worksIn ?dept ;
             ex:name ?colleague_name .
  
  FILTER(?colleague_name != "Bob")
}}
'
query_type: RETRIEVE
</example_2>

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
You are a problem solver using a RDF knowledge graph to solve a given problem. Note that the database may be incomplete.
</task>

<instructions>
Take a deep breath, understand the initial problem, the initial problem nuances, and *ALL the existing data* in the database.
You have to solve the initial problem using the existing data currently in the database, if the existing data in the database is not enough, you can try and GUESS the remaining information. Return the final answer of the given problem.
</instructions>

<examples>

<example_1>
Initial problem: Retrieve all books written by "J.K. Rowling".
This is the current state of the RDF database:
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:ex="http://example.org/">

  <rdf:Description rdf:about="http://example.org/A1">
    <rdf:type rdf:resource="http://example.org/Author"/>
    <ex:name>J.K. Rowling</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A2">
    <rdf:type rdf:resource="http://example.org/Author"/>
    <ex:name>George R.R. Martin</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B1">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>Harry Potter and the Philosopher's Stone</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B2">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>Harry Potter and the Chamber of Secrets</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/B3">
    <rdf:type rdf:resource="http://example.org/Book"/>
    <ex:title>A Game of Thrones</ex:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A1">
    <ex:wrote rdf:resource="http://example.org/B1"/>
    <ex:wrote rdf:resource="http://example.org/B2"/>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/A2">
    <ex:wrote rdf:resource="http://example.org/B3"/>
  </rdf:Description>

</rdf:RDF>
Solution:
"Harry Potter and the Philosopher’s Stone, Harry Potter and the Chamber of Secrets, Harry Potter and the Prisoner of Azkaban, Harry Potter and the Goblet of Fire, Harry Potter and the Order of the Phoenix, Harry Potter and the Half-Blood Prince, Harry Potter and the Deathly Hallows, Fantastic Beasts & Where to Find Them, Quidditch Through the Ages, The Tales of Beedle the Bard, Harry Potter and the Cursed Child – Parts One and Two, Fantastic Beasts and Where To Find Them, Fantastic Beasts: The Crimes of Grindelwald, Fantastic Beasts: The Secrets of Dumbledore"
</example_1>
<example_2>
Initial problem: List all colleagues of "Bob".
This is the current state of the RDF database:
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:ex="http://example.org/">

  <rdf:Description rdf:about="http://example.org/E1">
    <rdf:type rdf:resource="http://example.org/Employee"/>
    <ex:name>Alice</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E2">
    <rdf:type rdf:resource="http://example.org/Employee"/>
    <ex:name>Bob</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E3">
    <rdf:type rdf:resource="http://example.org/Employee"/>
    <ex:name>Charlie</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/D1">
    <rdf:type rdf:resource="http://example.org/Department"/>
    <ex:name>HR</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/D2">
    <rdf:type rdf:resource="http://example.org/Department"/>
    <ex:name>Engineering</ex:name>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E1">
    <ex:worksIn rdf:resource="http://example.org/D1"/>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E2">
    <ex:worksIn rdf:resource="http://example.org/D1"/>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/E3">
    <ex:worksIn rdf:resource="http://example.org/D2"/>
  </rdf:Description>

</rdf:RDF>Solution: 
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

DEFINE_SPARQL_QUERY_GIVEN_NEW_INFORMATION_PROMPT_TEMPLATE = DEFINE_SPARQL_QUERY_GIVEN_NEW_INFORMATION_PROMPT_TEMPLATE

DEFINE_TOOL_CALLS_PROMPT_TEMPLATE = DEFINE_TOOL_CALLS_PROMPT_TEMPLATE

DEFINE_MATH_TOOL_CALL_PROMPT_TEMPLATE = DEFINE_MATH_TOOL_CALL_PROMPT_TEMPLATE

PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE = PARSE_SOLUTION_WITH_LLM_PROMPT_TEMPLATE

DEFINE_NEED_FOR_MATH_PROMPT_TEMPLATE = DEFINE_NEED_FOR_MATH_PROMPT_TEMPLATE

PARSE_FINAL_SOLUTION_WITH_LLM_PROMPT_TEMPLATE = PARSE_FINAL_SOLUTION_WITH_LLM_PROMPT_TEMPLATE

FIX_SPARQL_PROMPT_TEMPLATE = FIX_SPARQL_PROMPT_TEMPLATE