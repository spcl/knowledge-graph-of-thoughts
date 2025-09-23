# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Lorenzo Paleari
# 
# Contributions: Andrea Jiang
#                Jón Gunnar Hannesson

import logging
import re
import traceback
import warnings
from io import StringIO
from pprint import pformat
from typing import Any, Dict, List, Tuple, Type

import pandas as pd
import pywikibot
import pywikibot.config
import requests
import wikipedia
from bs4 import BeautifulSoup
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from transformers.agents import Tool

from kgot.prompts.tools.tools_v2_3 import (
    QUERY_FOR_WIKIPEDIA_INFO_EXTRACTION,
    QUERY_TO_CHOOSE_WIKIPEDIA_ARTICLES,
)
from kgot.utils import UsageStatistics, llm_utils
from kgot.utils.llm_utils import invoke_with_retry
from kgot.utils.log_and_statistics import collect_stats

logger = logging.getLogger("Controller.WikipediaTool")

pywikibot.config.maxlag = None


class WikipediaTool:
    def __init__(self, model_name, temperature, usage_statistics: UsageStatistics,
                 language: str = 'en'):
        
        wikipedia.set_lang(language)
        self.llm = None
        self.usage_statistics = usage_statistics
        self.model_name = model_name
        self.temperature = temperature

    def search(self, query: str, top_k: int = 10) -> Dict[str, str]:
        search_results = wikipedia.search(query, results=top_k)

        page_summaries = {}
        
        for page_title in search_results:
            try:
                page_summaries[page_title] = wikipedia.summary(page_title, auto_suggest=False)
            except wikipedia.DisambiguationError as e:
                page_summaries[page_title] = f"This page is a disambiguation of the term {page_title}.\n{e}"
            except Exception as e:  # Unlikely, but if the given page is not retrievable skip to next page
                logger.info(f"Error for {page_title}: {e}")
                continue

        print(f"Search results: {search_results}")

        return page_summaries

    @collect_stats("WikipediaTool.ask_LLM_which_article_to_explore")
    def ask_LLM_which_article_to_explore(self, search_results: Dict[str, str], query: str) -> List[str]:
        # Ask the LLM which article to explore
        if not search_results:
            return [], False

        class QueryAnswer(BaseModel):
            chosen_articles: List[str] = Field(description="List of chosen articles titles")

        prompt_template = PromptTemplate(
            input_variables=["articles_and_summary", "search_query"],
            template=QUERY_TO_CHOOSE_WIKIPEDIA_ARTICLES,
        )

        chain = self.llm.with_structured_output(QueryAnswer, method="json_schema")
        
        complete_template = prompt_template.invoke({"articles_and_summary": search_results,
                                                    "search_query": query})

        search_results = [{"title": title, "summary": summary} for title, summary in search_results.items()]
        response = invoke_with_retry(chain, complete_template)

        logger.info(f"Articles to search response: {pformat(response, width=160)}")

        return response.chosen_articles

    def _clean_parse(self, text: str) -> Tuple[str, List[str]]:
        for line in text.split('\n'):
            if line.startswith("[[File:"):
                text = text.replace(line, "''"+line[2:-2]+"''")

        def replace_match(match):
            content = match.group(1)
            # Split by '|' and take the last part
            return content.split('|')[-1]

        # Regular expression to find [[...]]
        pattern = re.compile(r'\[\[(.*?)\]\]')

        # Replace each match using the replace_match function
        cleaned_text = re.sub(pattern, replace_match, text)

        # Remove wiki-table
        while "{|" in cleaned_text:
            table_start = cleaned_text.find("{|")
            table_end = cleaned_text.find("|}", table_start) + 2
            table = cleaned_text[table_start:table_end]
            cleaned_text = cleaned_text.replace(table, "")

        # Extract tables
        tables = []
        for line in cleaned_text.split('\n'):
            if line.startswith("{{") and line.endswith("}}") and "|" not in line:
                tables.append(line.replace("{{", "").replace("}}", "").replace(" ", "_"))
        tables = list(dict.fromkeys(tables))

        # Cleaning of formatting options
        tables_copy = [item.lower() for item in tables]
        for item in ["clear", "clear_left", "clear_right", "reflist", "clear2", "break", "float", "stack", "break_lines", "paragraph_break", "align", "float_begin", "float_end", "commons_category", "attached_kml", "stack_begin", "stack_end", "multiple_image", "superimpose", "superimpose2", "center", "right", "left", "justify", "image_frame", "center_block"]:
            if item in tables_copy:
                tables.pop(tables_copy.index(item))
                tables_copy.remove(item)

        cleaned_text = cleaned_text[0:cleaned_text.find("==External links==")]
        cleaned_text = cleaned_text[0:cleaned_text.find("==References==")]
        return cleaned_text, tables

    def _parse_table(self, page_html: str, classes_to_exclude: List[str] = None, filter_table: List[str] = None) -> str:
        # Filtering of the page content to extract only the top level tables.
        soup = BeautifulSoup(page_html, "html.parser")
        div = soup.find('div', {'class': 'documentation'})
        if div:
            page_html = page_html.replace(str(div), "")

        soup = BeautifulSoup(page_html, "html.parser")
        div = soup.find('div', {'id': 'mw-content-text'})
        new_html = str(div)

        soup = BeautifulSoup(new_html, "html.parser")
        if not filter_table:
            # If filter_table is empty, find all tables without filtering by class
            parsed_tables = soup.find_all('table')
        else:
            # If filter_table is not empty, find tables with any of the classes in filter_table
            parsed_tables = soup.find_all('table', class_=lambda x: x and any(cls in filter_table for cls in x.split()))

        if classes_to_exclude:
            def should_exclude(table):
                for class_name in table.get("class", []):
                    if any(excluded in class_name for excluded in classes_to_exclude):
                        return True
                return False
            parsed_tables = [table for table in parsed_tables if not should_exclude(table)]

        # Filter out nested tables
        def remove_substrings(strings: List[str]) -> List[str]:
            result = []

            for i, string in enumerate(strings):
                clean = True
                for j, other_string in enumerate(strings):
                    if i != j and str(string) in str(other_string):
                        clean = False
                        break
                if clean:
                    result.append(string)

            return result

        def adjust_nested_tables(table):
            child_tables = []
            for i, child in enumerate(table.find_all('table')):
                # Append the child table to the list
                child_tables.append(child)

                # Create a placeholder string
                placeholder = f"Sub-table {i + 1}"

                # Replace the child table with the placeholder string
                child.replace_with(placeholder)

            table_list = [table]
            table_list.extend(child_tables)
            return table_list

        parsed_tables = remove_substrings(parsed_tables)

        table_data = ""
        for parse_table in parsed_tables:
            tables = adjust_nested_tables(parse_table)
            for i, table in enumerate(tables):
                try:
                    table_str = StringIO(str(table))
                    dfs = pd.read_html(table_str)
                    df = pd.DataFrame(dfs[0])

                    table_data += "<table>\n" + df.to_markdown() if i == 0 else f"\n\nSub-table {i}\n" + df.to_markdown() if i != len(tables) - 1 else f"\n\nSub-table {i}\n" + df.to_markdown() + "\n</table>\n\n\n"
                except Exception:
                    logger.info(f"Error parsing table: {traceback.format_exc()}")
                    print("Error extracting table, retrying...")
                    try:
                        table_tmp = []
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all('td')
                            table_tmp.append([cell.text.strip() for cell in cells])
                        table_tmp = pd.DataFrame(table_tmp)
                        table_data += "<table>\n" + table_tmp.to_markdown() if i == 0 else f"\n\nSub-table {i}\n" + table_tmp.to_markdown() if i != len(tables) - 1 else f"\n\nSub-table {i}\n" + table_tmp.to_markdown() + "\n</table>\n\n\n"
                    except Exception:
                        logger.info(f"Error parsing table (2): {traceback.format_exc()}")
                        print("Error extracting table, using raw html table")
                        table_data.append(table)
                    continue

        return table_data

    def _parse_table_with_history(self, table_titles: List[str], date: str) -> str:
        table_data = ""
        site = pywikibot.Site('en', 'wikipedia')

        for title in table_titles:
            try:
                page = pywikibot.Page(site, f"Template:{title}")

                stop = False
                while not stop:
                    try:
                        new_page = page.getRedirectTarget()
                        page = new_page
                    except Exception:
                        stop = True
                        continue

                revisions = page.getVersionHistoryTable()
                oldid_list = self._get_revisions_id(revisions, date)

                # Check validity
                curr_old_id = 0
                for i, oldid in enumerate(oldid_list):
                    try:
                        curr_old_id = oldid
                        page.getOldVersion(oldid)
                        break
                    except Exception:
                        print(f"Error getting old version: {traceback.format_exc()}")
                        if i == len(oldid_list) - 1:
                            print("No valid old version found. Using the current version.")
                            page = page.get()
                        continue

                print(f"Table: {title}, Oldid: {curr_old_id}")

                page_html = requests.get(f'https://en.wikipedia.org/w/index.php?title=Template:{title}&oldid={curr_old_id}').text

                table_data += self._parse_table(page_html, filter_table=["nowraplinks", "toccolours"])

            except Exception:
                logger.info(f"Table do not exist! {traceback.format_exc()}")
                print("Table do not exist! Continuing...")
                continue

        return table_data

    def _get_revisions_id(self, revisions: str, date: str) -> List[int]:
        lines = revisions.strip().split('\n')
        columns = []
        rows = []
        for line in lines:
            if line.startswith('!'):
                columns = line[1:].strip().split(' || ')
            elif line.startswith('|') and not line.startswith('|-'):
                row = line[1:].strip().split(' || ')
                rows.append(row)

        # Create DataFrame from the extracted data
        df = pd.DataFrame(rows, columns=columns)

        # Get the revision id for the given date
        oldid_list = []
        date_parsed = pd.to_datetime(date, format='%m-%d-%Y')
        df['date/time'] = pd.to_datetime(df['date/time'], format='%Y-%m-%dT%H:%M:%SZ', errors='coerce')
        df_filtered = df[df['date/time'] < date_parsed]
        df_sorted = df_filtered.sort_values(by='date/time', ascending=False)
        oldid_list.extend([int(id) for id in df_sorted['oldid'].dropna().tolist()])

        return oldid_list

    @collect_stats("WikipediaTool.get_page_content")
    def get_page_content(self, page_title: str, query: str, original_query: str, date: str) -> str:
        page = None
        if date == "cur":
            try:
                page = wikipedia.page(page_title, auto_suggest=False)  # Get the page without tables / images
                page = page.content
            except wikipedia.DisambiguationError as e:
                page =  f"This page is a disambiguation of the term {page_title}.\n{e}"
            # Find all the tables
            try:
                page_html = requests.get(f'https://en.wikipedia.org/w/index.php?title={page_title}').text
                table_data = self._parse_table(page_html)
            except Exception:
                logger.info(f"Error for {page_title}, continuing...: {traceback.format_exc()}")
                return f"Error for {page_title}, skipping..."
        else:
            site = pywikibot.Site('en', 'wikipedia')
            page = pywikibot.Page(site, page_title)
            stop = False
            while not stop:
                try:
                    new_page = page.getRedirectTarget()
                    page = new_page
                except Exception:
                    stop = True
                    continue

            revisions = page.getVersionHistoryTable()
            oldid_list = self._get_revisions_id(revisions, date)

            if len(oldid_list) == 0:
                page = page.get()

            curr_old_id = 0
            for i, oldid in enumerate(oldid_list):
                try:
                    curr_old_id = oldid
                    page = page.getOldVersion(oldid)
                    break
                except Exception:
                    logger.info(f"Error retrieving old version. Continuing... {traceback.format_exc()}")
                    if i == len(oldid_list) - 1:
                        print("No valid old version found. Using the current version.")
                        page = page.get()
                    continue

            print(f"Page: {page_title}, Oldid: {curr_old_id}")

            page_html = requests.get(f'https://en.wikipedia.org/w/index.php?title={page_title}&oldid={curr_old_id}').text
            page, tables = self._clean_parse(page)
            table_data = self._parse_table(page_html, classes_to_exclude=["infobox", "box-Expand_language", "box-Update", "nowraplinks", "toccolours"])
            table_data += self._parse_table_with_history(tables, date)

        logger.debug(f"Tables: {table_data}")

        # Ask a LLM for the most relevant information to extract
        class QueryAnswer(BaseModel):
            relevant_information: str = Field(
                description="The most relevant information inside the Wikipedia article relative to the query")


        prompt_template = PromptTemplate(
            input_variables=["full_page_text", "tables", "query_specific", "query_general"],
            template=QUERY_FOR_WIKIPEDIA_INFO_EXTRACTION,
        )

        chain = self.llm.with_structured_output(QueryAnswer, method="json_schema")
        
        complete_template = prompt_template.invoke({"full_page_text": page,
                                                    "tables": table_data,
                                                    "query_specific": query,
                                                    "query_general": original_query})
        
        response = invoke_with_retry(chain, complete_template)

        logger.info(f"Page content response: {pformat(response, width=160)}")
        
        return response.relevant_information

    def query_wikipedia(self, article_name: str, query: str, date: str, initial_problem: str) -> Dict[str, str]:
        self.llm = llm_utils.get_llm(model_name=self.model_name, temperature=self.temperature)

        # Search for articles and their summaries
        search_results = self.search(article_name)

        result = {}
        # Continue if search results are found
        if search_results:
            first_article = list(search_results.keys())[0]
            # Ask the LLM for the best match
            article_to_search = self.ask_LLM_which_article_to_explore(search_results, query)

            if first_article not in article_to_search:
                article_to_search.insert(0, first_article)
            if len(article_to_search) > 3:
                article_to_search = article_to_search[:3]

            print(f"Article to search: {article_to_search}")

            for page_title in article_to_search:
                try:
                    result[page_title] = self.get_page_content(page_title, query, initial_problem, date)
                except Exception:  # Unlikely, but if the given page is not retrievable skip to next page
                    logger.info(f"Error for {page_title}: {traceback.format_exc()}")
                    print(f"Error for {page_title} {traceback.format_exc()}")
                    continue

        return result


