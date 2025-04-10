# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#
# Contributions: You Wu

QUERY_TO_CHOOSE_WIKIPEDIA_ARTICLES = """
<task>
Given a list of articles and relative summary, you must choose the 3 most relevant articles based on the correlation with the search query.
</task>

<instructions>
If you think an article may contain the information related to the search query, you should choose it. Remember that articles summary may not contain all the information. 

<rules>
 - You must output a list of chosen articles titles.
 - You must output exactly 3 articles (if present).
</rules>

<examples>
<example>
Input:
{{    
    "articles": [
        "Article 1",
        "Article 2",
        "Article 3",
        "Article 4",
        "Article 5"
    ],
    "query": "Search query"
}}

Output:
{{
    "articles": [
        "Article 1",
        "Article 3",
        "Article 5"
    ]
}}
</example>
<example>
Input:
{{
    "articles": [
        "Article 1",
        "Article 2"
    ],
    "query": "Search query"
}}

Output:
{{
    "articles":
    [
        "Article 1",
        "Article 2"
    ]
}}
</example>
</examples>
</instructions>

<articles_and_summary>
{articles_and_summary}
</articles_and_summary>

<search_query>
{search_query}
</search_query>
"""

QUERY_FOR_WIKIPEDIA_INFO_EXTRACTION = """
<task>
You are tasked with extracting information from Wikipedia articles. Given two search queries, one specific and a more general one, a Wikipedia article content, and a list of tables, you must extract information based on the two search query.
</task>

<instructions>
Given a search query, a Wikipedia article content, and a list of tables, extract information based on the search query.
The Wikipedia article content is the full text of the article. The tables are a list of tables found in the article. Each table has a header, a caption, and the table data.
</instructions>

<rules>
    - You must output all the information inside the Wikipedia article relative to the query.
    - It is recommended to give more information than less. If you are unsure about the relevance of a piece of information, include it.
    - Be aware that some information about what is searched may be present in different locations.
    - You can use the full text of the article and the tables to extract the information.
    - Do not invent or assume information, you should only extract the information that is present in the article.
</rules>

<examples>
<example>
Input:
{{
    "full_page_text": "Full text of the Wikipedia article",
    "tables": [
        {{
            "header": "Header of the table",
            "caption": "Caption of the table",
            "table": [
                ["Row 1, Column 1", "Row 1, Column 2"],
                ["Row 2, Column 1", "Row 2, Column 2"]
            ]
        }}
    ],
    "query": "Search query"
}}

Output:
{{
    "relevant_information": "All the relevant information extracted from the Wikipedia article"
}}
</example>
</examples>


<full_page_text>
{full_page_text}
</full_page_text>


<tables>
{tables}
</tables>


<search_query_specific>
{query_specific}
</search_query_specific>

<search_query_general>
{query_general}
</search_query_general>
"""