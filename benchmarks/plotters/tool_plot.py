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
from enum import Enum
from typing import Any, Dict, List

import kaleido
import pandas as pd
import plotly.graph_objects as go

from benchmarks.plotters import (
    AnswerPlotGAIA,
    load_kgot_tools,
    load_reference_tools,
)
from benchmarks.plotters.plot_operations import PlotOperation


class ToolMatch(str, Enum):
    """
    Enum class representing the correctness of tool choice in KGoT.
    Each member represents a different level of correctness based on the coverage percentage.
    The coverage percentage is calculated as the ratio of correctly chosen tools to the total number of tools needed for a question.
    """
    CORRECT = "Correct Tool Choice"
    PARTIAL_HIGH = "Partially Correct (High Match)"
    PARTIAL_MEDIUM = "Partially Correct (Medium Match)"
    PARTIAL_LOW = "Partially Correct (Low Match)"
    WRONG = "Wrong Tool Choice"

    def categorize(coverage: float)-> Enum:
        """
        Categorize tool match correctness with quartile-based thresholds
        
        Args:
            coverage (float): Coverage percentage of tool choice.
        """
        match = (ToolMatch.CORRECT if coverage == 1.0 else
            ToolMatch.PARTIAL_HIGH if coverage >= 0.75 else
            ToolMatch.PARTIAL_MEDIUM if coverage >= 0.50 else
            ToolMatch.PARTIAL_LOW if coverage >= 0.25 else
            ToolMatch.WRONG)

        return match

    @property
    def color(self) -> str:
        """
        Returns:
            str: Color code for the tool match status.
        """
        colors = {
            ToolMatch.CORRECT: 'limegreen',
            ToolMatch.PARTIAL_HIGH: 'mediumaquamarine',
            ToolMatch.PARTIAL_MEDIUM: 'gold',  
            ToolMatch.PARTIAL_LOW: 'orange',
            ToolMatch.WRONG: 'tomato'
        }
        return colors[self]


