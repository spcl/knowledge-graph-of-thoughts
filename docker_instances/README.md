# Docker Image Setup

## Installing GAIA Attachments

If you intend to evaluate Knowledge Graph of Thoughts with the GAIA benchmark, please update the Python Docker image with the GAIA attachments. You find the respective instructions [here](/GAIA/dataset/README.md).

## Steps to Run

```sh
docker compose up

# detached version
docker compose up -d
```

This will build and start:

- Neo4j Docker image
- Python Docker image

If you want to start them separately, please refer to the respective READMEs:
- [Neo4j](/docker_instances/neo4j_docker/README.md)
- [Python](/docker_instances/python_docker/README.md)


## Rebuilding Images

If you modify the setup of the images, such as mounting new datasets as attachments for Docker instances to access or updating the code within the Python code executor, you may want to force a rebuild of the containers without using the cache:

```bash
docker compose build --no-cache
```
