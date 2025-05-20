# GAIA Dataset

## GAIA Dataset Download & Processing Script

The script `fetch_gaia_dataset.py` downloads a specific split (`validation` or `test`) of the [`GAIA`](https://huggingface.co/datasets/gaia-benchmark/GAIA) dataset from Hugging Face, extracts and processes its metadata.
The script defaults to fetching the validation dataset.
The script optionally generates a dummy subset for quick testing.

Additional files necessary for the evaluation of GAIA tasks, which we call attachments, are copied to the `./attachments` and `containers/python/files` directories.

### Requirements

- Python 3.9+
- Hugging Face account and an API token with read access
  
### Setup

1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Access dataset and set Hugging Face token<br>
First you must request access to the dataset [here](https://huggingface.co/datasets/gaia-benchmark/GAIA).
Then create a `.env` file in this directory and add your Hugging Face token:

```
HUGGINGFACE_TOKEN=your_token_here
```

### Usage

After fulfilling the steps in the previous section, please make sure to run the script from the current folder:

```bash
python3 ./fetch_gaia_dataset.py [--dataset <split>] [--dummy | --no_dummy]
```

#### Optional Arguments

- `--dataset`: Choose which split to download (default: **validation**)
  - `validation`
  - `test`
- `--dummy`: Include a dummy dataset with the first 5 rows (default: **enabled**)
- `--no_dummy`: Skip dummy dataset creation

## Folder Structure

After executing the script with the default parameters, you will get the following folder structure:

```
.
├── validation/                     # Merged set of questions
│   └── merged_dataset.json
├── validation_subsets/             # Per-level questions and dummy subset
│   ├── level_1.json
│   ├── level_2.json
│   ├── level_3.json
│   └── dummy.json                  # (if enabled)
├── attachments/validation/         # Attachments
```
