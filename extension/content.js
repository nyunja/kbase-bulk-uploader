let isAutomationRunning = false;
let dataQueue = [];
let processIndex = 0;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'START') {
    log('Content script received START signal.', 'success');
    dataQueue = message.data;
    processIndex = 0;
    isAutomationRunning = true;
    startAutomationLoop();
    sendResponse({ status: 'started' });
  } else if (message.action === 'STOP') {
    isAutomationRunning = false;
    log('Automation stopped.', 'info');
    sendResponse({ status: 'stopped' });
  }
  return true; // Keep channel open for async if needed
});

async function startAutomationLoop() {
  if (window.location.hostname.includes('accounts.google.com')) {
    await handleGoogleLogin();
    return;
  }

  if (window.location.pathname.includes('/login')) {
    await handleKBaseLogin();
    return;
  }

  if (window.location.host.includes('narrative.kbase.us')) {
    for (; processIndex < dataQueue.length; processIndex++) {
      if (!isAutomationRunning) break;
      
      const row = dataQueue[processIndex];
      log(`Processing: ${row.ena_run_acc || 'Row ' + (processIndex + 1)}`, 'info');
      
      try {
        await processRow(row);
        chrome.runtime.sendMessage({ action: 'PROGRESS', done: processIndex + 1, total: dataQueue.length });
        await sleep(5000); // Wait for KBase to stabilize
      } catch (err) {
        log(`Error in row ${processIndex + 1}: ${err.message}`, 'error');
        // Continue to next row?
      }
    }
    
    if (isAutomationRunning) {
      chrome.runtime.sendMessage({ action: 'FINISHED' });
    }
  }
}

async function handleKBaseLogin() {
  log('Attempting KBase Google Login...', 'info');
  const googleBtn = await waitForElement('button[value="Google"]', 2000);
  if (googleBtn) {
    googleBtn.click();
  } else {
    log('Google login button not found.', 'error');
  }
}

async function handleGoogleLogin() {
  log('Selecting Google Account...', 'info');
  // Look for the specific account or the first one
  const account = await waitForElement('div[data-email="[EMAIL_ADDRESS]"]', 3000) 
                || await waitForElement('div[data-identifier="[EMAIL_ADDRESS]"]', 1000)
                || await waitForElement('[role="link"]', 2000);
                
  if (account) {
    account.click();
  } else {
    log('Account selector not found.', 'error');
  }
}

async function processRow(row) {
  // 1. Add Data
  const addDataBtn = await findElementByText('button', 'Add Data');
  if (!addDataBtn) throw new Error('Add Data button not found');
  addDataBtn.click();
  await sleep(1000);

  // 2. Import Tab
  const importTab = await findElementByText('a', 'Import');
  if (!importTab) throw new Error('Import tab not found');
  importTab.click();
  await sleep(1000);

  // 3. Upload with URL
  const uploadBtn = await findElementByText('button', 'Upload with URL');
  if (!uploadBtn) throw new Error('Upload with URL button not found');
  uploadBtn.click();
  log('  - App cell added', 'success');
  await sleep(3000);

  // 4. Find the cell (last container)
  const cells = document.querySelectorAll('.kb-app-cell-container');
  const currentCell = cells[cells.length - 1];
  if (!currentCell) throw new Error('Could not locate new app cell');

  // 5. Select URL type: FTP Link
  const select = currentCell.querySelector('select') || await waitForElement('select', 2000, currentCell);
  if (select) {
    select.value = 'ftp'; // Double check if value is 'ftp' or 'FTP Link'
    // KBase uses React/custom controls, might need to trigger change
    select.dispatchEvent(new Event('change', { bubbles: true }));
  } else {
    // Attempt by label
    const dropdown = await findElementByText('div', 'URL type', currentCell);
    if (dropdown) {
      // Logic for custom dropdown if needed
    }
  }

  // 6. Fill URL 1
  const inputs = currentCell.querySelectorAll('input[placeholder="URL"]');
  if (inputs.length > 0 && row.ftp_link_1) {
    inputs[0].value = row.ftp_link_1;
    inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
    log(`  - Link 1 set: ${row.ftp_link_1.substring(0, 30)}...`, 'success');
  }

  // 7. Fill URL 2 if exists
  if (row.ftp_link_2) {
    const plusBtn = await findElementByText('button', '+', currentCell);
    if (plusBtn) {
      plusBtn.click();
      await sleep(500);
      const newInputs = currentCell.querySelectorAll('input[placeholder="URL"]');
      if (newInputs.length > 1) {
        newInputs[1].value = row.ftp_link_2;
        newInputs[1].dispatchEvent(new Event('input', { bubbles: true }));
        log(`  - Link 2 set: ${row.ftp_link_2.substring(0, 30)}...`, 'success');
      }
    }
  }

  // 8. Run
  const runBtn = await findElementByText('button', 'Run', currentCell);
  if (runBtn) {
    runBtn.click();
    log('  - Run clicked', 'success');
  } else {
    throw new Error('Run button not found in cell');
  }
}

// Helpers
function log(text, type) {
  chrome.runtime.sendMessage({ action: 'LOG', text, type });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForElement(selector, timeout, parent = document) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const el = parent.querySelector(selector);
    if (el) return el;
    await sleep(200);
  }
  return null;
}

async function findElementByText(tag, text, parent = document) {
  const els = parent.querySelectorAll(tag);
  for (const el of els) {
    if (el.textContent.trim() === text || el.innerText.trim() === text) {
      return el;
    }
    // Deep search if text is inside a span etc
    if (el.querySelector('span') && el.querySelector('span').textContent.trim() === text) {
      return el;
    }
  }
  return null;
}