class ToolPlot(PlotOperation):
    """
    The ToolPlot class handles the plotting of tool usage analysis from KGoT run on GAIA.

    Inherits from the PlotOperation class and implements its abstract methods.
    """    

    def locate(self, dir_path: str) -> Dict[str, pd.DataFrame]:
        """
        Locate and load the required files for tool usage analysis.

        Args:
            dir_path (str): Directory path where the files are located.
        
        Returns: 
            dict: Dictionary containing DataFrames loaded from the required files.
        """
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
        """
        Analyze the loaded DataFrames to extract tool usage statistics.
        
        Args:
            df_dict (dict): Dictionary containing DataFrames loaded from the required files.
            **kwargs: Additional keyword arguments.
            
        Returns:
            pd.DataFrame: DataFrame containing the analyzed tool usage statistics.
        """
        max_iterations = kwargs.get('max_iterations', 1)
        # would be better to put this in gaia_data_analyst 
        answer_df = AnswerPlotGAIA.analyze(df_dict, max_iterations=max_iterations)
        q_status = {}
        total_questions = 0

        # Same success categorization as in answer plot
        success_categories = {'correct', 'correct_forced', 'close_call'}
        for _, entry in answer_df.iterrows():
            total_questions += entry.get('total_questions')
            question_numbers = entry.get('question_numbers', {})
            for status, indices in question_numbers.items():
                success = 'successful' if status in success_categories else 'failed'
                for index in indices:
                    q_status[index] = success

        # Tool plot specific - fetch dataframes from the dict
        kgot_tool_df = df_dict.get('cmd_log.log')
        correct_stats = df_dict.get('correct_stats.json')
        reference_tool_df = load_reference_tools(correct_stats)

        # Postprocessing
        df = pd.merge(
            kgot_tool_df,
            reference_tool_df,
            on='question_number',
            how='outer'
        )

        # Calculate coverage percentage of GAIA categories wanted
        coverages = []
        matches = []
        successes = []

        for _, entry in df.iterrows():
            question_number = int(entry.get('question_number'))
            kgot_categories = entry.get('kgot_categories', [])
            ref_categories = entry.get('reference_categories', [])

            if not kgot_categories and not ref_categories:
                coverage = 1.0
            elif ref_categories:
                coverage = len(set(kgot_categories) & set(ref_categories)) / len(ref_categories)
            else:
                coverage = 0.0 # no tools needed but tool used

            # Quartile-based thresholds
            match =ToolMatch.categorize(coverage)

            # Append to the lists
            coverages.append(coverage)
            matches.append(match)
            successes.append(q_status[question_number])

        # Add coverage and match as new columns in the dataframe
        df['tool_correctness']    = matches
        df['coverage_percentage'] = coverages
        df['question_success'] = successes

        # Add meta data
        category_counts = df['tool_correctness'].value_counts()
        df._metadata = {
            'total_questions': total_questions,
            'category_counts': category_counts
        }

        return df

    def summarize(self, df_array: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Combine multiple DataFrames into one and recalculate metadata.

        Args:
            df_array (list): List of DataFrames to be combined.

        Returns:
            pd.DataFrame: Combined DataFrame with recalculated metadata.
        """
        if not df_array:
            raise ValueError("Input array cannot be empty")

        # Check for duplicates and combine data
        all_questions = [q for df in df_array for q in df['question_number']]
        if len(all_questions) != len(set(all_questions)):
            raise ValueError("Duplicate question numbers found")
        
        combined = pd.concat(df_array, ignore_index=True)
        
        # Recalculate metadata        
        combined._metadata = {
            'total_questions': len(combined),
            'category_counts': combined['tool_correctness'].value_counts(),
        }
        
        return combined

    def execute(self, custom_inputs: Any = None) -> Any:
        """
        Execute the plotting operations.

        Args:
            custom_inputs: Optional dictionary containing additional parameters.
        """
        # Fetch custom input
        df_analyzed = custom_inputs.get('df_analyzed')
        category    = custom_inputs.get('category')

        # Create plots
        self._plot_tool_match(df_analyzed, f'{category}_tool_match')
        self._plot_sankey(df_analyzed, f'{category}_tool_choice_analysis')
        self._plot_kgot_tool_usage(df_analyzed, f'{category}_tool_usage_count')
        self._plot_category_success_bar(df_analyzed, f'{category}_tool_category_success')

    def _plot_tool_match(self, df: pd.DataFrame, filename: str) -> None:
        """Create tool match plot as stacked bars."""
        category_counts = df._metadata['category_counts']
        total = df._metadata['total_questions']

        # Create figure with all tool match categories
        fig = go.Figure([
            go.Bar(
                x=[''],
                y=[count],
                name=match.value,
                marker_color=match.color
            ) for match in ToolMatch if (count := category_counts.get(match, 0)) > 0
        ])

        # Calculate percentages directly from tool match category counts
        cumsum = 0
        annotations = []
        for match in ToolMatch:
            count = category_counts.get(match, 0)
            if count > 0:
                percentage = (count / total * 100).round(1)
                cumsum += count
                annotations.append({
                    'x': 0,
                    'y': cumsum - (count / 2),
                    'text': f"{percentage:.1f}%",
                    'showarrow': False,
                    'font': {'color': 'white', 'size': 15}
                })

        fig.update_layout(
            title={'text': 'Tool Choice Correctness Analysis', 'x': 0.5},
            height=600, width=1000,
            barmode='stack',
            showlegend=True,
            yaxis_title='Number of Questions',
            template='plotly_white',
            annotations=annotations + [{
                'text': f"Total Questions Analyzed: {total}",
                'showarrow': False,
                'x': 0.5,
                'y': -0.1,
                'xref': "paper",
                'yref': "paper",
                'font': {'size': 14}
            }]
        )

        # Save outputs
        kaleido.write_fig_sync(fig, os.path.join(self.result_dir_path, f"{filename}.png"))

    def _plot_sankey(self, df: pd.DataFrame, filename: str) -> None:
        """Create sankey flow diagram showing tool correctness to GAIA success"""
        tool_usage = (
            pd.DataFrame({
                'tool_status': df['tool_correctness'],
                'question_success': df['question_success'],
                'count': 1
            })
            .groupby(['tool_status', 'question_success'])
            .size()
            .reset_index(name='count')
        )
        
        tool_usage['order'] = tool_usage['tool_status'].map(lambda x: list(ToolMatch).index(x))
        tool_usage = tool_usage.sort_values('order')
        
        # Calculate node totals for labels
        tool_counts = tool_usage.groupby('tool_status')['count'].sum()
        qn_success_counts = tool_usage.groupby('question_success')['count'].sum()
        
        # Create labels with counts
        tool_labels = [f"{str(status)}<br>N = {int(tool_counts.get(status, 0))}" for status in ToolMatch]
        qn_success_labels = [f"{s.capitalize()}<br>N = {int(qn_success_counts.get(s, 0))}" for s in ['successful', 'failed']]
        nodes = tool_labels + qn_success_labels
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color=[status.color for status in ToolMatch] + ['lightslategray', 'lightslategray']
            ),
            link=dict(
                source=[list(ToolMatch).index(s) for s in tool_usage['tool_status']],
                target=[len(ToolMatch) + ['successful', 'failed'].index(t) for t in tool_usage['question_success']],
                value=tool_usage['count'],
                color="rgba(211, 211, 211, 0.5)",
                customdata=tool_usage['count'],  # Store counts for hover text
                hovertemplate='Flow count: %{customdata}<extra></extra>'  # Show count on hover
            )
        )])
        
        # Add level labels
        for x, text in [(0.01, "Tool Choice"), (0.99, "GAIA Question")]:
            fig.add_annotation(
                x=x, y=-0.15,
                text=text,
                showarrow=False,
                font=dict(size=14),
                xref="paper",
                yref="paper"
            )
                
        fig.update_layout(
            title={
                'text': 'Tool Correctness to Question Success Analysis',
                'x': 0.5,
                'xanchor': 'center'
            },
            height=600,
            width=600,
            margin=dict(t=100, l=50, r=50, b=100)
        )
        kaleido.write_fig_sync(fig, os.path.join(self.result_dir_path, f"{filename}.png"))

    def _plot_kgot_tool_usage(self, df: pd.DataFrame, filename: str) -> None:
        """Create a pie chart showing KGoT tool usage distribution."""
        tool_counts = df['kgot_tools'].explode().value_counts()
        
        # Generate colors for each KGoT tool in the pie chart
        num_tools = len(tool_counts)
        colors = [
            f'rgba({50 + int(i * (150 / num_tools))}, {150 + int(i * (80 / num_tools))}, {200 - int(i * (100 / num_tools))}, 0.9)' 
            for i in range(num_tools)
        ]

        # Create figure
        fig = go.Figure(go.Pie(
            values=tool_counts.values,
            labels=tool_counts.index,
            hole=0.6,
            textposition='outside',
            texttemplate='%{label}<br>%{percent}',
            showlegend=False,
            marker=dict(
                colors=colors,
                line=dict(color='white', width=2)
            ),
            rotation=90,
            domain=dict(x=[0.15, 0.85], y=[0.15, 0.85])  # pie chart size
        ))
        
        # Update layout with title and annotations
        total_questions = df._metadata['total_questions']
        fig.update_layout(
            title=dict(
                text=f'KGoT Tool Usage Distribution<br>'
                    f'<sup>{len(tool_counts)} unique tools for '
                    f'{total_questions} GAIA questions</sup>',
                x=0.5,
                y=0.88,
                xanchor='center', yanchor='top',
                font=dict(size=16)
            ),
            width=600, height=600,
            template='simple_white',
            margin=dict(t=80, l=10, r=10, b=10),
            annotations=[dict(
                text=f'Total Tool Usage Count:<br>{tool_counts.sum():,}',
                x=0.5, 
                y=0.5,
                font=dict(size=14),
                showarrow=False
            )]
        )
        
        # Save output
        kaleido.write_fig_sync(fig, os.path.join(self.result_dir_path, f"{filename}.png"))

    def _plot_category_success_bar(self, df: pd.DataFrame, filename: str) -> None:
        """Create grouped bar chart showing GAIA categories success"""
        # Prepare data
        categories_expanded = (
            df.explode('reference_categories')[['reference_categories', 'question_success']]
            .dropna(subset=['reference_categories'])
        )
        category_success = (
            categories_expanded
            .groupby(['reference_categories', 'question_success'])
            .size()
            .unstack(fill_value=0)
        )
        category_success = category_success.loc[category_success.sum(axis=1).sort_values().index]

        # Create figure
        fig = go.Figure()
        colors = {'successful': 'lightgreen', 'failed': 'lightcoral'}
        
        for status in category_success.columns:
            fig.add_trace(go.Bar(
                y=category_success.index,
                x=category_success[status],
                name=status.capitalize(),
                orientation='h',
                marker_color=colors.get(status, 'lightgray'),
                text=category_success[status],
                textposition='auto',
            ))
        
        # Update layout
        fig.update_layout(
            title={
                'text': f'Question Success by GAIA Categories<br><sup>Total Questions: {df._metadata["total_questions"]}</sup>',
                'x': 0.5,
                'xanchor': 'center'
            },
            plot_bgcolor='whitesmoke',
            barmode='stack',
            height=800,
            width=800,
            margin=dict(l=200, r=50, t=100, b=50),
            xaxis_title="Number of Questions",
            yaxis={'categoryorder': 'total ascending'}
        )
        
        # Save the figure
        kaleido.write_fig_sync(fig, os.path.join(self.result_dir_path, f"{filename}.png"))