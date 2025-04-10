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

from GAIA.plotters.plot_operations import PlotOperation


class AnswerPlot(PlotOperation):
    """
    The AnswerPlot class handles the plotting of results from querying.

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
            close_call_idx = level_df[(~level_df['successful']) & level_df['close_call']]['question_number'].tolist()
            wrong_forced_idx = level_df[(~level_df['successful']) & (level_df['iterations_taken'] == max_iterations)]['question_number'].tolist()
            other_error_idx = level_df[level_df['returned_answer'].fillna('').astype(str).str.contains("error during execution", na=False)]['question_number'].tolist()
            wrong_idx = level_df[~level_df['question_number'].isin(
                correct_idx + correct_forced_idx + close_call_idx + wrong_forced_idx + other_error_idx
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
                'total_successful_answers': len(correct_idx) + len(correct_forced_idx) + len(close_call_idx),
                'correct': len(correct_idx),
                'correct_forced': len(correct_forced_idx),
                'close_call': len(close_call_idx),
                'total_failed_answers': len(wrong_idx) + len(wrong_forced_idx) + len(other_error_idx),
                'wrong_forced': len(wrong_forced_idx),
                'other_error': len(other_error_idx),
                'wrong': len(wrong_idx),
                'question_numbers': {
                    'correct': correct_idx,
                    'correct_forced': correct_forced_idx,
                    'close_call': close_call_idx,
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
            'close_call': 'sum',
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
        self._plot_steps_distribution(df_analyzed, f'{category}_plot_steps_distribution')

    def _plot_steps_distribution(self, df: pd.DataFrame, filename: str) -> None:
        """Create distribution plot showing both all questions and correct answers."""
        plt.figure(figsize=(12, 6))
        
        # Data for all questions from the provided distribution
        all_steps_data = {
            1: 3, 2: 7, 3: 13, 4: 19, 5: 17, 6: 20, 7: 15, 8: 15, 9: 16,
            10: 7, 11: 4, 12: 11, 13: 4, 14: 6, 15: 1, 17: 1, 20: 2,
            24: 1, 32: 1, 44: 1
        }
        
        # Combine steps from correct answers
        correct_steps = []
        for steps in df['correct_steps']:
            correct_steps.extend(steps)
        
        if not correct_steps:
            plt.text(0.5, 0.5, 'No step data available for correct answers',
                    ha='center', va='center', fontsize=12)
        else:
            # Create bins that cover both distributions
            max_steps = max(max(all_steps_data.keys()), max(correct_steps))
            bins = range(0, max_steps + 2, 1)  # +2 to include the max value
            
            # Plot histogram for all questions
            plt.hist(
                [k for k, v in all_steps_data.items() for _ in range(v)],  # Expand frequencies into list
                bins=bins,
                alpha=0.5,
                color='lightblue',
                edgecolor='blue',
                label='All questions',
                align='left'
            )
            
            # Plot histogram for correct questions
            plt.hist(
                correct_steps,
                bins=bins,
                alpha=0.5,
                color='red',
                edgecolor='red',
                label='Correct questions',
                align='left'
            )
            
            # Customize the plot
            plt.xlabel('No. Steps required', fontsize=12)
            plt.ylabel('Question Count', fontsize=12)
            
            # Set x-axis to show steps with reasonable intervals
            plt.xticks(range(0, max_steps + 1, 5))
            
            # Add grid
            plt.grid(True, alpha=0.3, linestyle='--')
            
            # Add legend
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Add title
            plt.title('Distribution of Steps Required for Questions', fontsize=14)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.result_dir_path, f"{filename}.png"), 
                    bbox_inches='tight', dpi=300)
        plt.close()

    def _plot_success(self, df: pd.DataFrame, filename: str) -> None:
        """Create success rate plot."""
        plt.figure(figsize=(12, 6))
        
        # Fetch levels
        levels = df['level'].astype(int)

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
        
        plt.savefig(os.path.join(self.result_dir_path, f"{filename}.png"))
        plt.close()

    def _plot_all_stats(self, df: pd.DataFrame, filename: str) -> None:
        """Create all statistics plot."""
        plt.figure(figsize=(12, 6))
        
        bar_width = 0.15
        index = range(len(df))
        colors = ['green', "cyan", "blue", 'yellow', 'orange', 'red']
        
        for i, stat in enumerate(['correct', 'correct_forced', 'close_call', 'wrong_forced', 'other_error', 'wrong']):
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
        plt.xticks([x + bar_width * 2 for x in index], df['level'].astype(int))
        plt.legend(fontsize="x-large")
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        plt.savefig(os.path.join(self.result_dir_path, f"{filename}.png"))
        plt.close()