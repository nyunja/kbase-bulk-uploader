let csvData = [];
let isRunning = false;

const csvFileInput = document.getElementById('csvFile');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const logContent = document.getElementById('logContent');
const doneCountEl = document.getElementById('doneCount');
const todoCountEl = document.getElementById('todoCount');
const progressBarFill = document.getElementById('progressBarFill');

// Initialize: Restore state from storage
document.addEventListener('DOMContentLoaded', async () => {
    const state = await chrome.storage.local.get(['csvData', 'fileName', 'isRunning', 'doneCount']);
    if (state.csvData && state.csvData.length > 0) {
        csvData = state.csvData;
        const done = state.doneCount || 0;
        
        document.getElementById('fileInfo').classList.remove('hidden');
        document.getElementById('fileName').textContent = state.fileName;
        document.getElementById('rowCount').textContent = `${csvData.length} records found`;
        document.getElementById('statusCard').classList.remove('hidden');
        document.getElementById('logCard').classList.remove('hidden');
        
        updateProgress(done, csvData.length);
        startBtn.disabled = false;
        
        if (state.isRunning) {
            isRunning = true;
            startBtn.classList.add('hidden');
            stopBtn.classList.remove('hidden');
            addLog('Resuming automation monitoring...', 'info');
        } else {
            addLog('State restored from memory. Ready to start.', 'success');
        }
    }
});

// Handle CSV selection
csvFileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (event) => {
    const text = event.target.result;
    parseCSV(text);
    
    // Persist to storage
    await chrome.storage.local.set({ 
        csvData, 
        fileName: file.name, 
        isRunning: false,
        doneCount: 0 
    });

    document.getElementById('fileInfo').classList.remove('hidden');
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('rowCount').textContent = `${csvData.length} records found`;
    document.getElementById('statusCard').classList.remove('hidden');
    document.getElementById('logCard').classList.remove('hidden');
    
    updateProgress(0, csvData.length);
    startBtn.disabled = false;
    addLog(`Loaded ${csvData.length} records from ${file.name}`, 'success');
  };
  reader.readAsText(file);
});

function parseCSV(text) {
  const lines = text.split(/\r?\n/);
  const headers = lines[0].split(',');
  
  csvData = lines.slice(1)
    .filter(line => line.trim().length > 0)
    .map(line => {
      const values = line.split(',');
      const obj = {};
      headers.forEach((header, i) => {
        obj[header.trim()] = values[i] ? values[i].trim() : '';
      });
      return obj;
    });
}

// Start Automation
startBtn.addEventListener('click', async () => {
  if (isRunning) return;
  isRunning = true;
  startBtn.classList.add('hidden');
  stopBtn.classList.remove('hidden');
  
  await chrome.storage.local.set({ isRunning: true });
  addLog('Searching for active tab...', 'info');
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab) {
        throw new Error('No active tab found.');
    }

    if (!tab.url.includes('kbase.us') && !tab.url.includes('google.com')) {
      addLog('Please open a KBase Narrative page first!', 'error');
      isRunning = false;
      stopBtn.click();
      return;
    }

    addLog(`Sending start signal to tab: ${tab.id}`, 'info');
    chrome.tabs.sendMessage(tab.id, { action: 'START', data: csvData }, (response) => {
        if (chrome.runtime.lastError) {
            addLog(`Error: ${chrome.runtime.lastError.message}`, 'error');
            addLog('Try refreshing the KBase page.', 'info');
            stopBtn.click();
        } else {
            addLog('Start signal acknowledged by content script.', 'success');
        }
    });
  } catch (err) {
      addLog(`Critical Error: ${err.message}`, 'error');
      stopBtn.click();
  }
});

// Stop Automation
stopBtn.addEventListener('click', async () => {
  isRunning = false;
  startBtn.classList.remove('hidden');
  stopBtn.classList.add('hidden');
  await chrome.storage.local.set({ isRunning: false });
  addLog('Automation stopped by user.', 'info');
  
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) chrome.tabs.sendMessage(tabs[0].id, { action: 'STOP' });
  });
});

// Reset storage
const resetButton = document.createElement('button');
resetButton.textContent = 'Clear Memory';
resetButton.className = 'btn btn-secondary';
resetButton.style.marginTop = '8px';
resetButton.onclick = async () => {
    await chrome.storage.local.clear();
    location.reload();
};
document.querySelector('footer').appendChild(resetButton);

// Listen for updates from content script
chrome.runtime.onMessage.addListener(async (message) => {
  if (message.action === 'LOG') {
    addLog(message.text, message.type);
  } else if (message.action === 'PROGRESS') {
    updateProgress(message.done, message.total);
    await chrome.storage.local.set({ doneCount: message.done });
  } else if (message.action === 'FINISHED') {
    isRunning = false;
    startBtn.classList.remove('hidden');
    stopBtn.classList.add('hidden');
    await chrome.storage.local.set({ isRunning: false });
    addLog('All tasks completed successfully!', 'success');
  }
});

function addLog(text, type = 'info') {
  const line = document.createElement('div');
  line.className = `log-line ${type}`;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
  logContent.appendChild(line);
  logContent.scrollTop = logContent.scrollHeight;
}

function updateProgress(done, total) {
  doneCountEl.textContent = done;
  todoCountEl.textContent = total - done;
  const percent = total > 0 ? (done / total) * 100 : 0;
  progressBarFill.style.width = `${percent}%`;
}

