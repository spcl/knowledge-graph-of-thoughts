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
import numpy as np
import pandas as pd

from benchmarks.plotters.plot_operations import PlotOperation


class CostPlot(PlotOperation):
    """
    The CostPlot class handles the plotting of cost statistics from querying LLM.

    Inherits from the PlotOperation class and implements its abstract methods.
    """    

    def locate(self, dir_path: str) -> Dict[str, pd.DataFrame]:
        """Load required cost file into DataFrame"""
        path = os.path.join(dir_path, "llm_cost.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required cost file not found: {path}")
        return {"llm_cost.json": pd.read_json(path, lines=True)}

    def analyze(self, df_dict: Dict[str, pd.DataFrame], **kwargs) -> pd.DataFrame:
        """Analyze cost data and return aggregated statistics."""
        df = df_dict['llm_cost.json']
        
        # Convert timestamps and calculate duration
        df['StartTime'] = pd.to_datetime(df['StartTime'], unit='s')
        df['EndTime'] = pd.to_datetime(df['EndTime'], unit='s')
        df['Duration'] = (df['EndTime'] - df['StartTime']).dt.total_seconds()

        # Group and aggregate data
        grouped_df = df.groupby('FunctionName').agg({
            'PromptTokens': ['count', 'sum', 'mean'],
            'CompletionTokens': ['sum', 'mean'],
            'Cost': ['sum', 'mean'],
            'Duration': ['sum', 'mean'],
            'Model': 'first',
            'StartTime': 'min',
            'EndTime': 'max'
        })
        
        # Flatten column names
        grouped_df.columns = [f"{col[0]}{'_' + col[1] if col[1] != 'first' else ''}" 
                            for col in grouped_df.columns]
        grouped_df = grouped_df.reset_index()
        
        # Calculate total tokens
        grouped_df['TotalTokens'] = grouped_df['PromptTokens_sum'] + grouped_df['CompletionTokens_sum']
        
        # Get min start time and max end time before grouping
        start_time = df['StartTime'].min()
        end_time = df['EndTime'].max()
        
        # Add summary attributes
        grouped_df.attrs['summary'] = {
            'total_calls': grouped_df['PromptTokens_count'].sum(),
            'unique_functions': len(grouped_df),
            'total_cost': grouped_df['Cost_sum'].sum(),
            'total_duration': grouped_df['Duration_sum'].sum(),
            'total_tokens': grouped_df['TotalTokens'].sum(),
            'models_used': grouped_df['Model'].unique().tolist(),
            'start_time': start_time,
            'end_time': end_time
        }

        return grouped_df

    def summarize(self, df_array: List[pd.DataFrame]) -> pd.DataFrame:
        """Summarize cost statistics across multiple DataFrames."""
        if not df_array:
            raise ValueError("Input array cannot be empty")
        
        summarized = pd.concat(df_array).groupby('FunctionName').agg({
            'PromptTokens_count': 'sum',
            'TotalTokens': 'sum',
            'PromptTokens_sum': 'sum',
            'CompletionTokens_sum': 'sum',
            'Cost_sum': 'sum',
            'Duration_sum': 'sum',
            'Model': 'first'
        }).reset_index()

        # Find start time and end time by checking min and max in the whole run
        start_time = min(df.attrs['summary']['start_time'] for df in df_array)
        end_time = max(df.attrs['summary']['end_time'] for df in df_array)

        summarized.attrs['summary'] = {
            'total_calls': sum(df.attrs['summary']['total_calls'] for df in df_array),
            'unique_functions': len(summarized),
            'total_cost': sum(df.attrs['summary']['total_cost'] for df in df_array),
            'total_duration': sum(df.attrs['summary']['total_duration'] for df in df_array),
            'total_tokens': sum(df.attrs['summary']['total_tokens'] for df in df_array),
            'models_used': list(set().union(*[set(df.attrs['summary']['models_used']) for df in df_array])),
            'start_time': start_time,
            'end_time': end_time
        }
        
        return summarized.sort_values('Cost_sum', ascending=False)

    def execute(self, custom_inputs: Any = None) -> Any:
        """Execute the plotting operations."""
        df_analyzed = custom_inputs.get('df_analyzed')
        category = custom_inputs.get('category')
        self._plot_cost_summary(df_analyzed, f'{category}_cost_summary')

    def _plot_cost_summary(self, df: pd.DataFrame, filename: str) -> None:
        """Create detailed cost summary plot with 6 bar subplots."""
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, axes = plt.subplots(2, 3, figsize=(22, 15), facecolor='white')
        
        # Styling
        METRICS = {
            'Cost_sum': {'color': 'steelblue', 'ylabel': 'Cost [$]', 'format': '${:.2e}', 'show_mean': True},
            'PromptTokens_count': {'color': 'mediumorchid', 'ylabel': 'Number of Calls', 'format': '{:.0f}', 'show_mean': True},
            'Duration_sum': {'color': 'indianred', 'ylabel': 'Duration [s]', 'format': '{:.2f} s', 'show_mean': True},
            'cost_per_token': {'color': 'steelblue', 'ylabel': 'Cost/Token [$]', 'format': '${:.2e}', 'show_mean': False},
            'cost_per_second': {'color': 'steelblue', 'ylabel': 'Cost/Second [$/s]', 'format': '{:.2e}', 'show_mean': False},
            'tokens_per_second': {'color': 'forestgreen', 'ylabel': 'Tokens/Second [1/s]', 'format': '{:.2f} /s', 'show_mean': False}
        }

        PLOT_STYLE = {
            'TITLE_SIZE': 22,
            'SUBTITLE_SIZE': 18,
            'AXES_TITLE_SIZE': 16,
            'TICK_SIZE': 10,
            'STAT_SIZE': 10,
            'BG_COLOR': 'whitesmoke'
        }

        MODEL_ALIASES = {
            'gpt-4o-mini': 'gpt-4o-mini-2024-07-18',
            'gpt-4o': 'gpt-4o-2024-08-06'
        }

        # Prepare derived metrics
        df = df.copy()
        epsilon = 1e-10  # Small threshold for cost-related metrics
        df['cost_per_token'] = df['Cost_sum'].div(df['TotalTokens']).replace([np.inf, -np.inf], 0)
        df['cost_per_second'] = df['Cost_sum'].div(df['Duration_sum']).replace([np.inf, -np.inf], 0)
        df['tokens_per_second'] = df['TotalTokens'].div(df['Duration_sum']).replace([np.inf, -np.inf], 0)

        summary = df.attrs.get('summary', {})
        total_duration = summary.get('total_duration', 0)
        duration_str = (f"{total_duration:.2f}s" if total_duration < 60 else
                    f"{total_duration/60:.2f}min" if total_duration < 3600 else
                    f"{total_duration/3600:.2f}h")

        for (metric, config), ax in zip(METRICS.items(), axes.flatten()):
            ax.set_facecolor(PLOT_STYLE['BG_COLOR'])
            
            # Use stricter filtering for cost-related metrics
            if 'cost' in metric.lower():
                data = df[df[metric] > epsilon].sort_values(metric, ascending=False)
                # Set scientific notation for y-axis if it's a cost metric
                ax.yaxis.set_major_formatter(plt.ScalarFormatter(useMathText=True))
                ax.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
            else:
                data = df[df[metric] > 0].sort_values(metric, ascending=False)
            
            if data.empty:
                continue

            values = data[metric]
            ax.bar(range(len(values)), values, color=config['color'], alpha=0.85, edgecolor='none')
            
            # Configure axes
            ax.set_title(config['ylabel'], pad=20, fontsize=PLOT_STYLE['AXES_TITLE_SIZE'], fontweight='bold')
            ax.tick_params(axis='both', labelsize=PLOT_STYLE['TICK_SIZE'])
            ax.set_xticks(range(len(values)))
            ax.set_xticklabels(data['FunctionName'], rotation=45, ha='right')
            ax.grid(True, axis='y', linestyle='--', alpha=0.15, color='gray')
            ax.spines[['top', 'right']].set_visible(False)
            ax.spines[['left', 'bottom']].set_color('gray')

            # Add statistics only for non-zero values
            y_range = values.max() - values.min()
            
            # Define stats based on whether to show mean
            if config['show_mean']:
                stats = [('Arithmetic Mean', values.mean(), '--', 0),
                        ('Min', values.min(), ':', y_range * 0.05),
                        ('Max', values.max(), ':', -y_range * 0.05)]
            else:
                stats = [('Min', values.min(), ':', y_range * 0.05),
                        ('Max', values.max(), ':', -y_range * 0.05)]
                
            for stat_name, stat_value, line_style, y_offset in stats:
                ax.axhline(y=stat_value, color='gray', linestyle=line_style, alpha=0.5)
                text = ax.text(len(values)-1, stat_value + y_offset,
                            f'{stat_name}: {config["format"].format(stat_value)}',
                            va='bottom', ha='right', fontsize=PLOT_STYLE['STAT_SIZE'])
                text.set_bbox(dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))

        # Title and subtitle
        title = fig.suptitle("KGoT Function Call Cost Summary",
                        fontsize=PLOT_STYLE['TITLE_SIZE'], fontweight='bold', y=0.98)
        title.set_bbox(dict(facecolor='white', alpha=0.8, edgecolor='none', pad=2))
        
        time_range = ("({:%Y-%m-%d %H:%M:%S} to {:%Y-%m-%d %H:%M:%S})".format(
            summary.get('start_time'), summary.get('end_time'))
            if summary.get('start_time') and summary.get('end_time')
            else "(No time data available)")
        
        total_cost = summary.get('total_cost', 0)
        cost_str = f"${total_cost:.2f}"
        canonical_models = {MODEL_ALIASES.get(m, m) for m in summary.get('models_used', [])}
        subtitle = (
            f"Model: {' '.join(canonical_models)}, Total Cost: {cost_str}\n"
            f"Unique Functions: {summary.get('unique_functions', 0)}, "
            f"analyzed {summary.get('total_calls', 0)} calls over {duration_str} "
            f"{time_range}"
        )
                
        plt.figtext(0.5, 0.94, subtitle, fontsize=PLOT_STYLE['SUBTITLE_SIZE'], ha='center', va='top')
        plt.tight_layout(rect=[0, 0, 1, 0.90])
        plt.savefig(os.path.join(self.result_dir_path, f"{filename}.pdf"),
                bbox_inches='tight', dpi=300, facecolor='white')
        plt.close(fig)
