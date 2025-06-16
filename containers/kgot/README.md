# KGoT Image Setup

## Setup

In order to change the KGoT options, please navigate to the `kgot` directory and edit the `.env` file.
All options specified in [`benchmarks/README.md`](../../benchmarks/README.md) are available in the `.env` file.

In addition, the following option is available

- FILE_TO_EXECUTE=""
  - This option specifies the file to execute. By default, it is set to `run_multiple_gaia.sh`, which executes the GAIA benchmark.
  - If you want to run a different script, please specify the script here.

## Steps to Run

### Docker

In order to build and run the KGoT Docker image, please navigate to the `kgot` directory and execute:

```bash
docker-compose up 
```

### Sarus

In order to build and run the KGoT Docker image, please navigate to the `kgot` directory and execute:

```bash
chmod +x sarus_launcher.sh     # If needed
./sarus_launcher.sh
```

## Steps to Create a Local KGoT Image

We provide an already built KGoT image `spcleth/kgot:latest`, which is the default image used in the [`Dockerfile`](./Dockerfile).
If you want to build the image locally, please follow these steps:

- Create a local image with the following command:

```bash
cd kgot_image
docker build -t kgot:latest .
```

- Modify [`Dockerfile`](./Dockerfile) and/or [`sarus_launcher.sh`](./sarus_launcher.sh) to use a local image instead of the provided image by substituting `spcleth/kgot:latest` with `kgot:latest`.

- If you want to use the local image with Sarus an additional step is needed. You need to save the image as a tar file and load it into Sarus. You can do this with the following command:

```bash
docker save --output kgot.tar kgot:latest
sarus load ./kgot.tar kgot:latest
```
