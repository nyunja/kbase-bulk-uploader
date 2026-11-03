---
title: "Stop Point-and-Clicking: Automating Genomic Data Imports in KBase"
published: false
description: "How to save hours of manual labor, reduce human error, and focus on analysis rather than data entry in KBase."
tags: kbase, bioinformatics, automation, python
---

## The Frustration of Manual Uploads

If you work with genomic data, you know the drill. You have dozens, maybe even hundreds, of samples to upload to KBase for analysis. Each one requires you to:

1.  Open a new "Upload from Web" cell in your Narrative.
2.  Copy and paste an FTP link.
3.  Click "Import."
4.  Wait for it to finish.
5.  Repeat.

This point-and-click marathon is not only tedious but also a significant source of human error. A slip of the mouse or a copied link can lead to incorrect data, forcing you to start over. It's a productivity killer that keeps you from the real work: analysis.

## The Solution: Automating the Tedium

What if you could automate this entire process? With the **KBase Bulk FTP Uploader**, you can. This Python script, powered by Playwright, transforms the way you import data into KBase.

Instead of manually clicking through the UI, you can now:

-   **List all your FTP links in a single CSV file.**
-   **Run a single command.**
-   **Watch as the script opens each cell, pastes the link, and starts the import.**

The script is designed to be resilient. It waits for each upload to complete before starting the next, ensuring that your data is imported correctly every time.

## Focus on What Matters

By automating the data import process, you can:

-   **Save hours of manual labor.** What used to take an entire afternoon can now be done in minutes.
-   **Reduce human error.** The script doesn't get tired or make mistakes.
-   **Focus on analysis.** Spend your time analyzing your data, not entering it.

The KBase Bulk FTP Uploader is a simple but powerful tool that can dramatically improve your productivity. It's a perfect example of how a little bit of automation can go a long way in scientific research.

Ready to give it a try? Check out the [GitHub repository](https://github.com/your-repo-link) for instructions on how to get started.
