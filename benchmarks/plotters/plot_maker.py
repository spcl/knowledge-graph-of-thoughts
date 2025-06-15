# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: You Wu
#               Lorenzo Paleari      

import argparse
import os

from benchmarks.plotters import AnswerPlotGAIA, AnswerPlotSimpleQA, CostPlot, ToolPlot

"""
Usage Examples:
---------------
1. Basic Usage:
   python3 benchmarks/plotters/plot_maker.py --root_directory <path_to_results>

2. Specify Categories:
   python3 benchmarks/plotters/plot_maker.py --root_directory <path_to_results> --categories wikipedia calculator

Flags:
------
--root_directory : str (Required)
    Root directory containing result data.

--categories : str (Optional)
    List of categories to process. Defaults to all available.
"""

DEFAULT_MAX_ITERATIONS = 7

def default_plots(data_dir_path: str, categories: list = None, max_iterations: int = 1, benchmark: str = "gaia"):
    """
    Generates plots from the result data in the specified directory.

    Args:
        data_dir_path (str): Path to the root directory containing result data.
        max_iterations (int): Maximum iterations used in KGoT.
        categories (list): List of categories to process. If None, all available categories are processed.
    """
    if not os.path.exists(data_dir_path):
        raise ValueError(f"The specified root directory '{data_dir_path}' does not exist.")

    # Create the central 'plots' directory under the root directory
    result_dir_path = os.path.join(data_dir_path, "plots")
    os.makedirs(result_dir_path, exist_ok=True)

    # If a specific category is specified, use that
    categories = [
        d.name for d in os.scandir(data_dir_path)
        if d.is_dir() and d.name not in ["snapshots", "plots", "costs"]
    ] if not categories else categories

    # Define plot operations
    plot_operations = [
        AnswerPlotGAIA,
        ToolPlot,
        CostPlot
    ]
    if benchmark == "simpleqa":
        plot_operations = [
            AnswerPlotSimpleQA,
            CostPlot
        ]

    # Use different plotters
    for op in plot_operations:
        df_array = []

        # Initialize the current plot operation once
        res = os.path.join(result_dir_path, op.__name__)
        os.makedirs(res, exist_ok=True)

        plotter = op(res, data_dir_path)

        for category in categories:
            category_path = os.path.join(data_dir_path, category)

            # Find the leaf folder containing the log files
            for dir_path, subfolders, _ in os.walk(category_path):
                if not subfolders:
                    df_dict = plotter.locate(dir_path)
                    df_array_temp = []

                    # analyze the data
                    df_analyzed = plotter.analyze(df_dict, max_iterations=max_iterations)
                    df_array_temp.append(df_analyzed)

                    inputs = {
                        'df_analyzed': df_analyzed,
                        'category': category
                    }

                    # performs actual plotting
                    plotter.execute(custom_inputs=inputs)
                    print(f"Plots for category '{category}' using {op.__name__} have been generated.")
            
            df_array.extend(df_array_temp)
                    
        # To plot the overview with analyzed from each category
        df_merged = plotter.summarize(df_array)
        plotter.execute({'df_analyzed': df_merged, 'category': "all"})

        # Store the json file as overview
        df_merged.to_json(f"{res}/{op.__name__}.json", orient='records', indent=4)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate plots from result data.')
    parser.add_argument('--root_directory', type=str, help='Root directory with result data.')
    parser.add_argument('--categories', type=str, nargs='+', help='Category to process (default: all).')
    parser.add_argument('--max_iterations', type=int, default=DEFAULT_MAX_ITERATIONS, help='Maximum iterations used in KGoT.')
    parser.add_argument('--benchmark', choices=['gaia', 'simpleqa'], default='gaia', help='Answer plot to use (default: gaia).')

    args = parser.parse_args()

    try:
        args.root_directory
    except AttributeError:
        raise ValueError("Please specify the root directory containing the result data.")
    default_plots(args.root_directory, args.categories, args.max_iterations, args.benchmark)
