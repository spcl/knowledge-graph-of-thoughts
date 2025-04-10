# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: You Wu
#               Lorenzo Paleari      

import argparse
import json
import os

from GAIA.plotters import AnswerPlot, CostPlot, LeaderboardPlot, ToolPlot

"""
Usage Examples:
---------------
1. Basic Usage:
   python3 GAIA/plotters/plot_maker.py --root_directory <path_to_results>

2. Specify Categories:
   python3 GAIA/plotters/plot_maker.py --root_directory <path_to_results> --categories wikipedia calculator

3. Generate Leaderboard:
    python3 GAIA/plotters/plot_maker.py --root_directory <path_to_results> --leaderboard

Flags:
------
--root_directory : str (Required)
    Root directory containing result data.

--categories : str (Optional)
    List of categories to process. Defaults to all available.
"""

DEFAULT_LEADERBOARD_DIR = "results/current_runs"
DEFAULT_MAX_ITERATIONS = 7


def default_plots(data_dir_path: str, categories: list = None, max_iterations: int = 1) -> None:
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
        AnswerPlot,
        ToolPlot,
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


def leaderboard_plot(leaderboard_dir: str, max_iterations: int) -> None:
    """
    Generates leaderboard plots from the result data in the specified directory.

    Args:
        leaderboard_dir (str): Path to the root directory containing leaderboard data.
        max_iterations (int): Maximum iterations used in KGoT.
    """
    if not os.path.exists(leaderboard_dir):
        raise ValueError(f"The specified root directory '{leaderboard_dir}' does not exist.")

    # Create the central 'plots' directory under the root directory
    result_dir_path = os.path.join(leaderboard_dir, "leaderboard_plots")
    os.makedirs(result_dir_path, exist_ok=True)

    # All methods except the ones starting with "HF_full" and "leaderboard"
    methods = [d for d in os.listdir(leaderboard_dir) if os.path.isdir(os.path.join(leaderboard_dir, d)) 
               and not d.startswith("HF_full") and not d.startswith("leaderboard") and not d.startswith("Zero-Shots")]

    df_array = {}

    # Initialize the current plot operation once
    plotter = LeaderboardPlot(result_dir_path, leaderboard_dir)

    for method in methods:
        method_path = os.path.join(leaderboard_dir, method)

        df_array[method] = []

        # categories are directories inside the method directory
        if not os.path.isdir(method_path):
            continue

        categories = [c for c in os.listdir(method_path) if os.path.isdir(os.path.join(method_path, c))
                        and c not in ["plots", "costs", "snapshots"]]
        
        for category in categories:
            category_path = os.path.join(method_path, category)

            # Find the leaf folder containing the log files
            for dir_path, subfolders, files in os.walk(category_path):
                if not subfolders:
                    df_dict = plotter.locate(dir_path)

                    # analyze the data
                    df_analyzed = plotter.analyze(df_dict, max_iterations=max_iterations)
                    df_array[method].append(df_analyzed)
                
    df_merged = plotter.summarize(df_array)
    plotter.execute(df_merged)

    # Store the json file as overview
    with open(f"{result_dir_path}/leaderboard.json", "w") as f:
        json.dump(df_merged, f, indent=4)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate plots from result data.')
    parser.add_argument('--root_directory', type=str, help='Root directory with result data.')
    parser.add_argument('--categories', type=str, nargs='+', help='Category to process (default: all).')
    parser.add_argument('--max_iterations', type=int, default=DEFAULT_MAX_ITERATIONS, help='Maximum iterations used in KGoT.')
    parser.add_argument('--leaderboard', action='store_true', help='Generate leaderboard plots.')
    parser.add_argument('--leaderboard_dir', type=str, default=DEFAULT_LEADERBOARD_DIR, help='Directory for leaderboard data.')
    parser.add_argument('--no-op', action='store_true', help='Do not generate "normal" plots.')

    args = parser.parse_args()

    if not args.no_op:
        try:
            args.root_directory
        except AttributeError:
            raise ValueError("Please specify the root directory containing the result data.")
        default_plots(args.root_directory, args.categories, args.max_iterations)
    
    if args.leaderboard:
        leaderboard_plot(args.leaderboard_dir, args.max_iterations)
