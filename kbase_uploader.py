"""
kbase_uploader.py — KBase Bulk FTP Import Automation
=====================================================
Automates the repetitive process of submitting "Upload File to Staging from Web"
jobs in a KBase Narrative for a list of FTP/HTTP URLs stored in a CSV file.

Usage:
    python kbase_uploader.py [OPTIONS]

Run `python kbase_uploader.py --help` for full option descriptions.

Configuration:
    Create a .env file from .env.example and fill in your KBase credentials
    and Narrative name. All options can also be passed as CLI arguments.
"""

import pandas as pd
import time
import argparse
import sys
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# --- SCRIPT DIRECTORY (used for reliable default paths) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- DEFAULTS (read from .env — no hardcoded credentials) ---
DEFAULT_EMAIL          = os.getenv("KBASE_EMAIL", "")
DEFAULT_PASSWORD       = os.getenv("KBASE_PASSWORD", "")
DEFAULT_NARRATIVE_URL  = os.getenv("KBASE_NARRATIVE_URL", "")
DEFAULT_NARRATIVE_NAME = os.getenv("NARRATIVE", "")
DEFAULT_DASHBOARD_URL  = os.getenv("KBASE_DASHBOARD_URL", "https://narrative.kbase.us/narratives")
DEFAULT_CSV            = os.getenv("KBASE_CSV_PATH", "data.csv")
DEFAULT_USER_DIR       = os.getenv("KBASE_USER_DIR", os.path.join(SCRIPT_DIR, "kbase_user_session"))
DEFAULT_LOG_FILE       = os.path.join(SCRIPT_DIR, "uploaded_samples.log")
DEFAULT_LOGS_DIR       = os.path.join(SCRIPT_DIR, "logs")

# --- DEFAULT CSV COLUMN NAMES (overridable via CLI) ---
DEFAULT_ACC_COL        = "ena_run_acc"   # Unique ID for deduplication
DEFAULT_URL_COL        = "ftp_link_1"   # Forward / primary FTP URL
DEFAULT_URL_COL2       = "ftp_link_2"   # Reverse / secondary FTP URL (optional, for paired-end reads)
DEFAULT_COUNTRY_COL    = "country"      # Optional: for display in logs
DEFAULT_CITY_COL       = "city"         # Optional: for display in logs


# ==============================================================================
# HELPERS
# ==============================================================================

def wait_for_kbase_ready(page, timeout=120000):
    """
    Waits for the KBase loading blocker to disappear and confirms the Narrative
    interface is interactive before proceeding with any UI actions.
    """
    try:
        blocker_selector = '#kb-loading-blocker'
        if page.is_visible(blocker_selector):
            print(f"    - [BLOCKER] Waiting for {blocker_selector} to hide...")
            page.wait_for_selector(blocker_selector, state="hidden", timeout=timeout)
            time.sleep(2)

        ready_selector = (
            'button[data-test-id="add-data-button"], '
            'button:has-text("Add Data"), '
            '.kb-nav__link:has-text("Analyze")'
        )
        page.wait_for_selector(ready_selector, state="visible", timeout=timeout)
        return True
    except Exception as e:
        print(f"  - [WARNING] Narrative ready check timed out or failed: {str(e)}")
        return False


def open_narrative_by_name(page, context, name):
    """
    Finds and opens a narrative by its exact name on the KBase dashboard.
    Returns the new page object (tab) for the opened Narrative editor.
    """
    print(f"Searching for narrative: '{name}' on dashboard...")

    # Check if it's already open in another tab
    for p in context.pages:
        try:
            p_title = p.title()
            if name.lower() in p_title.lower() or "/narrative/" in p.url:
                print(f"  - Narrative already open in a tab. Switching...")
                p.bring_to_front()
                return p
        except:
            continue

    # Find the narrative item in the sidebar
    list_item_selector = f'div[class*="NarrativeList_narrative_item_outer"]:has-text("{name}")'
    if not page.is_visible(list_item_selector):
        list_item_selector = f'div:has-text("{name}")'

    try:
        page.wait_for_selector(list_item_selector, timeout=15000)
        print(f"  - Selecting '{name}' in the list...")
        page.locator(list_item_selector).first.click()
        time.sleep(2)
    except Exception as e:
        print(f"  - [ERROR] Could not find narrative '{name}': {str(e)}")
        page.screenshot(path=os.path.join(DEFAULT_LOGS_DIR, "dashboard_selection_error.png"))
        return None

    # Click the external link to open the Narrative Editor in a new tab
    print("  - Clicking the external link to open Narrative Editor...")
    external_link_selector = f'a[target="_blank"]:has-text("{name}")'
    try:
        page.wait_for_selector(external_link_selector, timeout=10000)
        with context.expect_page(timeout=20000) as new_page_info:
            page.locator(external_link_selector).first.click()
        new_page = new_page_info.value
        print(f"  - Successfully switched to Narrative Editor tab: {new_page.url}")
        wait_for_kbase_ready(new_page)
        return new_page
    except Exception as e:
        print(f"  - Error opening editor tab: {str(e)}")
        time.sleep(5)
        for p in context.pages:
            if "/narrative/" in p.url:
                wait_for_kbase_ready(p)
                return p
    return None