class WikipediaQuerySchema(BaseModel):
    article_name: str = Field(description="Keyword or title of the article you are looking for. Article name + keywords work best.")
    information_to_retrieve: str = Field(
        description="Detailed description of the information you are looking for in the articles. Can be long.")
    date: str = Field(description="The date of the article to retrieve mm-dd-yyyy. If you want current data insert 'cur'. It is a mandatory field. It is more efficient than indicating date inside information_to_retrieve.")
    initial_problem: str = Field(description="The initial problem to solve. It is a mandatory field.")


class LangchainWikipediaTool(BaseTool):
    name : str = "wikipedia_search"
    description: str = ("""
The WikipediaTool interfaces with Wikipedia's extensive database, allowing users to retrieve detailed articles and summaries on a wide range of topics.
This tool is useful for gathering information from one of the largest and most frequently updated encyclopedic sources available.

Features:
 - Access to millions of articles across diverse subjects.
 - Possibility to retrieve articles at a specific date.

Usage:
article_name="Albert Einstein awards and biography",
information_to_retrieve="Detailed biography, key contributions to physics, and notable awards as of March 2022."
date="03-01-2022"
# Even if present in information_to_retrieve, put date argument.   
# response = "Albert Einstein was a theoretical physicist who developed the theory of relativity..."
                   
article_name="Climate Change",
information_to_retrieve="Summary of causes, effects, and recent research."

# response = "Climate change refers to significant changes in global temperatures and weather patterns over time..."
""")
    args_schema: Type[BaseModel] = WikipediaQuerySchema
    wikipedia_tool: WikipediaTool = None
    usage_statistics: UsageStatistics = None

    def __init__(self, model_name: str, temperature: float, usage_statistics: UsageStatistics, **kwargs: Any):
        super().__init__(**kwargs)

        self.usage_statistics = usage_statistics
        self.wikipedia_tool = WikipediaTool(model_name, temperature, usage_statistics=self.usage_statistics)

    def _run(self, article_name: str, information_to_retrieve: str, date: str, initial_problem: str) -> Dict[str, str]:
        # Wikipedia regulary throws a GuessedAtParser warning. This hasn't been fixed since 2015 so we just suppress them.
        with warnings.catch_warnings(action='ignore'):
            return self.wikipedia_tool.query_wikipedia(article_name, information_to_retrieve, date, initial_problem)


