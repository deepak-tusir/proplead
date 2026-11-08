# PropLead & WhatsApp Outreach Hub (Unified Command Center)

Multi-Niche B2B Local Leads Scraper, Master CRM Database, and Automated Conversational WhatsApp Outreach Engine.

---

## Key Features

1. **Multi-Niche Google Maps Scraper (Python + Playwright)**:
   - Target across **16+ Curated High-Converting Business Niches**:
     - **Tier 1 (High-Ticket):** Real Estate, Interior Designers, Architects, Builders, Banquet Halls.
     - **Tier 2 (High-Trust Services):** Dental Clinics, Polyclinics, Immigration Consultants, Coaching Institutes, Wedding Planners.
     - **Tier 3 (Commercial Showrooms):** Hotels & Resorts, Used Car Dealers, Car Modification, Solar Dealers, Furniture, Travel.
     - **Custom Niche:** Search by any custom business keyword and city.
   - Harvests Business Name, Phone Number, Business Email, Website, Full Address, Rating, and Review count.
   - Formatted Excel (.xlsx) and CSV exports with direct WhatsApp links.

2. **Master CRM Lead Database (`crm_manager.py`)**:
   - Leads from all searches and cities automatically deduplicate and merge into `Master_CRM_Leads.xlsx`.
   - Niche Filter and Lead Status tracking (New Lead, Contacted, Follow Up, Meeting Scheduled, Converted, Not Interested).
   - WhatsApp outreach status indicator (Sent with timestamp or Unsent).

3. **Smart WhatsApp Outreach & Contextual Follow-up Engine (Node.js + `whatsapp-web.js`)**:
   - Niche-tailored, conversational outreach messages.
   - **Smart Follow-up System**: Max 2 follow-ups with contextual messaging (Blue Tick / Seen vs Unopened / Bump, plus a respectful Breakup pitch).
   - **Dead Leads Blacklist Vault**: Automatically isolates unresponsive leads after 2 follow-ups so they are never messaged again.
   - **Auto-Revival**: If any dead lead replies back on WhatsApp, they are automatically restored to active CRM.
   - **Anti-Ban Protections**: Random delays (25s - 50s), batch limits (10-30), WhatsApp number validation, deduplication against `sent_history.json`.
   - Saved login session (`.wwebjs_auth`) — no repeated QR scans required.

4. **Unified Web Dashboard (Browser GUI - `http://localhost:5000`)**:
   - Single browser command center:
     - **Tab 1: Lead Scraper**: Niche selector, live progress bar, activity feed, session preview table.
     - **Tab 2: Master CRM**: Niche & status filters, search, WhatsApp chat links, Excel download.
     - **Tab 3: WhatsApp Outreach**: Dry-run preview, test message to your phone, live campaign stream with countdown timer.
     - **Tab 4: Follow-ups & Dead Leads**: Chat status scanner, pending queue, dead leads vault, and manual revival.
   - **Auto-Backup & Reset System**: 1-click full ZIP archive backup with clean workspace reset.

---

## How to Run

### Method 1: Master Launcher (Recommended)
Double click:
```bat
start.bat
```
Select from the menu:
- **[1] Start Web Dashboard** (Opens browser interface)
- **[2] Run Lead Scraper** (Terminal CLI)
- **[3] Run WhatsApp Outreach Tool** (Terminal CLI)
- **[4] Open Exports Folder**
- **[5] Install / Verify Dependencies**

---

### Method 2: Direct Shortcuts
- **Web UI**: Double click `start_web_ui.bat` -> browser opens at `http://localhost:5000`.
- **Terminal Scraper**: Double click `run_scraper.bat`.
- **Terminal WhatsApp Outreach**: Double click `run_whatsapp.bat`.

---

## Project Structure

```
scrapper+whatsapp/
├── exports/                       # Scraped Excel files and Master CRM
│   ├── Master_CRM_Leads.xlsx      # Master deduplicated database
│   ├── Master_CRM_Leads.csv
│   └── ... (Session files)
├── backups/                       # Timestamped system ZIP backups
├── .wwebjs_auth/                  # WhatsApp saved authenticated session
├── scraper.py                     # Web scraping engine (Playwright)
├── crm_manager.py                 # Master CRM & deduplication logic
├── web_app.py                     # Web GUI (Flask + Tailwind CSS + SSE)
├── system_backup.py               # Auto-backup & workspace reset engine
├── niches_config.json             # Tier 1-3 niches and custom templates
├── whatsapp_runner.js             # WhatsApp engine runner (Web & CLI bridge)
├── index.js                       # Interactive CLI WhatsApp Outreach
├── leadLoader.js                  # Lead loader from ./exports
├── phoneFormatter.js              # Phone number normalizer
├── templates.js                   # Sales pitch & follow-up message templates
├── historyManager.js              # Sent tracking, follow-ups & dead leads logic
├── config.json                    # Outreach settings (delays, batch limits, sender)
├── start.bat                      # Master launcher menu
├── start_web_ui.bat               # Web GUI launcher
├── run_scraper.bat                # CLI Scraper launcher
├── run_whatsapp.bat               # CLI WhatsApp launcher
├── requirements.txt               # Python dependencies
└── package.json                   # Node.js dependencies
```

---

## Configuration (`config.json`)

```json
{
  "scraperExportsPath": "./exports",
  "defaultCountryCode": "91",
  "minDelaySeconds": 25,
  "maxDelaySeconds": 50,
  "defaultBatchLimit": 20,
  "onlyWithoutWebsite": true,
  "senderName": "Deepaktusir",
  "testPhoneNumber": ""
}
```

---

## Anti-Ban Safety Guidelines
1. Limit sending to **20-30 messages** per session.
2. Keep `minDelaySeconds` at 25+ seconds and `maxDelaySeconds` at 50+ seconds.
3. Use **"Preview / Dry Run"** to inspect targets before launching live outreach.
4. Send a test message to your own number to verify connectivity.

---

## License & Legal Terms

Copyright (c) 2026 Deepak Tusir. All Rights Reserved.

This project is licensed under a **Source-Available Non-Commercial License**.
- **Permitted**: Individual, educational, and personal non-commercial use.
- **Strictly Prohibited**: Commercial sale, white-labeling, repackaging, or reselling of this software or derivatives without explicit prior written authorization from Deepak Tusir.

See the full [LICENSE](LICENSE) file for complete legal terms.
