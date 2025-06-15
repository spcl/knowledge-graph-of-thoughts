# RDF4J Image Setup

## Steps to Run

### Docker

In order to build and run the KGoT Docker image, please navigate to the `kgot` directory and execute:

```bash
docker-compose up 
```

### Sarus

In order to build and run the KGoT Sarus image, please navigate to the `kgot` directory and execute:

```bash
chmod +x sarus_launcher.sh     # If needed
./sarus_launcher.sh
```

## Steps to Create a Local KGoT Image

We provide an already built KGoT image `spcleth/kgot-rdf4j:latest`, that is the default image used in the [`docker-compose`](./docker-compose.yaml) file.
If you want to build the image locally, please follow these steps:

- Create a local image with the following command:

```bash
cd rdf4j_image
docker build -t kgot-rdf4j:latest .
```

- Modify [`docker-compose`](./docker-compose.yaml) and/or [`sarus_launcher.sh`](./sarus_launcher.sh) to use a local image instead of the provided image by substituting `spcleth/kgot-rdf4j:latest` with `kgot-rdf4j:latest`.

- If you want to use the local image with Sarus an additional step is needed. You need to save the image as a tar file and load it into Sarus. You can do this with the following command:

```bash
docker save --output kgot-rdf4j.tar kgot-rdf4j:latest
sarus load ./kgot-rdf4j.tar kgot-rdf4j:latest
```
