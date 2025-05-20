# Python Image Setup

## Installing GAIA Attachments

If you intend to evaluate Knowledge Graph of Thoughts with the GAIA benchmark, please update the Python Docker image with the GAIA attachments. You find the respective instructions [here](/GAIA/dataset/README.md).

## Steps to Run (Docker)

In order to build and run the Python Docker image, please navigate to the `python` directory and execute:

```bash
docker-compose up 
```

## Steps to Run (Sarus)

```bash
chmod +x sarus_launcher.sh     # If needed
./sarus_launcher.sh
```
