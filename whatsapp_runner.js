/**
 * Unified WhatsApp Outreach Runner Engine
 * Supports CLI arguments, non-interactive batch runs, dry-runs, test message sending,
 * and structured JSON streaming for Web Dashboard integration.
 */

const path = require('path');
const fs = require('fs');
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

let config;
try {
  config = require('./config.json');
} catch (_) {
  config = require('./config.example.json');
}
const leadLoader = require('./leadLoader');
const { formatWhatsAppNumber } = require('./phoneFormatter');
const { getPersonalizedMessage, templates } = require('./templates');
const historyManager = require('./historyManager');

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function getRandomDelay(minSec, maxSec) {
  const min = minSec * 1000;
  const max = maxSec * 1000;
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function emitEvent(data) {
  console.log(JSON.stringify(data));
}

/**
 * Perform dry-run and return statistics and sample previews
 */
async function runDryRun(filePath, onlyNoWeb = true, sampleLimit = 5) {
  try {
    const exportsPath = config.scraperExportsPath || './exports';
    const available = leadLoader.listExportFiles(exportsPath);
    let targetFile = filePath;

    if (!targetFile || targetFile === 'latest' || targetFile === 'master') {
      const master = available.find(f => f.filename.includes('Master_CRM'));
      targetFile = master ? master.fullPath : available[0]?.fullPath;
    }

    if (!targetFile || !fs.existsSync(targetFile)) {
      emitEvent({ type: 'error', message: `Target file not found: ${targetFile || 'No files in exports'}` });
      return;
    }

    const rawLeads = await leadLoader.loadLeads(targetFile);
    const targetLeads = onlyNoWeb ? rawLeads.filter(l => !l.hasWebsite) : rawLeads;

    let readyToSend = 0;
    let alreadySent = 0;
    const samples = [];

    for (let i = 0; i < targetLeads.length; i++) {
      const lead = targetLeads[i];
      const formatted = formatWhatsAppNumber(lead.phone, config.defaultCountryCode);
      if (!formatted) continue;

      if (historyManager.isAlreadyMessaged(formatted.cleanNumber)) {
        alreadySent++;
        continue;
      }

      if (samples.length < sampleLimit) {
        samples.push({
          index: samples.length + 1,
          name: lead.name,
          phone: lead.phone,
          formattedPhone: formatted.display,
          address: lead.address,
          message: getPersonalizedMessage(lead, samples.length, config.senderName)
        });
      }
      readyToSend++;
    }

    emitEvent({
      type: 'dry_run_result',
      filename: path.basename(targetFile),
      fullPath: targetFile,
      totalInFile: rawLeads.length,
      filteredCount: targetLeads.length,
      alreadySent,
      readyToSend,
      samples
    });
  } catch (err) {
    emitEvent({ type: 'error', message: err.message });
  }
}

/**
 * Return current stats and files
 */
function getStatusInfo() {
  const stats = historyManager.getStats();
  const files = leadLoader.listExportFiles(config.scraperExportsPath || './exports');
  const authSessionExists = fs.existsSync(path.join(__dirname, '.wwebjs_auth', 'session'));
  emitEvent({
    type: 'status_info',
    stats,
    filesCount: files.length,
    authSessionExists,
    files: files.map(f => ({
      name: f.filename,
      sizeKB: (f.size / 1024).toFixed(1),
      lastModified: f.lastModified
    }))
  });
}

/**
 * Send a single test message
 */
async function sendTestMessage(targetPhone, senderName) {
  const name = senderName || config.senderName || 'Deepaktusir';
  const formatted = formatWhatsAppNumber(targetPhone, config.defaultCountryCode);
  if (!formatted) {
    emitEvent({ type: 'error', message: `Invalid phone format: ${targetPhone}` });
    return;
  }

  emitEvent({ type: 'log', message: `Initializing WhatsApp client to send test message to ${formatted.display}...` });

  const client = new Client({
    authStrategy: new LocalAuth({
      dataPath: path.join(__dirname, '.wwebjs_auth')
    }),
    puppeteer: {
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    }
  });

  client.on('qr', qr => {
    emitEvent({ type: 'qr_required', message: 'Scan the QR code to link WhatsApp' });
    qrcode.generate(qr, { small: true });
  });

  client.on('ready', async () => {
    emitEvent({ type: 'log', message: 'WhatsApp client is ready. Verifying number registration...' });
    try {
      const isRegistered = await client.isRegisteredUser(formatted.chatId);
      if (!isRegistered) {
        emitEvent({ type: 'error', message: `Number ${formatted.display} is not registered on WhatsApp.` });
        await client.destroy();
        return;
      }

      const sampleLead = {
        name: 'Sample Property Consultant',
        address: 'Sector 14, Sonipat',
        rating: '4.9',
        category: 'Real Estate Consultant',
        hasWebsite: false
      };
      const testMsg = `[TEST MESSAGE - PropLead Outreach]\n\n` + getPersonalizedMessage(sampleLead, 0, name);

      await client.sendMessage(formatted.chatId, testMsg);
      emitEvent({ type: 'test_sent_success', phone: formatted.display, message: 'Test message sent successfully!' });
    } catch (err) {
      emitEvent({ type: 'error', message: `Failed to send test message: ${err.message}` });
    } finally {
      try { await client.destroy(); } catch (_) {}
    }
  });

  client.on('auth_failure', msg => {
    emitEvent({ type: 'error', message: `Auth failure: ${msg}` });
  });

  try {
    await client.initialize();
  } catch (err) {
    emitEvent({ type: 'error', message: `Client init error: ${err.message}` });
  }
}

/**
 * Run campaign with full logging and anti-ban safeguards
 */
async function runCampaign(filePath, batchLimit = 20, minDelay = 25, maxDelay = 50, onlyNoWeb = true, senderName = 'Deepaktusir') {
  try {
    const exportsPath = config.scraperExportsPath || './exports';
    const available = leadLoader.listExportFiles(exportsPath);
    let targetFile = filePath;

    if (!targetFile || targetFile === 'latest' || targetFile === 'master') {
      const master = available.find(f => f.filename.includes('Master_CRM'));
      targetFile = master ? master.fullPath : available[0]?.fullPath;
    }

    if (!targetFile || !fs.existsSync(targetFile)) {
      emitEvent({ type: 'error', message: `File not found: ${targetFile}` });
      return;
    }

    const rawLeads = await leadLoader.loadLeads(targetFile);
    const targetLeads = onlyNoWeb ? rawLeads.filter(l => !l.hasWebsite) : rawLeads;

    const queue = [];
    for (const lead of targetLeads) {
      const formatted = formatWhatsAppNumber(lead.phone, config.defaultCountryCode);
      if (!formatted) continue;

      if (!historyManager.isAlreadyMessaged(formatted.cleanNumber)) {
        queue.push({ lead, formatted });
      }
    }

    if (queue.length === 0) {
      emitEvent({ type: 'campaign_complete', success: 0, failed: 0, message: 'All target leads in this file have already been contacted!' });
      return;
    }

    const toProcess = queue.slice(0, batchLimit);
    emitEvent({
      type: 'campaign_start',
      file: path.basename(targetFile),
      batchSize: toProcess.length,
      totalQueue: queue.length,
      minDelay,
      maxDelay,
      senderName
    });

    const client = new Client({
      authStrategy: new LocalAuth({
        dataPath: path.join(__dirname, '.wwebjs_auth')
      }),
      puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
      }
    });

    client.on('qr', qr => {
      emitEvent({ type: 'qr_required', message: 'WhatsApp scan needed' });
      qrcode.generate(qr, { small: true });
    });

    client.on('auth_failure', msg => {
      emitEvent({ type: 'error', message: `WhatsApp auth failed: ${msg}` });
    });

    await new Promise((resolve, reject) => {
      client.on('ready', resolve);
      client.initialize().catch(reject);
    });

    emitEvent({ type: 'log', message: 'WhatsApp Client connected. Starting outbound queue...' });

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < toProcess.length; i++) {
      const { lead, formatted } = toProcess[i];
      const message = getPersonalizedMessage(lead, i, senderName);

      emitEvent({
        type: 'contact_progress',
        index: i + 1,
        total: toProcess.length,
        name: lead.name,
        phone: formatted.display,
        status: 'sending'
      });

      try {
        const isRegistered = await client.isRegisteredUser(formatted.chatId);
        if (!isRegistered) {
          historyManager.recordSent(lead, formatted.cleanNumber, 'FAILED', 'Not on WhatsApp');
          failCount++;
          emitEvent({
            type: 'contact_result',
            index: i + 1,
            total: toProcess.length,
            name: lead.name,
            phone: formatted.display,
            status: 'failed',
            reason: 'Number not on WhatsApp'
          });
          continue;
        }

        await client.sendMessage(formatted.chatId, message);
        historyManager.recordSent(lead, formatted.cleanNumber, 'SUCCESS');
        successCount++;

        emitEvent({
          type: 'contact_result',
          index: i + 1,
          total: toProcess.length,
          name: lead.name,
          phone: formatted.display,
          status: 'success'
        });

        if (i < toProcess.length - 1) {
          const delayMs = getRandomDelay(minDelay, maxDelay);
          const delaySec = Math.round(delayMs / 1000);
          emitEvent({ type: 'delay_start', seconds: delaySec });

          for (let s = delaySec; s > 0; s--) {
            await sleep(1000);
            emitEvent({ type: 'delay_tick', secondsRemaining: s - 1 });
          }
        }
      } catch (err) {
        historyManager.recordSent(lead, formatted.cleanNumber, 'FAILED', err.message);
        failCount++;
        emitEvent({
          type: 'contact_result',
          index: i + 1,
          total: toProcess.length,
          name: lead.name,
          phone: formatted.display,
          status: 'failed',
          reason: err.message
        });
      }
    }

    try { await client.destroy(); } catch (_) {}

    emitEvent({
      type: 'campaign_complete',
      success: successCount,
      failed: failCount,
      message: `Batch completed! Sent: ${successCount}, Failed: ${failCount}`
    });
  } catch (err) {
    emitEvent({ type: 'error', message: err.message });
  }
}

// Parse Command Line
const args = process.argv.slice(2);
const command = args[0];

if (command === '--status') {
  getStatusInfo();
} else if (command === '--dry-run') {
  const filePath = args[1];
  const onlyNoWeb = args[2] !== 'false';
  const limit = parseInt(args[3] || '5', 10);
  runDryRun(filePath, onlyNoWeb, limit);
} else if (command === '--test') {
  const phone = args[1];
  const sender = args[2];
  sendTestMessage(phone, sender);
} else if (command === '--campaign') {
  const filePath = args[1];
  const batchLimit = parseInt(args[2] || '20', 10);
  const minDelay = parseInt(args[3] || '25', 10);
  const maxDelay = parseInt(args[4] || '50', 10);
  const onlyNoWeb = args[5] !== 'false';
  const senderName = args[6] || config.senderName || 'Deepaktusir';
  runCampaign(filePath, batchLimit, minDelay, maxDelay, onlyNoWeb, senderName);
} else {
  getStatusInfo();
}
