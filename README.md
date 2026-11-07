# 🏢 PropLead & WhatsApp Outreach Hub (Unified Command Center)

Ek hi jagah se **Multi-Niche B2B Local Leads Scrape** karne, **Master CRM** me manage karne, aur unhe direct **Automated Conversational WhatsApp Pitches** bhejne ka complete unified client acquisition engine.

---

## 🌟 Key Features

1. **Multi-Niche Google Maps Scraper (Python + Playwright)**:
   - Ab sirf property dealers hi nahi, balki **16+ Curated High-Converting Niches** me se kisi ko bhi target karein:
     - 👑 **Tier 1 (High-Ticket):** Real Estate, Interior Designers, Architects, Builders, Banquet Halls.
     - 🥈 **Tier 2 (High-Trust Services):** Dental Clinics, Polyclinics, Immigration Consultants, Coaching Institutes, Wedding Planners.
     - 🥉 **Tier 3 (Commercial Showrooms):** Hotels & Resorts, Used Car Dealers, Car Modification, Solar Dealers, Furniture, Travel.
     - ✏️ **Custom Niche:** Koi bhi local business keyword type karke scrape karein.
   - Business Name, Phone Number, Business Email, Website, Full Address, Star Rating & Review count nikalta hai.
   - Excel (`.xlsx`) and `.csv` formatted auto-exports with WhatsApp direct links.

2. **Master CRM Lead Database (`crm_manager.py`)**:
   - Sabhi cities aur niches ke leads automatically `Master_CRM_Leads.xlsx` me deduplicate hokar merge hote hain.
   - Niche Filter + Lead Status management (`New Lead`, `Contacted`, `Follow Up`, `Meeting Scheduled`, `Converted`, `Not Interested`).
   - WhatsApp outreach status indicator (`✅ Sent` with timestamp ya `Unsent`).

3. **Smart Niche-Specific WhatsApp Outreach Engine (Node.js + `whatsapp-web.js`)**:
   - Har niche ke dukh-dard ke hisab se **personalized non-salesy pitch**:
     - *Interior / Architects:* Project portfolio & design showcase pitch.
     - *Dental / Clinics:* Patient appointment scheduling pitch.
     - *Real Estate:* Active inventory & WhatsApp leads pitch.
     - *Banquet / Hotels:* Venue decor photos & date booking pitch.
   - **Anti-Ban Safeguards**: Random delays (25s - 50s), batch limits (10-30), WhatsApp number validation check, deduplication against `sent_history.json`.
   - **Filter targets**: Sirf unhi businesses ko message bhejta hai jinki website nahi hai (`onlyWithoutWebsite: true`).
   - Saved login session (`.wwebjs_auth`) — baar-baar QR code scan karne ki zaroorat nahi.

4. **Unified Web Dashboard (Browser GUI - `http://localhost:5000`)**:
   - Single browser tab me teeno tools:
     - **Tab 1: Lead Scraper**: Categorized Niche selector (Tier 1-3), live progress bar, live logs stream, session preview table.
     - **Tab 2: Master CRM**: Niche & Status filters, search, WhatsApp chat quick links, Excel download.
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
