# 🏢 PropLead & WhatsApp Outreach Hub (Unified Command Center)

Ek hi jagah se **Property Dealer Leads Scrape** karne, **Master CRM** me manage karne, aur unhe direct **WhatsApp Web Development Pitch** automate karne ka complete unified tool.

---

## 🌟 Key Features

1. **Google Maps Property Dealer Scraper (Python + Playwright)**:
   - Kisi bhi city ya locality (e.g., *South Delhi*, *Gurgaon*, *Sonipat*, *Bangalore*) se real estate dealers scrape karein.
   - Agency Name, Phone Number, Business Email, Website, Full Address, Star Rating & Review count nikalta hai.
   - Excel (`.xlsx`) and `.csv` formatted auto-exports with WhatsApp direct links.

2. **Master CRM Lead Database (`crm_manager.py`)**:
   - Sabhi cities ke leads automatically `Master_CRM_Leads.xlsx` me deduplicate hokar merge hote hain.
   - Lead Status management (`New Lead`, `Contacted`, `Follow Up`, `Meeting Scheduled`, `Converted`, `Not Interested`).
   - WhatsApp outreach status indicator (pata chal jata hai ki kis dealer ko WhatsApp message bheja ja chuka hai aur kisko nahi).

3. **WhatsApp Outreach Engine (Node.js + `whatsapp-web.js`)**:
   - Scraped leads ko customized website development / real estate portal pitch bhejne ka system.
   - **Anti-Ban Safeguards**: Random delays (25s - 50s), batch limits (10-30), WhatsApp number validation check, deduplication against `sent_history.json`.
   - **Filter targets**: Sirf unhi dealers ko message bhejta hai jinki website nahi hai (`onlyWithoutWebsite: true`).
   - Saved login session (`.wwebjs_auth`) — baar-baar QR code scan karne ki zaroorat nahi.

4. **Unified Web Dashboard (Browser GUI - `http://localhost:5000`)**:
   - Single browser tab me teeno tools:
     - **Tab 1: Lead Scraper**: Live progress bar, live logs stream.
     - **Tab 2: Master CRM**: Search, status dropdowns, WhatsApp chat quick links, Excel download.
     - **Tab 3: WhatsApp Outreach**: Dry-run preview, test message to your own phone, live automated campaign with real-time countdown timer.

---

## 🚀 How to Run (Kaise Chalayein)

### Method 1: Master Launcher (Recommended)
Double click karein:
```bat
start.bat
```
Ye ek menu show karega:
- **[1] Start Web Dashboard** (Browser GUI khul jayega)
- **[2] Run Property Dealer Lead Scraper** (Terminal CLI)
- **[3] Run WhatsApp Outreach Tool** (Terminal CLI)
- **[4] Open Exports Folder**
- **[5] Install / Verify Dependencies**

---

### Method 2: Direct Shortcuts
- **Web UI chalane ke liye**: Double click `start_web_ui.bat` -> browser me `http://localhost:5000` open hoga.
- **Terminal Scraper chalane ke liye**: Double click `run_scraper.bat`
- **Terminal WhatsApp Outreach chalane ke liye**: Double click `run_whatsapp.bat`

---

## 📁 Project Structure

```
scrapper+whatsapp/
├── exports/                       # Sabhi scraped files aur Master CRM
│   ├── Master_CRM_Leads.xlsx      # Master deduplicated database
│   ├── Master_CRM_Leads.csv
│   └── ... (Faridabad, Gurgaon, Jind, Sonipat, Delhi files)
├── .wwebjs_auth/                  # WhatsApp saved authenticated session
├── node_modules/                  # Node.js dependencies
├── scraper.py                     # Core web scraping engine (Playwright)
├── crm_manager.py                 # Master CRM & deduplication logic
├── web_app.py                     # Unified Web GUI (Flask + Tailwind CSS + SSE)
├── main.py                        # Terminal CLI scraper
├── whatsapp_runner.js             # WhatsApp engine runner (Web & CLI bridge)
├── index.js                       # Interactive CLI WhatsApp Outreach
├── leadLoader.js                  # Lead loader from ./exports
├── phoneFormatter.js              # Phone number normalizer
├── templates.js                   # Sales pitch message templates
├── historyManager.js              # Sent tracking & deduplication
├── sent_history.json              # History of all contacted numbers
├── config.json                    # Configuration (delays, batch limits, sender name)
├── start.bat                      # Master launcher menu
├── start_web_ui.bat               # Web GUI launcher
├── run_scraper.bat                # CLI Scraper launcher
├── run_whatsapp.bat               # CLI WhatsApp launcher
├── requirements.txt               # Python requirements
└── package.json                   # Node.js requirements
```

---

## ⚙️ Configuration (`config.json`)

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

## 🛡️ Anti-Ban Safety Tips
1. Ek session me **20-30 messages** se zyada na bhejein.
2. `minDelaySeconds` ko 25 seconds aur `maxDelaySeconds` ko 50 seconds se kam na karein.
3. Pehle **"Preview / Dry Run"** karke verify karein ki kaunse leads target ho rahe hain.
4. Khud ke phone number pe **"Send Test Message"** test karke WhatsApp verify karein.
