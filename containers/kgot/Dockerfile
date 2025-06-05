FROM spcleth/kgot:latest

WORKDIR /home/knowledge_graph_of_thoughts

# Adding minimum files to build dependencies
ADD pyproject.toml .
CMD mkdir kgot
ADD kgot/__init__.py kgot/__init__.py
ADD kgot/__main__.py kgot/__main__.py
ADD LICENSE .
ADD README.md .

# Install kgot dependencies
RUN python3.11 -m venv venv
RUN . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -e . && \
    playwright install

# The copy process is done later, so that all Python dependencies are installed before copying the code and thus cached if code changes.
# Copy KGoT code to the container
COPY kgot kgot
COPY benchmarks benchmarks
ADD run_multiple_* .
RUN chmod +x run_multiple_*

ENTRYPOINT [ "/bin/bash", "-c"]