def check_for_unauthorized_popups(page):
    """
    Detects and dismisses 'Not Authorized' or 'Session Expired' popups
    that can block the UI mid-run.
    """
    detectors = [
        'text="Not Authorized"',
        'text="Session Expired"',
        'text="Please sign in"',
        '.modal-title:has-text("Not Authorized")',
        '.modal-body:has-text("Sign In")',
    ]
    for selector in detectors:
        try:
            if page.locator(selector).first.is_visible(timeout=1000):
                print(f"  - [ALERT] Detected unauthorized popup: {selector}")
                close_btn = page.locator(
                    'button:has-text("OK"), button:has-text("Close"), button:has-text("Dismiss")'
                ).first
                if close_btn.is_visible(timeout=1000):
                    close_btn.click()
                print("  - Refreshing page to clear state...")su chats 
                page.reload()
                time.sleep(5)
                return True
        except:
            continue
    return False


def handle_google_login(page, email, password):
    """
    Handles Google OAuth login for KBase.
    Supports both the 'Choose an account' screen and fresh email/password entry.
    If automated login is not possible (e.g., 2FA), the script will wait for
    manual login up to 5 minutes.
    """
    print(f"Attempting Google login for: {email}")
    try:
        google_btn = page.locator('button:has-text("Continue with Google")')
        if google_btn.is_visible():
            google_btn.click()
            page.wait_for_url(lambda url: "accounts.google.com" in url, timeout=30000)
            time.sleep(2)

        account_entry = page.locator(
            f'div[role="link"]:has-text("{email}"), div[data-identifier="{email}"]'
        )
        if account_entry.is_visible():
            print(f"  - Selecting existing account: {email}")
            account_entry.click()
        else:
            use_another = page.locator('div[role="link"]:has-text("Use another account")')
            if use_another.is_visible():
                use_another.click()
                time.sleep(1)

            email_field = page.locator('input[type="email"]')
            if email_field.is_visible():
                print(f"  - Entering email: {email}")
                email_field.fill(email)
                page.locator('button:has-text("Next")').click()
                time.sleep(2)

        page.wait_for_selector('input[type="password"]', timeout=30000)
        print("  - Entering password...")
        page.locator('input[type="password"]').fill(password)
        page.locator('button:has-text("Next")').filter(
            has_not=page.locator('[aria-hidden="true"]')
        ).last.click()

        print("  - Authentication submitted. Waiting for KBase interface...")
        page.wait_for_selector(
            'a:has-text("New Narrative"), button:has-text("Add Data"), #user-menu-button',
            timeout=120000
        )
        print("  - Login successful!")
    except Exception as e:
        print(f"  - Automated login failed: {str(e)}")
        print("  - Falling back: Please complete login manually in the browser window.")
        page.wait_for_selector(
            'a:has-text("New Narrative"), button:has-text("Add Data")',
            timeout=300000
        )


# ==============================================================================
# MAIN UPLOAD FUNCTION
# ==============================================================================

