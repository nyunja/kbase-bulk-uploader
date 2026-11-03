# Step-by-Step: Bulk Uploading SRA/ENA Reads to KBase via FTP Links

Importing large genomic datasets into [KBase](https://kbase.us) is a common starting point for bioinformatics workflows. However, if you have dozens or hundreds of samples, manually opening the "Upload with URL" app for every single link is a recipe for carpal tunnel.

In this guide, we’ll show you how to use the **KBase Bulk FTP Uploader** to automate this process using a simple CSV and browser automation.

---

## Prerequisites

Before starting, ensure you have:
1. A **KBase account** (and the name of the Narrative you want to upload to).
2. **Python 3.9+** installed on your machine.
3. The **KBase Bulk FTP Uploader** source code.

---

## Step 1: Prepare Your CSV Data

The uploader reads a CSV file containing at least two things: a **Unique ID** for each sample and the **FTP/HTTP URL**.

If you are downloading from the **European Nucleotide Archive (ENA)**, you can export a report that already includes these headers (`ena_run_acc` and `ftp_link_1`).

**Example `data.csv`:**
```csv
ena_run_acc,ftp_link_1,country
ERR2607401,ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR260/001/ERR2607401/ERR2607401.fastq.gz,Kenya
ERR2607398,ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR260/008/ERR2607398/ERR2607398.fastq.gz,Uganda
```

---

## Step 2: Installation

Clone the repository and install the dependencies. We use **Playwright** for the browser automation, which requires a one-time browser installation.

```bash
# Clone the tool
git clone https://github.com/nyunja/kbase-bulk-uploader.git
cd kbase-bulk-uploader

# Install dependencies
pip install -r requirements.txt

# Install the Chromium browser
playwright install chromium
```

---

## Step 3: Configure Your Environment

Instead of hardcoding your password in the script, we use a `.env` file. Copy the provided template and fill in your details.

```bash
cp .env.example .env
```

Edit the `.env` file:
```ini
KBASE_EMAIL=your.email@gmail.com
KBASE_PASSWORD=your_secure_password
NARRATIVE=Microbiome Analysis 2024
KBASE_CSV_PATH=data.csv
```

---

## Step 4: Run the Uploader

Now, trigger the automation. On the first run, the script will open a browser window. If it can't log in automatically (due to 2FA), you can simply log in manually, and the script will take over once it detects the KBase dashboard.

```bash
python kbase_uploader.py
```

### Pro Tip: Custom Column Names
If your CSV uses different headers (e.g., `SampleID` instead of `ena_run_acc`), you don't need to rename them in Excel. Just pass the arguments:

```bash
python kbase_uploader.py --acc-col SampleID --url-col download_url
```

---

## Step 5: Monitoring and Resuming

As the script runs, you will see it:
1. Open your Narrative.
2. Search for the "Upload with URL" app.
3. Fill in the FTP link.
4. Click **Run**.
5. Save the accession to `uploaded_samples.log`.

**Why the log matters:** If your internet drops or KBase goes down for maintenance, you can simply restart the script. It will read `uploaded_samples.log`, see which samples are already done, and skip them automatically.

---

## Conclusion

Automating the data entry layer of your bioinformatics workflow saves time and ensures that every sample is imported with the exact same parameters. 

**Happy uploading!**

*Find the full source code and contribute on GitHub: [nyunja/kbase-bulk-uploader](https://github.com/nyunja/kbase-bulk-uploader)*
