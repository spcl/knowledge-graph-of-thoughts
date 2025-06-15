# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main author: You Wu
#               
# Contributions: Lorenzo Paleari

import os
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd

from benchmarks.plotters.plot_operations import PlotOperation


class AnswerPlotSimpleQA(PlotOperation):
    """
    The AnswerPlot class handles the plotting of results from querying the SimpleQA benchmark.

    Inherits from the PlotOperation class and implements its abstract methods.
    """

    def locate(self, dir_path: str) -> Dict[str, pd.DataFrame]:
        """Load required stats file into DataFrame"""
        path = os.path.join(dir_path, "correct_stats.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required stats file not found: {path}")
            
        return {"correct_stats.json": pd.read_json(path)}

    @staticmethod
    def analyze(df_dict: Dict[str, pd.DataFrame], **kwargs) -> pd.DataFrame:
        """Analyze statistics for each level."""
        df = df_dict.get('correct_stats.json')

        max_iterations = kwargs.get('max_iterations', 1)
        
        # Postprocessing
        stats = []        
        for level in df['level'].unique():
            level_df = df[df['level'] == level]
            total = len(level_df)

            # Collect question numbers for all metrics for better json overview & debugging
            correct_idx = level_df[(level_df['successful']) & (level_df['iterations_taken'] < max_iterations)]['question_number'].tolist()
            correct_forced_idx = level_df[(level_df['successful']) & (level_df['iterations_taken'] == max_iterations)]['question_number'].tolist()
            not_attempted_idx = level_df[level_df['not_attempted']]['question_number'].tolist()
            wrong_forced_idx = level_df[(~level_df['successful']) & (level_df['iterations_taken'] == max_iterations)]['question_number'].tolist()
            other_error_idx = level_df[level_df['returned_answer'].fillna('').astype(str).str.contains("error during execution", na=False)]['question_number'].tolist()
            wrong_idx = level_df[~level_df['question_number'].isin(
                correct_idx + correct_forced_idx + not_attempted_idx + wrong_forced_idx + other_error_idx
            )]['question_number'].tolist()

            # Get steps data for correct answers
            correct_steps = level_df[
                (level_df['successful']) & 
                (level_df['iterations_taken'] < max_iterations)
            ]['num_steps']

            correct_steps_temp = []
            for steps in correct_steps:
                try:
                    step = int(steps)
                    correct_steps_temp.append(step)
                except ValueError:
                    correct_steps_temp.append(-1)

            correct_steps = correct_steps_temp

            # Metrics
            metrics = {
                'level': level,
                'total_questions': total,
                'total_successful_answers': len(correct_idx) + len(correct_forced_idx),
                'correct': len(correct_idx),
                'correct_forced': len(correct_forced_idx),
                'not_attempted': len(not_attempted_idx),
                'total_failed_answers': len(wrong_idx) + len(wrong_forced_idx) + len(other_error_idx),
                'wrong_forced': len(wrong_forced_idx),
                'other_error': len(other_error_idx),
                'wrong': len(wrong_idx),
                'question_numbers': {
                    'correct': correct_idx,
                    'correct_forced': correct_forced_idx,
                    'not_attempted': not_attempted_idx,
                    'wrong_forced': wrong_forced_idx,
                    'other_error': other_error_idx,
                    'wrong': wrong_idx
                },
                'correct_steps': correct_steps  # Add steps data
            }
            stats.append(metrics)
        
        return pd.DataFrame(stats).sort_values('level')

    def summarize(self, df_array: List[pd.DataFrame]) -> pd.DataFrame:
        """Summarize statistics across multiple DataFrames by level."""
        if not df_array:
            raise ValueError("Input array cannot be empty")
        
        combined = pd.concat(df_array, ignore_index=True)
        return combined.groupby('level', as_index=False).agg({
            'total_questions': 'sum',
            'total_successful_answers': 'sum',
            'correct': 'sum',
            'correct_forced': 'sum',
            'not_attempted': 'sum',
            'total_failed_answers': 'sum',
            'wrong_forced': 'sum',
            'other_error': 'sum',
            'wrong': 'sum',
            'question_numbers': lambda x: {
                key: [item for d in x for item in d[key]] for key in x.iloc[0]
            },
            'correct_steps': lambda x: [item for items in x for item in items]  # Flatten steps lists
        }).sort_values('level')

    def execute(self, custom_inputs: Any = None) -> Any:
        """
        Execute the plotting operations.

        Args:
            custom_inputs: Optional dictionary containing additional parameters.
        """
        # Fetch custom input
        df_analyzed = custom_inputs.get('df_analyzed')
        category = custom_inputs.get('category')

        # Create plots
        self._plot_success(df_analyzed, f'{category}_plot_success')
        self._plot_all_stats(df_analyzed, f'{category}_plot_all_stats')

    def _plot_success(self, df: pd.DataFrame, filename: str) -> None:
        """Create success rate plot."""
        plt.figure(figsize=(12, 6))
        
        # Fetch levels
        levels = df['level'].astype(str)

        # Prepare percentage bars
        success_count = df['total_successful_answers']
        success_rates = (success_count / df['total_questions']) * 100        
        bars = plt.bar(levels, success_rates, color='skyblue', alpha=0.7, capsize=5)
        
        # Add labels showing both percentage and raw counts
        for bar, count, total in zip(bars, success_count, df['total_questions']):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{bar.get_height():.2f}%\n({count}/{total})',
                    ha='center', va='bottom')
        
        plt.xlabel('Level', fontsize="xx-large")
        plt.ylabel('Success Rate (%)', fontsize="xx-large")
        plt.ylim(0, 100)

        # Ensure x-ticks are integers
        plt.xticks(levels, labels=levels)
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        plt.savefig(os.path.join(self.result_dir_path, f"{filename}.pdf"))
        plt.close()

    def _plot_all_stats(self, df: pd.DataFrame, filename: str) -> None:
        """Create all statistics plot."""
        plt.figure(figsize=(12, 6))
        
        bar_width = 0.15
        index = range(len(df))
        colors = ['green', "cyan", "blue", 'yellow', 'orange', 'red']
        
        for i, stat in enumerate(['correct', 'correct_forced', 'not_attempted', 'wrong_forced', 'other_error', 'wrong']):
            rate = df[stat] / df['total_questions'] * 100
            bars = plt.bar([x + i * bar_width for x in index], rate, bar_width,
                        alpha=0.7, color=colors[i],
                        label=stat.replace('_', ' ').capitalize(),
                        capsize=5)
            
            for bar, val, tot, total in zip(bars, rate, df[stat], df['total_questions']):
                plt.text(bar.get_x() + bar.get_width()/2, val + 1,
                        f'{int(val)}%\n({tot}/{total})',
                        ha='center', va='bottom')
        
        plt.xlabel('Level', fontsize="xx-large")
        plt.ylabel('Rate (%)', fontsize="xx-large")
        plt.ylim(0, 100)
        plt.xticks([x + bar_width * 2 for x in index], df['level'].astype(str))
        plt.legend(fontsize="x-large")

        # Add title with statistics
        title = "Statistics for SimpleQA\n"
        
        # Correct, not attempted and incorrect percentages
        correct_percentage = ((df['correct'] + df['correct_forced']) / df['total_questions'])[0]
        not_attempted_percentage = (df['not_attempted'] / df['total_questions'])[0]
        incorrect_percentage = ((df['wrong'] + df['wrong_forced'] + df['other_error']) / df['total_questions'])[0]
        title += f"Correct: {correct_percentage:.4f}   --   "
        title += f"Not Attempted: {not_attempted_percentage:.4f}    --   \n"
        title += f"Incorrect: {incorrect_percentage:.4f}    --   "

        # Correct given attempts
        correct_given_attempts = ((df['correct'] + df['correct_forced']) / (df['total_questions'] - df['not_attempted']))[0]
        title += f"Correct Given Attempts: {correct_given_attempts:.4f}   --  "

        # F1 score
        f1_score = (2 * correct_percentage * correct_given_attempts) / (correct_percentage + correct_given_attempts) if (correct_percentage + correct_given_attempts) > 0 else 0
        title += f"F1 Score: {f1_score:.4f}\n"

        plt.title(title, fontsize=10, loc='center')
        plt.suptitle("SimpleQA Statistics", fontsize=20)
        plt.subplots_adjust(top=0.85)

        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        plt.savefig(os.path.join(self.result_dir_path, f"{filename}.pdf"))
        plt.close()
