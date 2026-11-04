const fs = require('fs');
const path = require('path');

const HISTORY_FILE = path.join(__dirname, 'sent_history.json');

class HistoryManager {
  constructor() {
    this.history = this.loadHistory();
  }

  loadHistory() {
    try {
      if (fs.existsSync(HISTORY_FILE)) {
        const raw = fs.readFileSync(HISTORY_FILE, 'utf8');
        return JSON.parse(raw);
      }
    } catch (err) {
      console.warn('⚠️ Could not load history file, starting fresh:', err.message);
    }
    return {};
  }

  saveHistory() {
    try {
      fs.writeFileSync(HISTORY_FILE, JSON.stringify(this.history, null, 2), 'utf8');
    } catch (err) {
      console.error('❌ Error saving history file:', err.message);
    }
  }

  isAlreadyMessaged(cleanNumber) {
    return Boolean(this.history[cleanNumber] && this.history[cleanNumber].status === 'SUCCESS');
  }

  recordSent(lead, cleanNumber, status, error = null) {
    this.history[cleanNumber] = {
      name: lead.name,
      phone: cleanNumber,
      timestamp: new Date().toISOString(),
      status: status, // 'SUCCESS' | 'FAILED'
      error: error
    };
    this.saveHistory();
  }

  getStats() {
    const records = Object.values(this.history);
    const successful = records.filter(r => r.status === 'SUCCESS').length;
    const failed = records.filter(r => r.status === 'FAILED').length;
    return {
      totalMessaged: records.length,
      successful,
      failed
    };
  }
}

module.exports = new HistoryManager();
