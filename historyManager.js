const fs = require('fs');
const path = require('path');

const HISTORY_FILE = path.join(__dirname, 'sent_history.json');
const DEAD_FILE = path.join(__dirname, 'dead_leads.json');

class HistoryManager {
  constructor() {
    this.history = this.loadHistory();
    this.deadLeads = this.loadDeadLeads();
  }

  loadHistory() {
    try {
      if (fs.existsSync(HISTORY_FILE)) {
        const raw = fs.readFileSync(HISTORY_FILE, 'utf8');
        const data = JSON.parse(raw);
        // Normalize older records if needed
        for (const phone in data) {
          const item = data[phone];
          if (!item.first_sent_at) item.first_sent_at = item.timestamp || new Date().toISOString();
          if (!item.last_sent_at) item.last_sent_at = item.timestamp || item.first_sent_at;
          if (item.follow_up_count === undefined) item.follow_up_count = 0;
          if (item.client_replied === undefined) item.client_replied = false;
          if (item.is_dead === undefined) item.is_dead = false;
        }
        return data;
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

  loadDeadLeads() {
    try {
      if (fs.existsSync(DEAD_FILE)) {
        const raw = fs.readFileSync(DEAD_FILE, 'utf8');
        return JSON.parse(raw);
      }
    } catch (err) {
      console.warn('⚠️ Could not load dead leads file:', err.message);
    }
    return {};
  }

  saveDeadLeads() {
    try {
      fs.writeFileSync(DEAD_FILE, JSON.stringify(this.deadLeads, null, 2), 'utf8');
    } catch (err) {
      console.error('❌ Error saving dead leads file:', err.message);
    }
  }

  isDead(cleanNumber) {
    if (!cleanNumber) return false;
    const clean = String(cleanNumber).replace(/\D/g, '');
    const key10 = clean.slice(-10);

    for (const dPhone in this.deadLeads) {
      const dClean = String(dPhone).replace(/\D/g, '');
      if (dClean === clean || (key10 && dClean.endsWith(key10))) {
        return true;
      }
    }
    return Boolean(this.history[clean]?.is_dead);
  }

  markDead(cleanNumber, name = '', reason = 'Max 2 follow-ups completed with no reply') {
    const clean = String(cleanNumber).replace(/\D/g, '');
    this.deadLeads[clean] = {
      phone: clean,
      name: name || this.history[clean]?.name || 'Unknown',
      reason,
      added_at: new Date().toISOString(),
      follow_up_count: this.history[clean]?.follow_up_count || 2
    };

    if (this.history[clean]) {
      this.history[clean].is_dead = true;
      this.history[clean].chat_status = 'DEAD';
    }

    this.saveDeadLeads();
    this.saveHistory();
  }

  reviveDead(cleanNumber) {
    const clean = String(cleanNumber).replace(/\D/g, '');
    const key10 = clean.slice(-10);

    // Delete matching keys from dead leads
    let removed = false;
    for (const dPhone in this.deadLeads) {
      const dClean = String(dPhone).replace(/\D/g, '');
      if (dClean === clean || (key10 && dClean.endsWith(key10))) {
        delete this.deadLeads[dPhone];
        removed = true;
      }
    }

    if (this.history[clean]) {
      this.history[clean].is_dead = false;
      this.history[clean].client_replied = true;
      this.history[clean].chat_status = 'REPLIED';
      this.history[clean].last_reply_at = new Date().toISOString();
    }

    this.saveDeadLeads();
    this.saveHistory();
    return removed;
  }

  isAlreadyMessaged(cleanNumber) {
    return Boolean(this.history[cleanNumber] && this.history[cleanNumber].status === 'SUCCESS');
  }

  recordSent(lead, cleanNumber, status, error = null, msgType = 'initial') {
    const now = new Date().toISOString();
    const clean = String(cleanNumber).replace(/\D/g, '');
    const existing = this.history[clean];

    if (existing) {
      existing.status = status;
      existing.error = error;
      existing.last_sent_at = now;

      if (msgType === 'follow_up' && status === 'SUCCESS') {
        existing.follow_up_count = (existing.follow_up_count || 0) + 1;
        existing.message_count = (existing.message_count || 1) + 1;

        // If completed 2 follow-ups (total 3 messages: 1 initial + 2 follow-ups) with no reply
        if (existing.follow_up_count >= 2 && !existing.client_replied) {
          this.markDead(clean, lead.name, 'Max 2 follow-ups completed without reply');
          return;
        }
      }
    } else {
      this.history[clean] = {
        name: lead.name,
        phone: clean,
        first_sent_at: now,
        last_sent_at: now,
        timestamp: now,
        message_count: 1,
        follow_up_count: 0,
        client_replied: false,
        chat_status: 'SENT',
        is_dead: false,
        status: status,
        error: error
      };
    }

    this.saveHistory();
  }

  updateChatStatus(cleanNumber, { seen, ack, clientReplied, lastReplyText, lastReplyTime }) {
    const clean = String(cleanNumber).replace(/\D/g, '');
    const existing = this.history[clean];
    if (!existing) return;

    if (clientReplied) {
      existing.client_replied = true;
      existing.last_reply_text = lastReplyText || existing.last_reply_text || '';
      existing.last_reply_at = lastReplyTime || new Date().toISOString();
      existing.chat_status = 'REPLIED';
      // Automatically revive if they were in the dead list!
      if (this.isDead(clean)) {
        this.reviveDead(clean);
      }
    } else if (seen) {
      existing.chat_seen = true;
      existing.ack = ack;
      if (existing.chat_status !== 'DEAD') {
        existing.chat_status = 'SEEN';
      }
    } else if (ack) {
      existing.ack = ack;
    }

    this.saveHistory();
  }

  getFollowUpQueue(maxHoursWait = 24) {
    const now = Date.now();
    const waitMs = maxHoursWait * 60 * 60 * 1000;
    const queue = [];

    for (const phone in this.history) {
      const item = this.history[phone];
      // Skip failed, dead, or already replied leads
      if (item.status !== 'SUCCESS') continue;
      if (item.client_replied) continue;
      if (item.is_dead || this.isDead(phone)) continue;
      if ((item.follow_up_count || 0) >= 2) continue;

      const lastSentMs = new Date(item.last_sent_at || item.first_sent_at || item.timestamp).getTime();
      const timeElapsedHours = Math.round((now - lastSentMs) / (1000 * 60 * 60));

      queue.push({
        phone: item.phone || phone,
        name: item.name || 'Business',
        follow_up_count: item.follow_up_count || 0,
        next_followup_num: (item.follow_up_count || 0) + 1,
        chat_seen: Boolean(item.chat_seen || item.ack === 3),
        first_sent_at: item.first_sent_at,
        last_sent_at: item.last_sent_at,
        hours_elapsed: timeElapsedHours,
        ready_now: (now - lastSentMs) >= waitMs
      });
    }

    // Sort by longest waiting first
    return queue.sort((a, b) => b.hours_elapsed - a.hours_elapsed);
  }

  getStats() {
    const records = Object.values(this.history);
    const successful = records.filter(r => r.status === 'SUCCESS').length;
    const failed = records.filter(r => r.status === 'FAILED').length;

    const deadCount = Object.keys(this.deadLeads).length;
    const clientReplied = records.filter(r => r.client_replied).length;
    const needsFollowUp1 = records.filter(r => r.status === 'SUCCESS' && (r.follow_up_count === 0 || !r.follow_up_count) && !r.client_replied && !r.is_dead && !this.isDead(r.phone)).length;
    const needsFollowUp2 = records.filter(r => r.status === 'SUCCESS' && r.follow_up_count === 1 && !r.client_replied && !r.is_dead && !this.isDead(r.phone)).length;

    return {
      totalMessaged: records.length,
      successful,
      failed,
      needsFollowUp1,
      needsFollowUp2,
      clientReplied,
      deadCount
    };
  }
}

module.exports = new HistoryManager();
