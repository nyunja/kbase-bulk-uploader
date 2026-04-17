# KBase Bulk FTP Uploader

Automates the repetitive process of importing multiple genomic data files from FTP/HTTP URLs into a [KBase](https://kbase.us) Narrative using Playwright browser automation.

Instead of manually opening each "Upload File to Staging from Web" app cell in your Narrative, this script reads a CSV of URLs and submits each one automatically — skipping samples that have already been processed.

---

## Features

- ✅ **Resumable** — tracks submitted samples in a log file; safe to restart at any time
- ✅ **Duplicate-safe** — skips samples already in the log (staged or running)  
- ✅ **Flexible CSV format** — column names are configurable via CLI arguments
- ✅ **Persistent sessions** — saves your KBase login so you only authenticate once
- ✅ **Clear error reporting** — saves screenshots to `logs/` on failures

---

## Prerequisites

- Python 3.9+
- A [KBase](https://kbase.us) account (Google login supported)
- The target Narrative must already exist and contain the "Upload File to Staging from Web" app (or be able to add it)

---

## Installation

```bash
# 1. Clone or download this repository
git clone https://github.com/your-username/kbase-uploader.git
cd kbase-uploader

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install the Chromium browser for Playwright
playwright install chromium
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your details:

```bash
cp .env.example .env
```

```ini
# .env
KBASE_EMAIL=your.email@gmail.com
KBASE_PASSWORD=your_password_here
NARRATIVE=My Narrative Name
KBASE_CSV_PATH=data.csv
```

> **Never commit your `.env` file.** It is already listed in `.gitignore`.

---

## CSV Format

Your CSV must have at minimum:
- **A unique ID column** (for deduplication tracking)
- **A URL column** (the FTP or HTTP link to upload)

The default column names match the ENA/SRA export format but are fully configurable:

| Default Column Name | Purpose                              |
|---------------------|--------------------------------------|
| `ena_run_acc`       | Unique sample ID (for deduplication) |
| `ftp_link_1`        | Primary FTP/HTTP URL to upload       |
| `country`           | *(optional)* Shown in log messages   |
| `city`              | *(optional)* Shown in log messages   |

See `example_data.csv` for a minimal working example.

---

## Usage

### Basic (uses `.env` for all settings)
```bash
python kbase_uploader.py
```

### Specify a different CSV or Narrative
```bash
python kbase_uploader.py --csv my_samples.csv --narrative "My Narrative"
```

### Custom CSV column names (if your CSV uses different headers)
```bash
python kbase_uploader.py \
  --acc-col sample_id \
  --url-col ftp_url \
  --csv my_data.csv
```

### Use a direct Narrative URL instead of searching by name
```bash
python kbase_uploader.py --narrative-url https://narrative.kbase.us/narrative/12345
```

### Full options
```
python kbase_uploader.py --help
```

---

## First Run (Login Setup)

On first run, a browser window will open. If you have not set `KBASE_EMAIL` and `KBASE_PASSWORD`, the script will pause and ask you to sign in manually. After signing in, your session is saved in `kbase_user_session/` and future runs will skip the login step automatically.

> If the script fails to start with a `SingletonLock` error, run:
> ```bash
> rm -f kbase_user_session/SingletonLock
> ```

---

## Tracking & Resumption

Every successfully submitted sample is appended to `uploaded_samples.log` (one accession per line). On restart, the script loads this log and skips those samples.

You can manually add accessions to this file to mark them as "done" before running:
```
ERR2607401
ERR2607398
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `SingletonLock` error on start | `rm -f kbase_user_session/SingletonLock` |
| CSV column not found error | Use `--acc-col` / `--url-col` to specify correct column names |
| Script skips run after entering URL | Likely a KBase UI validation issue — check `logs/error_*.png` |
| Narrative not found on dashboard | Make sure `--narrative` exactly matches the name shown in KBase |
| Session expired mid-run | The script will detect this and attempt a page refresh; re-run if needed |

---

## Project Structure

```
kbase-uploader/
├── kbase_uploader.py      # Main automation script
├── requirements.txt       # Python dependencies
├── .env.example           # Configuration template (copy to .env)
├── .gitignore             # Prevents committing secrets/sessions
├── example_data.csv       # Minimal CSV example showing expected format
├── uploaded_samples.log   # Auto-created: tracks processed samples
├── kbase_user_session/    # Auto-created: persistent browser session
└── logs/                  # Auto-created: error screenshots
```

---

## License

MIT
