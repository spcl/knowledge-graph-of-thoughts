# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Tao Zhang

import glob
import os
import re
import sys


def process_log_file(log_file_path):
    """Process a single log file and extract tool calls based on specific rules."""
    chunks = []
    with open(log_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        
        # We'll search for each pattern in the raw text
        matches = []
        start_pos = 0
        while True:
            # Find the next "Tool call to" pattern
            start_idx = content.find("Tool call to '", start_pos)
            if start_idx == -1:
                break
                
            # Find where the returned part starts
            returned_idx = content.find("returned:", start_idx)
            if returned_idx == -1:
                start_pos = start_idx + 1
                continue
                
            # Find the opening quote of the response
            response_start = content.find("\n'", returned_idx)
            if response_start == -1:
                start_pos = start_idx + 1
                continue
                
            # Look for a line that has only a single quote
            response_start += 2  # Skip past \n'
            
            # Look for a line that has only a single quote
            end_pos = response_start
            while True:
                line_end = content.find("\n", end_pos)
                if line_end == -1:
                    break
                    
                # Check if this line is just a single quote
                line = content[end_pos:line_end].strip()
                if line == "'":
                    # Found the end of the response
                    tool_type = re.search(r"Tool call to '([^']+)'", content[start_idx:returned_idx]).group(1)
                    args_part = content[start_idx:returned_idx + len("returned:")]
                    args_match = re.search(r"with arguments (\{[^}]+\})", args_part)
                    arguments = args_match.group(1) if args_match else "{}"
                    response = content[response_start:end_pos].strip()
                    
                    matches.append((tool_type, arguments, response))
                    start_pos = line_end + 1
                    break
                    
                end_pos = line_end + 1
            
            if end_pos == response_start:  # If we didn't find a closing quote
                start_pos = start_idx + 1
        
        # Process each found tool call
        for tool_type, arguments, response in matches:
            # Skip extract_zip tool calls
            if tool_type == 'extract_zip':
                continue
                
            # Extract query from arguments if available
            query = ""
            if 'question' in arguments:
                query_match = re.search(r"'question': '([^']*)'", arguments)
                if query_match:
                    query = query_match.group(1)
            
            # Process based on tool type
            if tool_type in ['ask_search_agent', 'llm_query']:
                # Only include response
                chunks.append(response.strip())
            elif tool_type in ['inspect_file_as_text', 'image_inspector', 'run_python_code']:
                # Include query and response
                if query:
                    chunks.append(f"Question: {query}\nAnswer: {response.strip()}")
                else:
                    chunks.append(response.strip())
    
    return chunks

def process_logs(num_files=None):
    """Process log files and create corpus file.
    
    Args:
        num_files: Number of files to process. If None or -1, process all files.
    """
    # If num_files is None, process all files
    if num_files is None:
        num_files = -1
    
    # Path to the log directory - use the specific logs/success_log path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(project_root, "logs", "success_log")
    
    # If success_log directory doesn't exist, try alternative paths
    if not os.path.exists(log_dir):
        # Try alternative paths
        alt_paths = [
            os.path.join(project_root, "logs", "fail"),
            os.path.join(project_root, "logs"),
            os.path.join(project_root, "raw_logs")
        ]
        
        for path in alt_paths:
            if os.path.exists(path):
                log_dir = path
                break
    
    print(f"Searching for log files in: {log_dir}")
    
    # Get all log files matching cmd_log_*.log pattern
    all_log_files = glob.glob(os.path.join(log_dir, 'cmd_log_*.log'))
    if not all_log_files:
        # If no files found with that pattern, try all log files
        all_log_files = glob.glob(os.path.join(log_dir, '*.log'))
    
    print(f"Found {len(all_log_files)} log files")
    
    # Sort the log files to process them in order
    all_log_files = sorted(all_log_files)
    
    # Select only the specified number of files if num_files is positive
    log_files = all_log_files if num_files <= 0 else all_log_files[:num_files]
    actual_num_files = len(log_files)
    
    print(f"Processing {actual_num_files} files...")
    
    # Make sure corpus directory exists
    corpus_dir = os.path.join(project_root, 'corpus')
    os.makedirs(corpus_dir, exist_ok=True)
    
    # Set output file name based on number of files processed
    corpus_path = os.path.join(corpus_dir, f'corpus_{actual_num_files}.txt')
    
    all_chunks = []
    
    # Process each log file
    for log_file in log_files:
        print(f"Processing {log_file}...")
        chunks = process_log_file(log_file)
        all_chunks.extend(chunks)
    
    # Write chunks to corpus.txt with "--- Chunk X ---" headers
    with open(corpus_path, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(all_chunks, 1):
            f.write(f"--- Chunk {i} ---\n{chunk}\n\n")
    
    print(f"Processed {len(log_files)} log files and extracted {len(all_chunks)} chunks.")
    print(f"Chunks saved to {corpus_path}")
    
    return corpus_path

def main():
    # Number of log files to process (default is all)
    num_files = -1  # -1 means process all files
    
    # Check if number of files is provided as command-line argument
    if len(sys.argv) > 1:
        try:
            num_files = int(sys.argv[1])
            print(f"Will process {num_files} log files")
        except ValueError:
            print("Invalid number provided. Using all files.")
            num_files = -1
    
    process_logs(num_files)

if __name__ == "__main__":
    main()