# Datasets

## Datasets Download & Processing Script

The script `fetch_dataset.py` downloads a specific benchmark dataset (`GAIA` or `SimpleQA`).

### GAIA Dataset

The script download a specific split (`validation` or `test`) of the [`GAIA`](https://huggingface.co/datasets/gaia-benchmark/GAIA) dataset from Hugging Face, extracts and processes its metadata.
The script defaults to fetching the validation dataset.
The script optionally generates a dummy subset for quick testing.

Additional files necessary for the evaluation of GAIA tasks, which we call attachments, are copied to the `./GAIA/attachments` and `containers/python/files` directories.

### SimpleQA Dataset

The script download the full [`SimpleQA`](https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv) dataset from OpenAI and processes it to create a JSON file with the same format as the GAIA dataset.
The script optionally generates a dummy subset for quick testing.
The script can also randomly sample a percentage of the dataset to create a smaller subset for testing purposes.

To reproduce the results in the paper please use the default seed `123456` and sample size of 10% of the dataset.

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
python3 ./fetch_dataset.py [--benchmark <bench>] [--dataset <split>] [--dummy | --no_dummy] [--random_sample <sample_size>] [--random_seed <seed>]
```

#### Optional Arguments

- `--benchmark`: Choose which benchmark to download (default: **all**)
  - `all`
  - `gaia`
  - `simpleqa`
- `--dataset`: Choose which GAIA split to download (default: **validation**)
  - `validation`
  - `test`
- `--dummy`: Include a dummy dataset with the first 5 rows (default: **enabled**)
- `--no-dummy`: Skip dummy dataset creation
- `--random_sample`: Set a percentage to randomly sample from the SimpleQA dataset (default: **10**)
- `--random_seed`: Set a random seed for sampling the SimpleQA dataset (default: **123456**)

## Folder Structure

After executing the script with the default parameters, you will get the following folder structure:

```
.
├── fetch_datasets.py
├── GAIA
│   ├── attachments/validation/                 # Attachments
│   ├── validation                              # GAIA validation set 
│   │   └── merged_dataset.json
│   └── validation_subsets                      # Per-level questions and dummy subset
│       ├── dummy.json                          # (if enabled)
│       ├── level_1.json
│       ├── level_2.json
│       └── level_3.json
├── SimpleQA
│   ├── dummy_set.json                          # (if enabled)  
│   ├── formatted_simpleqa.json
│   ├── simple_qa_test_set.csv
│   └── test_set_10_percent_seed123456.json     # (if enabled)
```
