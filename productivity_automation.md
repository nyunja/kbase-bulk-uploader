# Stop Point-and-Clicking: Automating Genomic Data Imports in KBase

If you’ve ever sat in front of a KBase Narrative with a spreadsheet of 50 FTP links, you know the feeling of impending boredom. 

The process is always the same:
1. Click **Add Data**.
2. Click **Import**.
3. Click **Upload File to Staging from Web**.
4. Paste the URL.
5. Click **Run**.
6. Wait for the cell to initialize… and repeat. 

For a dozen samples, it’s a nuisance. For a hundred, it’s a day of lost productivity. This is why I built the **KBase Bulk FTP Uploader**—a tool designed to turn a day of clicking into a single command.

---

## The Hidden Cost of Manual Data Entry

In bioinformatics, we often talk about high-performance computing and complex algorithms, but we rarely talk about the "data entry tax." 

When you manually import data:
- **Human Error increases:** It’s easy to skip a row in your CSV or paste the same URL twice when you’re 40 samples deep.
- **Cognitive Fatigue sets in:** Clicking buttons is mentally draining, leaving you less energy for the actual science—the analysis.
- **Time is Wasted:** Every minute spent babysitting a browser tab is a minute not spent reading literature or interpreting results.

---

## From Manual to "Set and Forget"

The KBase Bulk FTP Uploader uses **browser automation** (via Playwright) to mimic a human user. It logs in, navigates to your Narrative, and performs those repetitive clicks for you. 

The beauty of this approach is that it respects the KBase UI. It doesn’t try to hack an API; it just does exactly what you would do, but faster and without getting tired.

### The "Resumable" Workflow
One of the most frustrating parts of manual uploads is when the browser crashes or your session expires. With this automation tool, progress is tracked in a local log file. If the process is interrupted, you just run the command again. The script checks the log, sees which samples are already in the Narrative, and picks up exactly where it left off.

---

## How it Changes the Lab Workflow

Imagine your new workflow:
1. **Download** your sample list from the SRA or ENA.
2. **Configure** a simple `.env` file with your Narrative name.
3. **Run** the script: `python kbase_uploader.py`.
4. **Walk away.** Go grab a coffee, attend a meeting, or start drafting your methods section.

By the time you get back, your Narrative is populated with dozens of import jobs, all running in parallel or sequence, ready for your next analysis step.

---

## Conclusion: Let the Machines do the Boring Stuff

Bioinformatics should be about discovery, not data entry. Automation tools like this aren’t just about speed; they’re about reclaiming your time and ensuring your research is reproducible and error-free.

If you’re ready to stop clicking and start analyzing, check out the project on GitHub and automate your next batch of uploads.

**Explore the Project:** [KBase Bulk FTP Uploader on GitHub](https://github.com/nyunja/kbase-bulk-uploader)