class HuggingFaceAgentsWikipediaTool(Tool):
    name="wikipedia_search"
    description="Perform a WIKIPEDIA search query then return the search results."
    inputs = {
        "article_name": {
            "type": "text",
            "description": "Keyword or title of the article you are looking for. Article name + keywords work best"
        },
        "information_to_retrieve": {
            "type": "text",
            "description": "Detailed description of the information you are looking for in the articles. Can be long."
        },
        "date": {
            "type": "text",
            "description": "The date of the article to retrieve. Give this date in the format MM-DD-YYYY, for instance '27 June 2008' is written as '06-27-2008'. If you want current data insert 'cur'."
        },
        "initial_problem": {
            "type": "text",
            "description": "The initial problem to solve"
        }
    }
    output_type = "text"
    wikipedia_tool: WikipediaTool = None
    usage_statistics: UsageStatistics = None

    def __init__(self, *args: Any, **kwargs: Any):
        usage_statistics = kwargs.pop('usage_statistics', None)
        model_name = kwargs.pop('model_name', None)
        temperature = kwargs.pop('temperature', None)
        super().__init__(*args, **kwargs)
        self.usage_statistics = usage_statistics
        self.wikipedia_tool = WikipediaTool(model_name, temperature, usage_statistics=self.usage_statistics)

    def forward(self, article_name, information_to_retrieve, date, initial_problem) -> str:
        return self.wikipedia_tool.query_wikipedia(article_name, information_to_retrieve, date, initial_problem)
