# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: Lorenzo Paleari

import math
import os
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd

from GAIA.plotters import (
    AnswerPlot,
    load_kgot_tools,
    load_reference_tools,
)
from GAIA.plotters.plot_operations import PlotOperation


class LeaderboardPlot(PlotOperation):
    """
    The LeaderboardPlot class handles the plotting of leaderboard plots for GAIA runs.
    """

    def locate(self, dir_path: str) -> Dict[str, pd.DataFrame]:
        """Load required stats and log files into DataFrames"""
        df_dict = {}
        files = ["correct_stats.json", "cmd_log.log"]
        
        for file in files:
            path = os.path.join(dir_path, file)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Required file not found: {path}")
            
            with open(path) as f:
                df_dict[file] = pd.read_json(f) if file.endswith('.json') else load_kgot_tools(f)
                
        return df_dict

    def analyze(self, df_dict: Dict[str, pd.DataFrame], **kwargs) -> pd.DataFrame:
        """Analyze KGoT tool use on GAIA run from log files"""
        max_iterations = kwargs.get('max_iterations', 1)

        # Reuse analysis from AnswerPlot
        answer_df = AnswerPlot.analyze(df_dict, max_iterations=max_iterations)
        q_status = {}

        # success categorization
        success_categories = {'correct', 'correct_forced', 'close_call'}
        for _, entry in answer_df.iterrows():
            question_numbers = entry.get('question_numbers', {})
            for status, indices in question_numbers.items():
                success = 'successful' if status in success_categories else 'failed'
                for index in indices:
                    q_status[index] = success

        # Load dataframes
        kgot_tool_df = df_dict.get('cmd_log.log')
        correct_stats = df_dict.get('correct_stats.json')
        reference_tool_df = load_reference_tools(correct_stats)

        # Convert correct_stats into a DataFrame
        correct_stats_df = pd.DataFrame(correct_stats)

        # Ensure 'question_number' columns are integers
        kgot_tool_df['question_number'] = kgot_tool_df['question_number'].astype(int)
        reference_tool_df['question_number'] = reference_tool_df['question_number'].astype(int)
        correct_stats_df['question_number'] = correct_stats_df['question_number'].astype(int)

        # Merge the tool usage data with reference tool categories
        df = pd.merge(
            kgot_tool_df,
            reference_tool_df,
            on='question_number',
            how='outer'
        )

        # Add question success from q_status
        df['question_success'] = df['question_number'].apply(lambda x: q_status.get(int(x), 'failed'))

        # Add level from correct_stats
        df = pd.merge(
            df,
            correct_stats_df[['question_number', 'level']],
            on='question_number',
            how='left'
        )

        # Keep only important fields
        df = df[['question_number', 'level', 'reference_categories', "question_success"]]

        return df

    def summarize(self, df_array: Dict[str, List[pd.DataFrame]]) -> Dict[str, Dict[str, Dict[str, int]]]:
        """Summarize tool use statistics across multiple DataFrames by question.
        
        For each category:
        - Keep counts of successful questions by level for each method.
        - At the end, determine which method has the highest total count (sum of all levels).
        - 'total' key will hold the counts of that best-performing method.
        """

        if not df_array:
            raise ValueError("Input array cannot be empty")

        categories_dict = {}
        best_splits = None

        # Iterate over each method and its DataFrames
        for method_name, df_list in df_array.items():
            splits = {}

            # Some entries might be empty DataFrames
            for df in df_list:
                if df.empty:
                    continue
                # Iterate over each question in the dataframe
                for _, row in df.iterrows():
                    question_success = row.get('question_success', 'failed')
                    if question_success == 'successful':

                        level = row['level']
                        ref_cats = row['reference_categories']
                        level_key = f"level_{level}"

                        # Update categories_dict for each category found
                        for cat in ref_cats:
                            if cat not in categories_dict:
                                categories_dict[cat] = {}
                            if cat not in splits:
                                splits[cat] = {
                                    "level_1": 0,
                                    "level_2": 0,
                                    "level_3": 0
                                }
                            if method_name not in categories_dict[cat]:
                                categories_dict[cat][method_name] = {
                                    "level_1": 0,
                                    "level_2": 0,
                                    "level_3": 0
                                }
                            categories_dict[cat][method_name][level_key] += 1
                            splits[cat][level_key] += 1

                    else:
                        # Count splits for failed questions
                        level = row['level']
                        ref_cats = row['reference_categories']
                        level_key = f"level_{level}"

                        for cat in ref_cats:
                            if cat not in splits:
                                splits[cat] = {
                                    "level_1": 0,
                                    "level_2": 0,
                                    "level_3": 0
                                }
                            splits[cat][level_key] += 1

            if best_splits is None:
                best_splits = splits
            else:
                # Add splits in best splits if category not present
                for cat, levels in splits.items():
                    if cat not in best_splits:
                        best_splits[cat] = levels
                for cat, levels in splits.items():
                    for level, count in levels.items():
                        if count > best_splits[cat][level]:
                            best_splits[cat][level] = count

        # Add the best splits to the categories_dict
        for cat, levels in best_splits.items():
            if cat not in categories_dict:
                categories_dict[cat] = {}
            categories_dict[cat]["best"] = levels

        return categories_dict         

    def execute(self, combined_data: Dict[str, Dict[str, Dict[str, int]]] = None) -> Any:
        """
        Execute the plotting operations.

        Args:
            combined_data (Dict[str, Dict[str, Dict[str, int]]]): The combined data to be plotted.
        """
        if combined_data is None or not combined_data:
            print("No data provided to execute plotting.")
            return

        # Convert "level_1", "level_2", "level_3" to "1", "2", "3" for compatibility
        data = {}
        for category, methods_data in combined_data.items():
            data[category] = {}
            for method_name, level_counts in methods_data.items():
                # Convert keys
                data[category][method_name] = {
                    "1": level_counts.get("level_1", 0),
                    "2": level_counts.get("level_2", 0),
                    "3": level_counts.get("level_3", 0)
                }

        # Create a leaderboard per category
        for category, methods_data in data.items():
            df = pd.DataFrame.from_dict(methods_data, orient='index')
            # Ensure the levels columns exist even if empty
            for col in ["1", "2", "3"]:
                if col not in df.columns:
                    df[col] = 0
            df['total'] = df[['1','2','3']].sum(axis=1)

            # Extract "best" method data if present
            l1 = l2 = l3 = total = 0
            if 'best' in df.index:
                best_row = df.loc['best']
                l1, l2, l3, total = best_row['1'], best_row['2'], best_row['3'], best_row['total']
                # Remove 'best' so we don't plot it
                df = df.drop('best')

            # Sort by total descending
            df = df.sort_values(by='total', ascending=False)

            # Determine max value for the y-axis limit
            max_val = df['total'].max() if not df.empty else 0

            # Plot per-category (stacked bar chart by level)
            plt.figure(figsize=(10,6))
            methods_order = df.index.tolist()
            bottom = [0]*len(methods_order)
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

            for i, lvl in enumerate(["1","2","3"]):
                plt.bar(methods_order, df[lvl], bottom=bottom, label=f'Level {lvl}', color=colors[i])
                bottom = [x+y for x,y in zip(bottom, df[lvl])]

            # Construct subtitle from best data
            subtitle = ""
            if total > 0:
                subtitle = f"\nTotal: {total} (L1: {l1}, L2: {l2}, L3: {l3})"

            plt.title(f"Leaderboard for Category: {category}{subtitle}")
            plt.xlabel("Method")
            plt.ylabel("Number of Solved Problems")
            plt.legend()
            plt.xticks(rotation=45, ha='right')

            # Add space above the top score
            plt.ylim(0, max_val + 1)

            plt.tight_layout()
            plt.savefig(os.path.join(self.result_dir_path, f"{category}.png"))
            plt.close()

        # Now create a single figure with all categories as subplots
        num_categories = len(data.keys())
        if num_categories > 0:
            # Determine a grid that is as close to square as possible
            rows = int(math.floor(math.sqrt(num_categories)))
            cols = int(math.ceil(num_categories / rows))

            # Increase figure size for better readability
            _, axes = plt.subplots(nrows=rows, ncols=cols, figsize=(10*cols, 6*rows))

            # If there's only one subplot, ensure axes is a list
            if rows == 1 and cols == 1:
                axes = [axes]
            else:
                axes = axes.flatten()

            for i, (category, methods_data) in enumerate(data.items()):
                ax = axes[i]
                df = pd.DataFrame.from_dict(methods_data, orient='index')
                # Ensure columns 1,2,3 exist
                for col in ["1", "2", "3"]:
                    if col not in df.columns:
                        df[col] = 0
                df['total'] = df[['1','2','3']].sum(axis=1)

                # Extract "best" if present
                l1 = l2 = l3 = total = 0
                if 'best' in df.index:
                    best_row = df.loc['best']
                    l1, l2, l3, total = best_row['1'], best_row['2'], best_row['3'], best_row['total']
                    df = df.drop('best')

                df = df.sort_values(by='total', ascending=False)
                methods_order = df.index.tolist()

                bottom = [0]*len(methods_order)
                colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
                for j, lvl in enumerate(["1","2","3"]):
                    ax.bar(methods_order, df[lvl], bottom=bottom, label=f'Level {lvl}', color=colors[j])
                    bottom = [x+y for x,y in zip(bottom, df[lvl])]

                # Construct subtitle from best data
                subtitle = ""
                if total > 0:
                    subtitle = f"\nTotal: {total} (L1: {l1}, L2: {l2}, L3: {l3})"

                ax.set_title(f"{category}{subtitle}")
                ax.set_xlabel("Method")
                ax.set_ylabel("Solved")
                ax.legend()

                # Explicitly set tick positions and labels:
                ax.set_xticks(range(len(methods_order)))
                ax.set_xticklabels(methods_order, rotation=45, ha='right')

                # Add space above the top score
                max_val = df['total'].max() if not df.empty else 0
                ax.set_ylim(0, max_val + 1)

            # Turn off unused subplots if any
            for k in range(i+1, rows*cols):
                axes[k].axis('off')

            plt.tight_layout()
            plt.savefig(os.path.join(self.result_dir_path, "all_categories.pdf"))
            plt.close()

        print("Leaderboards generated successfully.")