def run_kbase_upload(
    csv_path,
    narrative_url,
    user_data_dir,
    email=None,
    password=None,
    narrative_name=None,
    acc_col=DEFAULT_ACC_COL,
    url_col=DEFAULT_URL_COL,
    url_col_2=DEFAULT_URL_COL2,
    country_col=DEFAULT_COUNTRY_COL,
    city_col=DEFAULT_CITY_COL,
    log_file=DEFAULT_LOG_FILE,
):
    """
    Main entry point for the upload automation.

    Args:
        csv_path       : Path to the CSV file with FTP links.
        narrative_url  : Direct URL to the KBase Narrative (alternative to narrative_name).
        user_data_dir  : Path to the persistent Chromium session directory.
        email          : Google email for KBase login (optional if already logged in).
        password       : Google password for KBase login (optional if already logged in).
        narrative_name : The narrative name to search for on the dashboard.
        acc_col        : CSV column name for sample accession/ID.
        url_col        : CSV column name for the forward/primary FTP URL.
        url_col_2      : CSV column name for the reverse/secondary FTP URL (optional; paired-end reads).
        country_col    : CSV column name for country (display only).
        city_col       : CSV column name for city (display only).
        log_file       : Path to the deduplication tracking log file.
    """
    # Ensure logs directory exists
    os.makedirs(DEFAULT_LOGS_DIR, exist_ok=True)

    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at '{csv_path}'")
        print("Tip: run with --csv path/to/your/file.csv")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    # Validate required columns
    if acc_col not in df.columns:
        print(f"Error: Accession column '{acc_col}' not found in CSV.")
        print(f"Available columns: {list(df.columns)}")
        print(f"Use --acc-col to specify the correct column name.")
        sys.exit(1)
    if url_col not in df.columns:
        print(f"Error: URL column '{url_col}' not found in CSV.")
        print(f"Available columns: {list(df.columns)}")
        print(f"Use --url-col to specify the correct column name.")
        sys.exit(1)

    # Load deduplication log
    processed_accessions = set()
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            processed_accessions = {line.strip() for line in f if line.strip()}
        print(f"Loaded {len(processed_accessions)} already-processed samples from log.")

    with sync_playwright() as p:
        print(f"Starting browser with persistent session in: {user_data_dir}")
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=["--no-sandbox"]
        )
        page = context.new_page()

        # --- Session check ---
        print(f"Checking session status via dashboard: {DEFAULT_DASHBOARD_URL}")
        try:
            page.goto(DEFAULT_DASHBOARD_URL, timeout=60000)
            time.sleep(3)
            check_for_unauthorized_popups(page)
        except Exception as e:
            print(f"Warning: Initial session check failed: {str(e)}")

        is_logged_out = (
            "login" in page.url
            or page.locator('button:has-text("Sign In")').is_visible()
            or page.locator('button:has-text("Continue with Google")').is_visible()
        )

        if is_logged_out:
            print("\n" + "=" * 50)
            if email and password:
                print(f"AUTOMATED LOGIN: Signing in as {email}...")
                handle_google_login(page, email, password)
            else:
                print("ACTION REQUIRED: Please sign in to KBase in the browser window.")
                print("The script will wait up to 5 minutes.")
                page.wait_for_selector('button:has-text("Add Data")', timeout=300000)
            print("=" * 50 + "\n")
        else:
            print("Session detected (Already logged in). Proceeding...")

        # --- Navigate to the target Narrative ---
        if narrative_name:
            print(f"Preparing to select narrative '{narrative_name}'...")
            if "narrative.kbase.us/narratives" not in page.url:
                page.goto(DEFAULT_DASHBOARD_URL)
            try:
                page.wait_for_selector(
                    'a:has-text("Narratives"), div:has-text("Narrative Navigator")',
                    timeout=60000
                )
                print("  - Dashboard loading signals detected.")
            except Exception:
                print("  - Warning: Dashboard took long to respond. Continuing...")
            new_page = open_narrative_by_name(page, context, narrative_name)
            if new_page:
                page = new_page
        elif narrative_url and page.url != narrative_url:
            print(f"Navigating to Narrative URL: {narrative_url}...")
            page.goto(narrative_url)
            wait_for_kbase_ready(page)

        if "/narrative/" not in page.url:
            print(f"[ERROR] Not on a Narrative page (Current URL: {page.url}). Aborting.")
            context.close()
            sys.exit(1)

        # --- Main upload loop ---
        total_samples = len(df)
        for index, row in df.iterrows():
            sample_acc = str(row.get(acc_col, f"Sample_{index}"))

            # Skip already-processed samples
            if sample_acc in processed_accessions:
                print(f"[{index+1}/{total_samples}] Skipping: {sample_acc} (already in log)")
                continue

            country = str(row.get(country_col, "")) if country_col in df.columns else ""
            city    = str(row.get(city_col, ""))    if city_col in df.columns else ""
            label_parts = [p for p in [country, city] if p and p != "nan"]
            sample_label = f"{sample_acc} ({', '.join(label_parts)})" if label_parts else sample_acc

            ftp1 = row.get(url_col)
            if pd.isna(ftp1) or str(ftp1).strip() == "":
                print(f"[{index+1}/{total_samples}] Skipping {sample_label}: No URL available.")
                continue

            print(f"[{index+1}/{total_samples}] Processing: {sample_label}")

            try:
                wait_for_kbase_ready(page, timeout=30000)
                check_for_unauthorized_popups(page)

                # 1. Open 'Add Data' panel if not already open
                if not page.locator('div[data-test-id="tab-import"]').is_visible():
                    page.wait_for_selector('#kb-loading-blocker', state="hidden", timeout=10000)
                    print("  - Opening 'Add Data' panel...")
                    page.locator(
                        'button[data-test-id="add-data-button"], button:has-text("Add Data")'
                    ).first.click()
                    page.wait_for_selector('div[data-test-id="tab-import"]', timeout=20000)

                # 2. Click 'Upload with URL' to add a new App Cell
                print("  - Clicking 'Upload with URL' to add app cell...")
                page.locator('div[data-test-id="tab-import"]').click()
                page.locator('button.web_upload_div').click()

                # 3. Wait for the App Cell to initialise
                print("  - Waiting for App Cell to initialize...")
                param_selector = 'div[data-parameter="download_type"]'
                page.wait_for_selector(param_selector, timeout=30000)
                app_cell = page.locator(f'.kb-app-cell:has({param_selector})').last
                app_cell.scroll_into_view_if_needed()

                # 3a. Select 'FTP Link' from the URL-type dropdown
                print("  - Selecting 'FTP' URL type...")
                url_type_container = app_cell.locator(f'div[data-parameter="download_type"]')
                url_type_container.wait_for(state="visible", timeout=30000)
                select2_box = url_type_container.locator('.select2-selection').first
                select2_box.scroll_into_view_if_needed()
                time.sleep(1)
                select2_box.click(force=True)
                print("    - Waiting for select2 results...")
                page.wait_for_selector('.select2-results__option', timeout=10000)
                page.locator('.select2-results__option:has-text("FTP Link")').click()
                time.sleep(1)

                # 3b. Add URL rows and fill in the FTP link(s)
                url_container = app_cell.locator('div[data-parameter="urls_to_add_web_unpack"]')

                # --- Forward / primary read (ftp_link_1) ---
                print("  - Adding forward URL (read 1)...")
                app_cell.locator('button:has(.fa-plus-circle)').click()
                url_field = url_container.locator('input[data-element="input"]').last
                url_field.wait_for(state="visible", timeout=10000)
                url_field.fill(str(ftp1).strip())
                url_field.evaluate(
                    "el => { el.blur(); el.dispatchEvent(new Event('change', { bubbles: true })); }"
                )
                time.sleep(1)

                # --- Reverse / secondary read (ftp_link_2, optional) ---
                ftp2 = row.get(url_col_2) if url_col_2 and url_col_2 in df.columns else None
                if ftp2 and not pd.isna(ftp2) and str(ftp2).strip():
                    print("  - Adding reverse URL (read 2)...")
                    app_cell.locator('button:has(.fa-plus-circle)').click()
                    url_field_2 = url_container.locator('input[data-element="input"]').last
                    url_field_2.wait_for(state="visible", timeout=10000)
                    url_field_2.fill(str(ftp2).strip())
                    url_field_2.evaluate(
                        "el => { el.blur(); el.dispatchEvent(new Event('change', { bubbles: true })); }"
                    )
                    time.sleep(1)

                # Final validation trigger — give KBase a moment to enable Run
                print("    - Triggering final validation...")
                time.sleep(2)

                # 4. Click 'Run'
                print("  - Submitting job (Clicking 'Run')...")
                try:
                    run_btn_selector = 'button[data-button="runApp"]:not(.hidden)'
                    page.wait_for_selector(run_btn_selector, state="visible", timeout=30000)
                    current_app_cell = page.locator(f'.kb-app-cell:has({param_selector})').last
                    run_btn = current_app_cell.locator(run_btn_selector)
                    for _ in range(15):
                        btn_class = run_btn.get_attribute("class") or ""
                        if not run_btn.get_attribute("disabled") and "hidden" not in btn_class:
                            print("    - Run button is visible and enabled.")
                            break
                        time.sleep(1)
                    run_btn.click(force=True)
                except Exception as e:
                    print(f"    - [RETRY] Falling back to global Run button: {str(e)}")
                    page.locator('button[data-button="runApp"]:not(.hidden)').last.click(force=True)

                # 5. Confirm submission
                print("  - Waiting for submission confirmation...")
                try:
                    page.wait_for_selector(
                        '.kb-rcp-status__container:has-text("running"), '
                        '.kb-rcp-status__container:has-text("submitted"), '
                        '.kb-app-cell-btn[data-button="jobStatus"]',
                        timeout=20000
                    )
                    print(f"  - [SUCCESS] Job submitted for {sample_label}")
                    processed_accessions.add(sample_acc)
                    with open(log_file, 'a') as f:
                        f.write(f"{sample_acc}\n")
                except Exception:
                    print(f"  - [WARNING] Could not confirm submission for {sample_label}, but Run was clicked.")

                time.sleep(10)

            except Exception as e:
                print(f"  - [ERROR] processing {sample_label}: {str(e)}")
                try:
                    screenshot_path = os.path.join(DEFAULT_LOGS_DIR, f"error_{sample_acc}.png")
                    page.screenshot(path=screenshot_path)
                    print(f"    - Screenshot saved: {screenshot_path}")
                except:
                    pass
                try:
                    close_btn = page.locator('button:has-text("Close")').first
                    if close_btn.is_visible():
                        close_btn.click()
                except:
                    pass
                if "Timeout" in str(e):
                    print("  - Timeout detected. Recovering by refreshing...")
                    page.reload()
                    page.wait_for_selector('button:has-text("Add Data")', timeout=60000)

        print("\nAll samples processed.")
        print("You can close the browser window now.")
        time.sleep(10)
        context.close()


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "kbase_uploader — Automate bulk FTP imports into a KBase Narrative.\n"
            "Configure via .env file (see .env.example) or pass arguments directly."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults from .env:
  python kbase_uploader.py

  # Specify a different CSV and narrative:
  python kbase_uploader.py --csv my_samples.csv --narrative "My Narrative"

  # Override CSV column names (if your CSV uses different headers):
  python kbase_uploader.py --acc-col sample_id --url-col ftp_url

  # Use a direct narrative URL instead of searching by name:
  python kbase_uploader.py --narrative-url https://narrative.kbase.us/narrative/12345
        """
    )

    parser.add_argument("--csv",           default=DEFAULT_CSV,            help="Path to input CSV file (default: from .env KBASE_CSV_PATH)")
    parser.add_argument("--narrative",     default=DEFAULT_NARRATIVE_NAME, help="Exact Narrative name to search on the dashboard")
    parser.add_argument("--narrative-url", default=DEFAULT_NARRATIVE_URL,  help="Direct URL to the Narrative (alternative to --narrative)")
    parser.add_argument("--user-dir",      default=DEFAULT_USER_DIR,       help="Path to browser session directory (default: ./kbase_user_session)")
    parser.add_argument("--email",         default=DEFAULT_su chats EMAIL,          help="Google email for KBase login (optional if session exists)")
    parser.add_argument("--password",      default=DEFAULT_PASSWORD,       help="Google password for KBase login (optional if session exists)")
    parser.add_argument("--acc-col",       default=DEFAULT_ACC_COL,        help=f"CSV column for sample accession/ID (default: {DEFAULT_ACC_COL})")
    parser.add_argument("--url-col",       default=DEFAULT_URL_COL,        help=f"CSV column for forward/primary FTP URL (default: {DEFAULT_URL_COL})")
    parser.add_argument("--url-col-2",     default=DEFAULT_URL_COL2,       help=f"CSV column for reverse/secondary FTP URL for paired-end reads (default: {DEFAULT_URL_COL2}, omit if single-end)")
    parser.add_argument("--country-col",   default=DEFAULT_COUNTRY_COL,    help=f"CSV column for country label (default: {DEFAULT_COUNTRY_COL})")
    parser.add_argument("--city-col",      default=DEFAULT_CITY_COL,       help=f"CSV column for city label (default: {DEFAULT_CITY_COL})")
    parser.add_argument("--log-file",      default=DEFAULT_LOG_FILE,       help="Path to the deduplication log file")

    args = parser.parse_args()

    if not args.narrative and not args.narrative_url:
        print("Error: You must specify either --narrative or --narrative-url.")
        print("  Example: python kbase_uploader.py --narrative 'My Narrative'")
        sys.exit(1)

    run_kbase_upload(
        csv_path       = args.csv,
        narrative_url  = args.narrative_url,
        user_data_dir  = args.user_dir,
        email          = args.email,
        password       = args.password,
        narrative_name = args.narrative,
        acc_col        = args.acc_col,
        url_col        = args.url_col,
        url_col_2      = args.url_col_2,
        country_col    = args.country_col,
        city_col       = args.city_col,
        log_file       = args.log_file,
    )
