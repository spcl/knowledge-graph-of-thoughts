# Containers Image Setup

## Installing GAIA Attachments

If you intend to evaluate Knowledge Graph of Thoughts with the GAIA benchmark, please update the Python image with the GAIA attachments. You find the respective instructions [here](/benchmarks/datasets/README.md).

## Docker

### Steps to Run

```sh
docker compose up

# detached version
docker compose up -d
```

This will build and start:

- Neo4j Docker image
- Python Docker image

If you want to start them separately, please refer to the respective READMEs:

- [Neo4j](/containers/neo4j/README.md)
- [Python](/containers/python/README.md)

Additionally we also support running [RDF4J](/containers/rdf4j/README.md) as a container.
If you want to run a containerized instance of KGoT, please refer to the [KGoT README](/containers/kgot/README.md).

### Rebuilding Images

If you modify the setup of the images, such as mounting new datasets as attachments for Docker instances to access or updating the code within the Python code executor, you may want to force a rebuild of the containers without using the cache:

```bash
docker compose build --no-cache
```

## Sarus

### Steps to Run

First download the necessary images:

```sh
sarus pull python:3.12-slim
sarus pull neo4j:5.26.2
sarus pull spcleth/kgot:latest
sarus pull spcleth/kgot-rdf4j:latest
```

Then run the containers using the provided scripts:

- You can run Python and Neo4j together `./sarus_launcher.sh`
- You can enter a sub-folder of the ``containers`` folder and run the respective script to start the single container: `./sarus_launcher.sh`
