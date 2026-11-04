const readline = require('readline');
const path = require('path');
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

const fs = require('fs');

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

let client = null;
let isClientReady = false;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function getRandomDelay(minSec, maxSec) {
  const min = minSec * 1000;
  const max = maxSec * 1000;
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function prompt(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  return new Promise(resolve => {
    rl.question(question, answer => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

/**
 * Initializes and starts the WhatsApp Web client
 */
function initWhatsAppClient() {
  return new Promise((resolve, reject) => {
    if (client && isClientReady) {
      return resolve(client);
    }

    console.log('\n========================================');
    console.log('🔄 Initializing WhatsApp Web Client...');
    console.log('========================================');

    client = new Client({
      authStrategy: new LocalAuth({
        dataPath: path.join(__dirname, '.wwebjs_auth')
      }),
      puppeteer: {
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-extensions',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote'
        ]
      }
    });

    client.on('qr', qr => {
      console.log('\n======================================================');
      console.log('📱 SCAN THIS QR CODE WITH YOUR WHATSAPP APP');
      console.log('👉 WhatsApp -> Linked Devices -> Link a Device');
      console.log('======================================================\n');
      qrcode.generate(qr, { small: true });
    });

    client.on('authenticated', () => {
      console.log('✅ Session Authenticated successfully!');
    });

    client.on('auth_failure', msg => {
      console.error('❌ Authentication failed:', msg);
      reject(new Error(msg));
    });

    client.on('ready', () => {
      isClientReady = true;
      console.log('\n🚀 WhatsApp Client is READY and CONNECTED!\n');
      resolve(client);
    });

    client.on('disconnected', reason => {
      isClientReady = false;
      console.log('⚠️ WhatsApp Client disconnected:', reason);
    });

    client.initialize().catch(err => {
      console.error('❌ Error during client.initialize():', err.message);
      reject(err);
    });
  });
}

/**
 * Helper to get the lead file to process
 */
async function selectLeadFile() {
  const files = leadLoader.listExportFiles(config.scraperExportsPath);
  if (files.length === 0) {
    console.log(`\n❌ No export files (.csv or .xlsx) found in: ${config.scraperExportsPath}`);
    return null;
  }

  console.log('\n📂 Available Scraped Files:');
  files.forEach((f, idx) => {
    const sizeKB = (f.size / 1024).toFixed(1);
    const dateStr = new Date(f.lastModified).toLocaleString();
    console.log(`  [${idx + 1}] ${f.filename} (${sizeKB} KB - ${dateStr})`);
  });

  const choice = await prompt(`\nSelect file [1-${files.length}] (Default 1): `);
  const selectedIndex = choice ? parseInt(choice, 10) - 1 : 0;

  if (selectedIndex >= 0 && selectedIndex < files.length) {
    return files[selectedIndex].fullPath;
  } else {
    console.log('⚠️ Invalid selection, using latest file.');
    return files[0].fullPath;
  }
}

/**
 * Preview / Dry-run messages without sending
 */
async function handleDryRun() {
  const filePath = await selectLeadFile();
  if (!filePath) return;

  console.log(`\n📖 Loading leads from: ${path.basename(filePath)}...`);
  const rawLeads = await leadLoader.loadLeads(filePath);
  
  const hasWebsiteCount = rawLeads.filter(l => l.hasWebsite).length;
  const targetLeads = config.onlyWithoutWebsite 
    ? rawLeads.filter(l => !l.hasWebsite)
    : rawLeads;

  console.log(`📊 Total scraped leads in file: ${rawLeads.length}`);
  if (config.onlyWithoutWebsite) {
    console.log(`🌐 Filter [Only Without Website]: ON`);
    console.log(`   - Excluded (Already have website): ${hasWebsiteCount}`);
    console.log(`   - Eligible targets (No website):   ${targetLeads.length}`);
  }

  let validCount = 0;
  let alreadySentCount = 0;

  console.log('\n--- SAMPLE WEB DEV OUTREACH PREVIEW (First 3 Targets) ---');
  for (let i = 0; i < targetLeads.length; i++) {
    const lead = targetLeads[i];
    const formatted = formatWhatsAppNumber(lead.phone, config.defaultCountryCode);
    if (!formatted) continue;

    if (historyManager.isAlreadyMessaged(formatted.cleanNumber)) {
      alreadySentCount++;
      continue;
    }

    if (validCount < 3) {
      console.log(`\n--------------------------------------------------`);
      console.log(`👤 Target #${validCount + 1}: ${lead.name}`);
      console.log(`🌐 Website Status: NO WEBSITE`);
      console.log(`📞 Original Phone: ${lead.phone} -> Formatted: ${formatted.display} (${formatted.chatId})`);
      console.log(`📍 Address: ${lead.address}`);
      console.log(`💬 Message Preview:\n`);
      console.log(getPersonalizedMessage(lead, validCount, config.senderName));
      console.log(`--------------------------------------------------`);
    }
    validCount++;
  }

  console.log(`\n📈 Summary for ${path.basename(filePath)}:`);
  console.log(`  - Total scraped leads: ${rawLeads.length}`);
  console.log(`  - Leads with existing website (skipped): ${hasWebsiteCount}`);
  console.log(`  - Target leads without website: ${targetLeads.length}`);
  console.log(`  - Already messaged previously: ${alreadySentCount}`);
  console.log(`  - Ready to message in queue: ${validCount}`);
}

/**
 * Send a single test message to verify connection
 */
async function handleTestMessage() {
  await initWhatsAppClient();

  let targetPhone = config.testPhoneNumber;
  if (!targetPhone) {
    targetPhone = await prompt('Enter your phone number for test message (e.g. 9812345678): ');
  }

  const formatted = formatWhatsAppNumber(targetPhone, config.defaultCountryCode);
  if (!formatted) {
    console.log('❌ Invalid phone number format.');
    return;
  }

  const dummyLead = {
    name: 'Sample Property Consultant',
    address: 'Sector 14, Sonipat',
    rating: '4.8',
    category: 'Real Estate Consultant',
    hasWebsite: false
  };

  const testMessage = `[TEST MESSAGE - Web Development Pitch]\n\n` + getPersonalizedMessage(dummyLead, 0, config.senderName);

  console.log(`\n📤 Sending test message to ${formatted.display}...`);
  try {
    const isRegistered = await client.isRegisteredUser(formatted.chatId);
    if (!isRegistered) {
      console.log(`⚠️ Number ${formatted.display} is not registered on WhatsApp.`);
      return;
    }

    await client.sendMessage(formatted.chatId, testMessage);
    console.log(`✅ Test message successfully sent to ${formatted.display}! Check your WhatsApp.`);
  } catch (err) {
    console.error('❌ Failed to send test message:', err.message);
  }
}

/**
 * Run Outreach Campaign
 */
async function handleRunOutreach() {
  const filePath = await selectLeadFile();
  if (!filePath) return;

  const rawLeads = await leadLoader.loadLeads(filePath);
  console.log(`📊 Loaded ${rawLeads.length} total leads.`);

  // Filter leads without website if enabled
  const leads = config.onlyWithoutWebsite 
    ? rawLeads.filter(l => !l.hasWebsite)
    : rawLeads;

  console.log(`🎯 Targets without website: ${leads.length} (Skipped ${rawLeads.length - leads.length} with websites)`);

  // Filter out invalid and already messaged
  const queue = [];
  for (const lead of leads) {
    const formatted = formatWhatsAppNumber(lead.phone, config.defaultCountryCode);
    if (!formatted) continue;

    if (!historyManager.isAlreadyMessaged(formatted.cleanNumber)) {
      queue.push({ lead, formatted });
    }
  }

  if (queue.length === 0) {
    console.log('\n🎉 All target leads without a website in this file have already been messaged!');
    return;
  }

  console.log(`\n🎯 Filtered Contacts ready for outreach: ${queue.length}`);
  const batchInput = await prompt(`How many messages do you want to send in this batch? (Default: ${config.defaultBatchLimit}): `);
  const batchLimit = batchInput ? parseInt(batchInput, 10) : config.defaultBatchLimit;

  const toProcess = queue.slice(0, batchLimit);
  console.log(`\n⚠️ Safety & Pitch Confirmation:`);
  console.log(`  - Pitch: Web Development / Website Creation`);
  console.log(`  - Target batch: ${toProcess.length} businesses (All WITHOUT website)`);
  console.log(`  - Delay between messages: ${config.minDelaySeconds}s - ${config.maxDelaySeconds}s`);
  console.log(`  - Sender Signature: "${config.senderName}"`);

  const confirm = await prompt('\nType "START" to begin sending: ');
  if (confirm.toUpperCase() !== 'START') {
    console.log('❌ Outreach cancelled.');
    return;
  }

  await initWhatsAppClient();

  console.log('\n🚀 Starting Web Development WhatsApp outreach campaign...\n');

  let successCount = 0;
  let failCount = 0;

  for (let i = 0; i < toProcess.length; i++) {
    const { lead, formatted } = toProcess[i];
    const message = getPersonalizedMessage(lead, i, config.senderName);

    console.log(`\n[${i + 1}/${toProcess.length}] Processing: ${lead.name} (${formatted.display})`);

    try {
      // Check if number is on WhatsApp
      const isRegistered = await client.isRegisteredUser(formatted.chatId);
      if (!isRegistered) {
        console.log(`  ⚠️ Number ${formatted.display} is not registered on WhatsApp. Skipping.`);
        historyManager.recordSent(lead, formatted.cleanNumber, 'FAILED', 'Not on WhatsApp');
        failCount++;
        continue;
      }

      // Send message
      await client.sendMessage(formatted.chatId, message);
      historyManager.recordSent(lead, formatted.cleanNumber, 'SUCCESS');
      successCount++;
      console.log(`  ✅ Pitch sent successfully!`);

      // If there are more contacts, wait with countdown delay
      if (i < toProcess.length - 1) {
        const delayMs = getRandomDelay(config.minDelaySeconds, config.maxDelaySeconds);
        const delaySec = Math.round(delayMs / 1000);
        process.stdout.write(`  ⏳ Anti-ban safeguard: waiting ${delaySec}s before next contact... `);

        for (let s = delaySec; s > 0; s--) {
          await sleep(1000);
          process.stdout.write(`${s} `);
        }
        console.log(' Done.');
      }
    } catch (err) {
      console.error(`  ❌ Failed to send to ${formatted.display}:`, err.message);
      historyManager.recordSent(lead, formatted.cleanNumber, 'FAILED', err.message);
      failCount++;
    }
  }

  console.log('\n========================================');
  console.log('🏁 Batch Campaign Completed!');
  console.log(`  ✅ Successfully Sent: ${successCount}`);
  console.log(`  ❌ Failed / Skipped:  ${failCount}`);
  console.log('========================================\n');
}

/**
 * Display outreach stats
 */
function handleViewStats() {
  const stats = historyManager.getStats();
  console.log('\n📊 --- OUTREACH STATISTICS ---');
  console.log(`  Total Leads Contacted: ${stats.totalMessaged}`);
  console.log(`  Successful Deliveries:  ${stats.successful}`);
  console.log(`  Failed / Unregistered:  ${stats.failed}`);
  console.log('-------------------------------\n');
}

/**
 * Main Interactive Menu
 */
async function mainMenu() {
  while (true) {
    console.log('\n=============================================');
    console.log('   🤖 WHATSAPP WEB DEV OUTREACH TOOL         ');
    console.log('=============================================');
    console.log(`Filter: Targets WITHOUT Website Only (${config.onlyWithoutWebsite ? 'ON' : 'OFF'})`);
    console.log('---------------------------------------------');
    console.log('1. 📱 Connect & Authenticate WhatsApp (Scan QR)');
    console.log('2. 🔍 Preview & Dry-Run (Check messages without sending)');
    console.log('3. 🧪 Send Test Message to your own phone');
    console.log('4. 🚀 Run Lead Outreach Campaign (Batch sending)');
    console.log('5. 📊 View Outreach Statistics & History');
    console.log('6. 🚪 Exit');
    console.log('=============================================');

    const choice = await prompt('Select an option (1-6): ');

    switch (choice) {
      case '1':
        await initWhatsAppClient();
        break;
      case '2':
        await handleDryRun();
        break;
      case '3':
        await handleTestMessage();
        break;
      case '4':
        await handleRunOutreach();
        break;
      case '5':
        handleViewStats();
        break;
      case '6':
        console.log('\n👋 Exiting. Goodbye!');
        if (client) {
          try { await client.destroy(); } catch (_) {}
        }
        process.exit(0);
      default:
        console.log('⚠️ Invalid option. Please enter 1 to 6.');
    }
  }
}

mainMenu().catch(err => {
  console.error('Fatal Error:', err);
});
