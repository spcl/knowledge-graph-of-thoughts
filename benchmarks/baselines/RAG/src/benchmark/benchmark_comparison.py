# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Tao Zhang

import json

import matplotlib.pyplot as plt
import numpy as np

# Load the results from correct_stats.json
with open('rag_baselines/rag_results_corpus1/correct_stats.json', 'r') as f:
    results = json.load(f)

# Count successful answers by level
rag_correct = [0, 0, 0]  # [level1, level2, level3]

for result in results:
    if result.get('successful', False):
        level = result.get('level')
        if level in [1, 2, 3]:
            rag_correct[level-1] += 1

# Load Graph-RAG results
with open('rag_baselines/results/graphrag_benchmark/results.json', 'r') as f:
    graphrag_results = json.load(f)

# Count successful answers by level for Graph-RAG
graphrag_correct = [0, 0, 0]  # [level1, level2, level3]

for result in graphrag_results:
    if result.get('successful', False):
        level = result.get('level')
        if level in [1, 2, 3]:
            graphrag_correct[level-1] += 1

# Data for the other benchmarks
zero_shot_correct = [4, 13, 0]  # [level1, level2, level3]
kgot_correct = [21, 18, 1]      # [level1, level2, level3]

# Set up the plot
fig, ax = plt.subplots(figsize=(10, 6))
width = 0.6
x = np.arange(4)  # 4 positions for the bars - updated to add Graph-RAG

# Create stacked bars - reordered as (Zero-Shot, Graph-RAG, RAG, KGoT)
p1 = ax.bar(x, [zero_shot_correct[0], graphrag_correct[0], rag_correct[0], kgot_correct[0]], width, label='Level 1', color='#5DA5DA')
p2 = ax.bar(x, [zero_shot_correct[1], graphrag_correct[1], rag_correct[1], kgot_correct[1]], width, bottom=[zero_shot_correct[0], graphrag_correct[0], rag_correct[0], kgot_correct[0]], label='Level 2', color='#FAA43A')
p3 = ax.bar(x, [zero_shot_correct[2], graphrag_correct[2], rag_correct[2], kgot_correct[2]], width, bottom=[zero_shot_correct[0]+zero_shot_correct[1], graphrag_correct[0]+graphrag_correct[1], rag_correct[0]+rag_correct[1], kgot_correct[0]+kgot_correct[1]], label='Level 3', color='#60BD68')

# Add labels, title, etc.
ax.set_ylabel('Number of Correct Answers')
ax.set_title('Performance Comparison by Level')
ax.set_xticks(x)
ax.set_xticklabels(['Zero-Shot', 'Graph-RAG', 'RAG', 'KGoT'])  # Updated order
ax.legend()

# Add total counts on top of each bar
for i, benchmarks in enumerate([(zero_shot_correct), (graphrag_correct), (rag_correct), (kgot_correct)]):
    total = sum(benchmarks)
    ax.text(i, total + 0.5, str(total), ha='center', fontweight='bold')

# Add value labels to each segment
for bar in p1:
    height = bar.get_height()
    if height > 0:
        ax.text(bar.get_x() + bar.get_width()/2., height/2, f'{int(height)}', 
                ha='center', va='center', color='white', fontweight='bold')

for bar, bottom in zip(p2, [zero_shot_correct[0], graphrag_correct[0], rag_correct[0], kgot_correct[0]]):
    height = bar.get_height()
    if height > 0:
        ax.text(bar.get_x() + bar.get_width()/2., bottom + height/2, f'{int(height)}', 
                ha='center', va='center', color='white', fontweight='bold')

for bar, bottom in zip(p3, [zero_shot_correct[0]+zero_shot_correct[1], graphrag_correct[0]+graphrag_correct[1], rag_correct[0]+rag_correct[1], kgot_correct[0]+kgot_correct[1]]):
    height = bar.get_height()
    if height > 0:
        ax.text(bar.get_x() + bar.get_width()/2., bottom + height/2, f'{int(height)}', 
                ha='center', va='center', color='white', fontweight='bold')

# Show the plot
plt.tight_layout()
plt.savefig('benchmark_comparison.png')
plt.show()

print(f"Zero-Shot correct answers: Level 1: {zero_shot_correct[0]}, Level 2: {zero_shot_correct[1]}, Level 3: {zero_shot_correct[2]}, Total: {sum(zero_shot_correct)}")
print(f"Graph-RAG correct answers: Level 1: {graphrag_correct[0]}, Level 2: {graphrag_correct[1]}, Level 3: {graphrag_correct[2]}, Total: {sum(graphrag_correct)}")
print(f"RAG correct answers: Level 1: {rag_correct[0]}, Level 2: {rag_correct[1]}, Level 3: {rag_correct[2]}, Total: {sum(rag_correct)}")
print(f"KGoT correct answers: Level 1: {kgot_correct[0]}, Level 2: {kgot_correct[1]}, Level 3: {kgot_correct[2]}, Total: {sum(kgot_correct)}") 