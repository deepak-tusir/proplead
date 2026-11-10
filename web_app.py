"""
Web-Based GUI Interface for Multi-Niche Scraper, Master CRM & WhatsApp Outreach + Follow-up Engine
Powered by Flask + Server-Sent Events (SSE) for real-time live progress.
Accessible via web browser from localhost or any device on the local network.
"""

import os
import sys
import re
import json
import time
import queue
import socket
import asyncio
import threading
import subprocess
from datetime import datetime
from flask import Flask, render_template_string, request, Response, jsonify, send_from_directory

# Set stdout encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from scraper import scrape_property_dealers, export_to_excel
import crm_manager
import system_backup

app = Flask(__name__)
import secrets
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Base Directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SENT_HISTORY_FILE = os.path.join(BASE_DIR, "sent_history.json")
DEAD_LEADS_FILE = os.path.join(BASE_DIR, "dead_leads.json")

# In-memory pairing state for real-time streaming and proxy fallback polling
latest_pair_state = {"status": "idle", "qrImage": None, "timestamp": 0}


def get_local_ip():
    """Detect local LAN IP for sharing the link with others."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def load_sent_history():
    """Load WhatsApp sent history JSON if exists."""
    if os.path.exists(SENT_HISTORY_FILE):
        try:
            with open(SENT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def load_dead_leads():
    """Load Dead Leads JSON if exists."""
    if os.path.exists(DEAD_LEADS_FILE):
        try:
            with open(DEAD_LEADS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


# HTML Template with Tailwind CSS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PropLead & WhatsApp Outreach Command Center</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; }
        .log-box::-webkit-scrollbar { width: 6px; }
        .log-box::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        .active-tab { background-color: #4f46e5 !important; color: #ffffff !important; }
    </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col">

    <!-- Top Navigation Bar -->
    <header class="bg-indigo-950 text-white shadow-xl sticky top-0 z-50 border-b border-indigo-900/60">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-emerald-400 flex items-center justify-center shadow-lg">
                    <i class="fa-solid fa-bolt text-white text-lg"></i>
                </div>
                <div>
                    <h1 class="text-base sm:text-lg font-bold tracking-tight">PropLead &amp; WhatsApp Hub</h1>
                    <p class="text-[11px] text-indigo-300">Scraper &bull; Master CRM &bull; WhatsApp Outreach &bull; Follow-up</p>
                </div>
            </div>

            <!-- Tab Switcher -->
            <div class="flex items-center space-x-1.5 bg-indigo-900/70 p-1 rounded-xl border border-indigo-800/80 shadow-inner overflow-x-auto">
                <button onclick="switchTab('scraper')" id="tab-btn-scraper" class="px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg bg-indigo-600 text-white shadow transition-all flex items-center space-x-1.5 whitespace-nowrap">
                    <i class="fa-solid fa-magnifying-glass text-indigo-200"></i>
                    <span>Scraper</span>
                </button>
                <button onclick="switchTab('crm')" id="tab-btn-crm" class="px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg text-indigo-200 hover:text-white transition-all flex items-center space-x-1.5 whitespace-nowrap">
                    <i class="fa-solid fa-database text-indigo-200"></i>
                    <span>Master CRM</span>
                </button>
                <button onclick="switchTab('whatsapp')" id="tab-btn-whatsapp" class="px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg text-emerald-300 hover:text-white transition-all flex items-center space-x-1.5 whitespace-nowrap">
                    <i class="fa-brands fa-whatsapp text-emerald-400"></i>
                    <span>WhatsApp Outreach</span>
                </button>
                <button onclick="switchTab('followup')" id="tab-btn-followup" class="px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg text-amber-300 hover:text-white transition-all flex items-center space-x-1.5 whitespace-nowrap">
                    <i class="fa-solid fa-arrows-rotate text-amber-400"></i>
                    <span>Follow-ups &amp; Dead Leads</span>
                </button>
            </div>

            <!-- Reset & Backup Button and LAN Badge -->
            <div class="flex items-center space-x-2">
                <button onclick="openResetModal()" class="px-3 py-1.5 bg-rose-900/60 hover:bg-rose-800 text-rose-200 hover:text-white rounded-lg text-xs font-bold border border-rose-700/60 transition-all flex items-center space-x-1.5 shadow-sm" title="Safely create backup and reset leads/history">
                    <i class="fa-solid fa-arrows-rotate"></i>
                    <span class="hidden sm:inline">Reset &amp; Backup</span>
                </button>

                <!-- Network URL Badge -->
                <div class="hidden lg:flex items-center space-x-2 text-xs bg-indigo-900/80 px-3 py-1.5 rounded-lg border border-indigo-700">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span class="text-indigo-200">LAN: <strong class="text-white">{{ network_url }}</strong></span>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content Area -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">

        <!-- =================== TAB 1: SCRAPER =================== -->
        <div id="tab-scraper" class="space-y-8">

            <!-- Control Card -->
            <div class="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200/80">
                <div class="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-100 gap-4">
                    <div>
                        <h2 class="text-xl font-bold text-slate-900">Multi-Niche Lead Extraction Engine</h2>
                        <p class="text-sm text-slate-500 mt-1">Select your target industry niche (Tier 1 High-Ticket, Tier 2 Services, Tier 3 Commercial) and harvest verified local business contacts.</p>
                    </div>
                    <div class="flex items-center space-x-3">
                        <a href="/download/master-crm" class="inline-flex items-center space-x-2 px-4 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-xs sm:text-sm font-bold rounded-xl border border-emerald-200 transition-all">
                            <i class="fa-solid fa-file-excel text-emerald-600"></i>
                            <span>Download Master CRM</span>
                        </a>
                    </div>
                </div>

                <form id="scrape-form" onsubmit="startScrape(event)" class="mt-6 space-y-6">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        
                        <!-- Target Niche Selector (Categorized by Tiers) -->
                        <div class="md:col-span-1 space-y-2">
                            <label class="block text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center justify-between">
                                <span>Target Industry Niche</span>
                                <span class="text-[10px] text-indigo-600 font-bold">Tier 1-3 Categorized</span>
                            </label>
                            <div class="relative">
                                <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                                    <i class="fa-solid fa-briefcase"></i>
                                </div>
                                <select id="target-niche" onchange="handleNicheChange()" class="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none text-sm transition-all shadow-sm bg-white font-medium">
                                    <optgroup label="TIER 1: High-Ticket / Maximum Profit (Recommended)">
                                        <option value="Property dealers" selected>Property Dealers &amp; Real Estate</option>
                                        <option value="Interior Designers">Interior Designers &amp; Decorators</option>
                                        <option value="Architects">Architects &amp; Design Studios</option>
                                        <option value="Builders and Developers">Builders &amp; Real Estate Developers</option>
                                        <option value="Banquet halls">Banquet Halls &amp; Wedding Venues</option>
                                    </optgroup>
                                    <optgroup label="TIER 2: Professional &amp; High-Trust Local Services">
                                        <option value="Dental Clinics">Dental Clinics &amp; Implant Centres</option>
                                        <option value="Hospital clinics">Polyclinics &amp; Specialized Hospitals</option>
                                        <option value="Immigration consultants">Immigration &amp; Visa Consultants</option>
                                        <option value="Coaching Institutes">Coaching Institutes &amp; Academies</option>
                                        <option value="Wedding planners">Wedding Planners &amp; Luxury Event Managers</option>
                                    </optgroup>
                                    <optgroup label="TIER 3: High-Volume Commercial &amp; Showrooms">
                                        <option value="Hotels and resorts">Hotels &amp; Boutique Resorts</option>
                                        <option value="Used Car dealers">Used &amp; Luxury Car Dealerships</option>
                                        <option value="Car modification studios">Car Modification &amp; Detailing Studios</option>
                                        <option value="Solar panel dealers">Solar Panel Dealers &amp; Installers</option>
                                        <option value="Furniture Manufacturers">Furniture Manufacturers &amp; Showrooms</option>
                                        <option value="Travel agencies">Travel Agencies &amp; Tour Operators</option>
                                    </optgroup>
                                    <optgroup label="Custom Search">
                                        <option value="custom">Custom Niche (Type any keyword)...</option>
                                    </optgroup>
                                </select>
                            </div>

                            <!-- Custom Niche Input (reveals when 'custom' selected) -->
                            <div id="custom-niche-container" class="hidden pt-1">
                                <input type="text" id="custom-niche-input" placeholder="e.g. Chartered Accountants, Pet Clinics, Lawyers..."
                                    class="w-full px-3.5 py-2 rounded-xl border border-indigo-200 bg-indigo-50/50 text-xs text-indigo-900 outline-none focus:ring-2 focus:ring-indigo-300">
                            </div>
                        </div>

                        <!-- City / Locality Input -->
                        <div class="md:col-span-1 space-y-2">
                            <label class="block text-xs font-bold uppercase tracking-wider text-slate-600">
                                Target City or Locality
                            </label>
                            <div class="relative">
                                <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                                    <i class="fa-solid fa-location-dot"></i>
                                </div>
                                <input type="text" id="target-city" required
                                    placeholder="e.g. South Delhi, Gurgaon, Mumbai, Whitefield Bangalore, Sonipat..."
                                    class="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none text-sm transition-all shadow-sm"
                                    value="South Delhi">
                            </div>

                            <!-- Quick Area Chips -->
                            <div class="flex flex-wrap items-center gap-1.5 pt-1">
                                <span class="text-[10px] text-slate-400">Quick:</span>
                                <button type="button" onclick="setCity('South Delhi')" class="px-2 py-0.5 text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 rounded-md text-slate-600 font-medium transition-all">Delhi</button>
                                <button type="button" onclick="setCity('Gurgaon')" class="px-2 py-0.5 text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 rounded-md text-slate-600 font-medium transition-all">Gurgaon</button>
                                <button type="button" onclick="setCity('Faridabad')" class="px-2 py-0.5 text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 rounded-md text-slate-600 font-medium transition-all">Faridabad</button>
                                <button type="button" onclick="setCity('Sonipat')" class="px-2 py-0.5 text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 rounded-md text-slate-600 font-medium transition-all">Sonipat</button>
                                <button type="button" onclick="setCity('Noida')" class="px-2 py-0.5 text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 rounded-md text-slate-600 font-medium transition-all">Noida</button>
                            </div>
                        </div>

                        <!-- Max Results -->
                        <div class="space-y-2">
                            <label class="block text-xs font-bold uppercase tracking-wider text-slate-600">
                                Lead Count Limit
                            </label>
                            <div class="relative">
                                <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                                    <i class="fa-solid fa-list-ol"></i>
                                </div>
                                <select id="max-leads" class="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none text-sm transition-all shadow-sm bg-white">
                                    <option value="15">15 Leads (Quick Sample)</option>
                                    <option value="30" selected>30 Leads (Standard Batch)</option>
                                    <option value="50">50 Leads (Deep Extraction)</option>
                                    <option value="100">100 Leads (Comprehensive)</option>
                                </select>
                            </div>
                        </div>

                    </div>

                    <!-- Toggles & Action Button -->
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between pt-4 border-t border-slate-100 gap-4">
                        <div class="flex flex-wrap items-center gap-6">
                            <label class="inline-flex items-center cursor-pointer">
                                <input type="checkbox" id="check-emails" checked class="sr-only peer">
                                <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                                <span class="ml-2.5 text-xs font-medium text-slate-700">Crawl Websites for Emails</span>
                            </label>

                            <label class="inline-flex items-center cursor-pointer">
                                <input type="checkbox" id="sync-crm" checked class="sr-only peer">
                                <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600"></div>
                                <span class="ml-2.5 text-xs font-medium text-slate-700">Auto-Sync to Master CRM</span>
                            </label>
                        </div>

                        <button type="submit" id="start-btn"
                            class="inline-flex items-center justify-center space-x-2 px-8 py-3.5 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white font-bold rounded-xl shadow-lg shadow-indigo-600/30 transition-all text-sm transform active:scale-95">
                            <i class="fa-solid fa-play text-xs"></i>
                            <span>Start Extraction</span>
                        </button>
                    </div>
                </form>
            </div>

            <!-- Live Progress Card (Hidden by default) -->
            <div id="progress-container" class="hidden bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200/80 space-y-6">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 id="progress-title" class="text-base font-bold text-slate-900">Extraction in Progress...</h3>
                        <p id="progress-sub" class="text-xs text-slate-500 mt-0.5">Initializing automated browser session...</p>
                    </div>
                    <span id="progress-percent" class="text-sm font-extrabold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-lg">0%</span>
                </div>

                <div class="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                    <div id="progress-bar" class="bg-gradient-to-r from-indigo-500 to-purple-600 h-3 rounded-full transition-all duration-300" style="width: 0%"></div>
                </div>

                <div class="space-y-1.5">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Live Activity Feed</span>
                        <span class="text-[11px] text-emerald-600 font-semibold flex items-center">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping mr-1.5"></span> Live
                        </span>
                    </div>
                    <div id="live-logs" class="log-box bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-xs h-48 overflow-y-auto space-y-1 border border-slate-800">
                        <!-- Streamed live logs -->
                    </div>
                </div>
            </div>

            <!-- Extraction Completed Banner -->
            <div id="completion-box" class="hidden p-6 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
                <div class="flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-emerald-500 text-white flex items-center justify-center text-xl shadow-md shadow-emerald-500/20">
                        <i class="fa-solid fa-check"></i>
                    </div>
                    <div>
                        <h3 class="text-base font-bold text-emerald-950">Extraction Finished Successfully!</h3>
                        <p id="completion-summary" class="text-xs text-emerald-700 mt-0.5">Harvested 0 leads.</p>
                    </div>
                </div>
                <div class="flex flex-wrap items-center gap-3">
                    <a id="btn-download-excel" href="#" class="inline-flex items-center space-x-2 px-4 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold rounded-xl shadow transition-all">
                        <i class="fa-solid fa-file-excel"></i>
                        <span>Download Excel (.xlsx)</span>
                    </a>
                    <a id="btn-download-csv" href="#" class="inline-flex items-center space-x-2 px-4 py-2.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-bold rounded-xl transition-all">
                        <i class="fa-solid fa-file-csv"></i>
                        <span>CSV</span>
                    </a>
                    <button onclick="switchTab('whatsapp')" class="inline-flex items-center space-x-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow transition-all">
                        <i class="fa-brands fa-whatsapp"></i>
                        <span>Send via WhatsApp</span>
                    </button>
                </div>
            </div>

            <!-- Results Preview Table -->
            <div id="results-table-container" class="hidden bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-4">
                <div class="flex items-center justify-between">
                    <h3 class="text-base font-bold text-slate-900">Session Leads Preview</h3>
                    <span id="results-count-badge" class="px-2.5 py-1 bg-indigo-50 text-indigo-700 font-bold text-xs rounded-lg">0 Leads</span>
                </div>
                <div class="overflow-x-auto rounded-xl border border-slate-200">
                    <table class="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr class="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                                <th class="p-3">#</th>
                                <th class="p-3">Agency Name</th>
                                <th class="p-3">Phone</th>
                                <th class="p-3">Email Address</th>
                                <th class="p-3">Website</th>
                                <th class="p-3">Address</th>
                                <th class="p-3">Rating</th>
                                <th class="p-3 text-center">Action</th>
                            </tr>
                        </thead>
                        <tbody id="session-table-body" class="divide-y divide-slate-100">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>

        </div>

        <!-- =================== TAB 2: MASTER CRM =================== -->
        <div id="tab-crm" class="hidden space-y-8">
            
            <!-- CRM KPI Stats -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-5">
                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                    <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total CRM Leads</p>
                    <h4 id="kpi-total" class="text-2xl font-extrabold text-slate-900 mt-1">0</h4>
                    <p class="text-[11px] text-indigo-600 font-medium mt-1">Deduplicated Master DB</p>
                </div>
                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                    <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">With Phone Number</p>
                    <h4 id="kpi-phone" class="text-2xl font-extrabold text-emerald-600 mt-1">0</h4>
                    <p class="text-[11px] text-slate-400 mt-1">Ready for WhatsApp</p>
                </div>
                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                    <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">With Verified Email</p>
                    <h4 id="kpi-email" class="text-2xl font-extrabold text-blue-600 mt-1">0</h4>
                    <p class="text-[11px] text-slate-400 mt-1">Email Outreach Ready</p>
                </div>
                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                    <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">With Live Website</p>
                    <h4 id="kpi-web" class="text-2xl font-extrabold text-purple-600 mt-1">0</h4>
                    <p class="text-[11px] text-slate-400 mt-1">Has Existing Online Presence</p>
                </div>
            </div>

            <!-- CRM Filter & Search Bar -->
            <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 space-y-4">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div class="flex-1 grid grid-cols-1 sm:grid-cols-4 gap-3">
                        <div class="relative">
                            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                                <i class="fa-solid fa-magnifying-glass"></i>
                            </div>
                            <input type="text" id="crm-search" oninput="filterCrmTable()" placeholder="Search name, phone, area, niche..."
                                class="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-xs outline-none focus:border-indigo-500">
                        </div>

                        <select id="crm-niche-filter" onchange="filterCrmTable()" class="px-3 py-2 rounded-xl border border-slate-200 text-xs outline-none bg-white">
                            <option value="">All Niches (Any)</option>
                            <option value="property">Property Dealers</option>
                            <option value="interior">Interior Designers</option>
                            <option value="architect">Architects</option>
                            <option value="builder">Builders &amp; Developers</option>
                            <option value="banquet">Banquet Halls</option>
                            <option value="dental">Dental Clinics</option>
                            <option value="hospital">Hospital Clinics</option>
                            <option value="immigration">Immigration Consultants</option>
                            <option value="coaching">Coaching Institutes</option>
                            <option value="hotel">Hotels &amp; Resorts</option>
                            <option value="car">Car Dealers</option>
                        </select>

                        <select id="crm-status-filter" onchange="filterCrmTable()" class="px-3 py-2 rounded-xl border border-slate-200 text-xs outline-none bg-white">
                            <option value="">All CRM Statuses</option>
                            <option value="New Lead">New Lead</option>
                            <option value="Contacted">Contacted</option>
                            <option value="Follow Up">Follow Up</option>
                            <option value="Meeting Scheduled">Meeting Scheduled</option>
                            <option value="Converted">Converted</option>
                            <option value="Not Interested">Not Interested</option>
                        </select>

                        <select id="crm-wa-filter" onchange="filterCrmTable()" class="px-3 py-2 rounded-xl border border-slate-200 text-xs outline-none bg-white">
                            <option value="">WhatsApp Outreach: All</option>
                            <option value="sent">Already Messaged</option>
                            <option value="unsent">Not Messaged Yet</option>
                        </select>
                    </div>

                    <div>
                        <a href="/download/master-crm" class="inline-flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow transition-all whitespace-nowrap">
                            <i class="fa-solid fa-download"></i>
                            <span>Download Full CRM (.xlsx)</span>
                        </a>
                    </div>
                </div>

                <!-- Master CRM Table -->
                <div class="overflow-x-auto rounded-xl border border-slate-200">
                    <table class="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr class="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                                <th class="p-3">#</th>
                                <th class="p-3">CRM Status</th>
                                <th class="p-3">WhatsApp Outreach</th>
                                <th class="p-3">Agency Name</th>
                                <th class="p-3">Phone</th>
                                <th class="p-3">Quick Chat</th>
                                <th class="p-3">Email</th>
                                <th class="p-3">Website</th>
                                <th class="p-3">Source City</th>
                                <th class="p-3">Date Added</th>
                            </tr>
                        </thead>
                        <tbody id="crm-table-body" class="divide-y divide-slate-100">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>

        </div>

        <!-- =================== TAB 3: WHATSAPP OUTREACH =================== -->
        <div id="tab-whatsapp" class="hidden space-y-8">
            
            <!-- WhatsApp Connection & Metrics Cards -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
                    <div class="flex items-center space-x-3.5">
                        <div id="wa-auth-icon" class="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center text-xl flex-shrink-0">
                            <i class="fa-brands fa-whatsapp"></i>
                        </div>
                        <div>
                            <p class="text-xs text-slate-500 font-semibold">WhatsApp Session</p>
                            <h4 id="wa-auth-status" class="text-sm font-extrabold text-emerald-600 mt-0.5">Checking...</h4>
                        </div>
                    </div>
                    <div class="flex items-center space-x-1.5">
                        <button onclick="openPairModal()" id="btn-open-pair" class="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-all flex items-center space-x-1 shadow-sm">
                            <i class="fa-solid fa-qrcode"></i>
                            <span id="btn-pair-text">Scan QR</span>
                        </button>
                        <button onclick="logoutWhatsApp()" id="btn-wa-logout" class="hidden px-2 py-1.5 bg-slate-100 hover:bg-rose-50 hover:text-rose-600 text-slate-500 rounded-lg text-xs font-semibold transition-all" title="Disconnect session">
                            <i class="fa-solid fa-power-off"></i>
                        </button>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center text-xl">
                        <i class="fa-solid fa-paper-plane"></i>
                    </div>
                    <div>
                        <p class="text-xs text-slate-500 font-semibold">Total Pitches Sent</p>
                        <h4 id="wa-total-sent" class="text-2xl font-extrabold text-slate-900 mt-0.5">0</h4>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center text-xl">
                        <i class="fa-solid fa-circle-check"></i>
                    </div>
                    <div>
                        <p class="text-xs text-slate-500 font-semibold">Delivered (Success)</p>
                        <h4 id="wa-success-sent" class="text-2xl font-extrabold text-emerald-600 mt-0.5">0</h4>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center text-xl">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                    </div>
                    <div>
                        <p class="text-xs text-slate-500 font-semibold">Failed / Not on WA</p>
                        <h4 id="wa-failed-sent" class="text-2xl font-extrabold text-rose-600 mt-0.5">0</h4>
                    </div>
                </div>
            </div>

            <!-- Campaign Setup Card -->
            <div class="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-6">
                <div class="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-100 gap-4">
                    <div>
                        <h2 class="text-xl font-bold text-slate-900">Automated WhatsApp Outreach Campaign</h2>
                        <p class="text-sm text-slate-500 mt-1">Send personalized website creation pitches to scraped property dealers with anti-ban delay protections.</p>
                    </div>

                    <!-- Test Connection Quick Button -->
                    <div class="flex items-center space-x-3">
                        <button onclick="openTestModal()" class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs sm:text-sm font-bold rounded-xl border border-slate-200 transition-all flex items-center space-x-2">
                            <i class="fa-solid fa-vial text-indigo-600"></i>
                            <span>Send Test Message</span>
                        </button>
                    </div>
                </div>

                <!-- Campaign Controls Grid -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    
                    <!-- Lead File Source -->
                    <div class="space-y-2">
                        <label class="block text-xs font-bold uppercase tracking-wider text-slate-600">
                            Target Leads File
                        </label>
                        <select id="wa-target-file" class="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none text-sm transition-all shadow-sm bg-white">
                            <option value="Master_CRM_Leads.xlsx">Master CRM Leads (Recommended)</option>
                        </select>
                        <p class="text-[11px] text-slate-400">Pulls directly from `./exports` folder</p>
                    </div>

                    <!-- Batch Limit -->
                    <div class="space-y-2">
                        <label class="block text-xs font-bold uppercase tracking-wider text-slate-600">
                            Batch Send Limit
                        </label>
                        <input type="number" id="wa-batch-limit" value="20" min="1" max="100" class="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none text-sm transition-all shadow-sm">
                        <p class="text-[11px] text-slate-400">Keep between 10-30 for safety</p>
                    </div>

                    <!-- Sender Name -->
                    <div class="space-y-2">
                        <label class="block text-xs font-bold uppercase tracking-wider text-slate-600">
                            Sender Signature Name
                        </label>
                        <input type="text" id="wa-sender-name" value="Deepaktusir" class="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none text-sm transition-all shadow-sm">
                        <p class="text-[11px] text-slate-400">Appears at end of pitch</p>
                    </div>

                </div>

                <!-- Anti-Ban Delay & Filter Options -->
                <div class="p-4 bg-slate-50 rounded-xl border border-slate-200/80 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div class="flex items-center space-x-3">
                        <input type="checkbox" id="wa-filter-noweb" checked class="w-4 h-4 text-indigo-600 rounded border-slate-300">
                        <div>
                            <label for="wa-filter-noweb" class="font-bold text-slate-800 cursor-pointer">Target ONLY without Website</label>
                            <p class="text-[11px] text-slate-500">Highest conversion for web dev pitch</p>
                        </div>
                    </div>

                    <div class="space-y-1">
                        <label class="font-bold text-slate-700">Min Delay (Seconds):</label>
                        <input type="number" id="wa-min-delay" value="25" min="10" max="120" class="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-white">
                    </div>

                    <div class="space-y-1">
                        <label class="font-bold text-slate-700">Max Delay (Seconds):</label>
                        <input type="number" id="wa-max-delay" value="50" min="20" max="180" class="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-white">
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="flex flex-wrap items-center justify-between pt-4 border-t border-slate-100 gap-4">
                    <button type="button" onclick="runDryRunPreview()" class="inline-flex items-center space-x-2 px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-xl border border-slate-300 transition-all text-xs sm:text-sm">
                        <i class="fa-solid fa-eye text-indigo-600"></i>
                        <span>1. Preview / Dry Run</span>
                    </button>

                    <button type="button" id="btn-start-campaign" onclick="startWhatsAppCampaign()" class="inline-flex items-center space-x-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-md hover:shadow-emerald-500/20 transition-all text-sm">
                        <i class="fa-brands fa-whatsapp text-lg"></i>
                        <span>2. Start WhatsApp Campaign</span>
                    </button>
                </div>
            </div>

            <!-- Dry Run Preview Container (Hidden by default) -->
            <div id="wa-dryrun-container" class="hidden bg-white rounded-2xl p-6 shadow-sm border border-slate-200 space-y-4">
                <div class="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div>
                        <h3 class="font-bold text-slate-900 text-base">Campaign Audience Preview</h3>
                        <p id="wa-dryrun-meta" class="text-xs text-slate-500 mt-0.5">Eligible leads ready for outreach</p>
                    </div>
                    <span id="wa-dryrun-ready-badge" class="px-3 py-1 bg-emerald-50 text-emerald-700 font-bold text-xs rounded-lg">0 Ready</span>
                </div>

                <div id="wa-dryrun-samples" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <!-- Populated dynamically with sample preview cards -->
                </div>
            </div>

            <!-- Live Campaign Execution Box (Hidden by default) -->
            <div id="wa-live-container" class="hidden bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-5">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 id="wa-live-title" class="font-bold text-slate-900 text-base">WhatsApp Campaign Running...</h3>
                        <p id="wa-live-sub" class="text-xs text-slate-500 mt-0.5">Initializing WhatsApp automation engine</p>
                    </div>
                    <span id="wa-live-counter" class="text-sm font-extrabold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-lg">0 / 0</span>
                </div>

                <!-- Progress Bar -->
                <div class="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                    <div id="wa-progress-bar" class="bg-emerald-600 h-3 rounded-full transition-all duration-300" style="width: 0%"></div>
                </div>

                <!-- Countdown Delay Status -->
                <div id="wa-countdown-badge" class="hidden p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs font-semibold flex items-center space-x-2">
                    <span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
                    <span id="wa-countdown-text">Anti-ban delay countdown: 35s</span>
                </div>

                <!-- Live Log Feed -->
                <div class="space-y-1.5">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Campaign Live Feed</span>
                        <span class="text-[11px] text-emerald-600 font-semibold flex items-center">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping mr-1.5"></span> Connected
                        </span>
                    </div>
                    <div id="wa-live-logs" class="log-box bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-xs h-56 overflow-y-auto space-y-1 border border-slate-800">
                        <!-- Populated by SSE -->
                    </div>
                </div>
            </div>

        </div>

        <!-- =================== TAB 4: FOLLOW-UPS & DEAD LEADS =================== -->
        <div id="tab-followup" class="hidden space-y-8">

            <!-- Follow-up Metrics KPI Cards -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center text-xl">
                        <i class="fa-solid fa-hourglass-half"></i>
                    </div>
                    <div>
                        <p class="text-xs text-slate-500 font-semibold">Needs Follow-up 1</p>
                        <h4 id="fu-kpi-fu1" class="text-2xl font-extrabold text-amber-600 mt-0.5">0</h4>
                        <p class="text-[10px] text-slate-400">Gentle bump (seen/unseen)</p>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center text-xl">
                        <i class="fa-solid fa-bell"></i>
                    </div>
                    <div>
                        <p class="text-xs text-slate-500 font-semibold">Needs Follow-up 2 (Final)</p>
                        <h4 id="fu-kpi-fu2" class="text-2xl font-extrabold text-purple-600 mt-0.5">0</h4>
                        <p class="text-[10px] text-slate-400">Last chance before Dead List</p>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center text-xl">
                        <i class="fa-solid fa-comments"></i>
                    </div>
                    <div>
                        <p class="text-xs text-slate-500 font-semibold">Client Replied (Hot!)</p>
                        <h4 id="fu-kpi-replied" class="text-2xl font-extrabold text-emerald-600 mt-0.5">0</h4>
                        <p class="text-[10px] text-emerald-600 font-semibold">Active conversations</p>
                    </div>
                </div>

                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center space-x-4">
                    <div class="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center text-xl">
                        <i class="fa-solid fa-skull"></i>
                    </div>
                    <div>
                        <p class="text-xs text-slate-500 font-semibold">Dead Leads Vault</p>
                        <h4 id="fu-kpi-dead" class="text-2xl font-extrabold text-rose-600 mt-0.5">0</h4>
                        <p class="text-[10px] text-rose-600 font-semibold">Strictly blacklisted</p>
                    </div>
                </div>
            </div>

            <!-- Follow-up Launch & Chat Scanner Card -->
            <div class="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-6">
                <div class="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-100 gap-4">
                    <div>
                        <h2 class="text-xl font-bold text-slate-900 flex items-center space-x-2">
                            <span>Smart WhatsApp Follow-up &amp; Dead Leads Engine</span>
                            <span class="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded-md">Anti-Spam Max 2</span>
                        </h2>
                        <p class="text-sm text-slate-500 mt-1">Tracks message views (blue ticks), replies, and auto-sends up to 2 follow-ups before moving dead contacts into the Blacklist Vault.</p>
                    </div>

                    <!-- Scan Chats Button -->
                    <div class="flex items-center space-x-3">
                        <button id="btn-scan-chats" onclick="scanWhatsAppChats()" class="inline-flex items-center space-x-2 px-4 py-2.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs sm:text-sm font-bold rounded-xl border border-indigo-200 transition-all shadow-sm">
                            <i class="fa-solid fa-satellite-dish text-indigo-600"></i>
                            <span>Scan WhatsApp for Replies &amp; Blue Ticks</span>
                        </button>
                    </div>
                </div>

                <!-- Scanner Live Notification Status Banner -->
                <div id="scan-status-box" class="hidden p-4 rounded-xl text-xs font-semibold"></div>

                <!-- Follow-up Campaign Controls -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
                    <div class="space-y-1.5">
                        <label class="block text-xs font-bold text-slate-700">Follow-up Batch Size:</label>
                        <input type="number" id="fu-batch-limit" value="10" min="1" max="50" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs outline-none focus:border-indigo-500">
                        <p class="text-[10px] text-slate-400">Recommended 5-15 per session</p>
                    </div>

                    <div class="space-y-1.5">
                        <label class="block text-xs font-bold text-slate-700">Min Anti-Ban Delay (s):</label>
                        <input type="number" id="fu-min-delay" value="25" min="15" max="120" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs outline-none">
                    </div>

                    <div class="space-y-1.5">
                        <label class="block text-xs font-bold text-slate-700">Max Anti-Ban Delay (s):</label>
                        <input type="number" id="fu-max-delay" value="50" min="25" max="180" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs outline-none">
                    </div>

                    <div class="space-y-1.5">
                        <label class="block text-xs font-bold text-slate-700">Sender Signature:</label>
                        <input type="text" id="fu-sender-name" value="Deepaktusir" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs outline-none">
                    </div>
                </div>

                <div class="flex items-center justify-between pt-4 border-t border-slate-100">
                    <div class="text-xs text-slate-500">
                        <i class="fa-solid fa-shield-halved text-emerald-600 mr-1"></i>
                        <span>Contacts who already completed 2 follow-ups or replied are strictly protected and excluded.</span>
                    </div>
                    <button type="button" id="btn-start-followup" onclick="startFollowupCampaign()" class="inline-flex items-center space-x-2 px-6 py-3 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-xl shadow-md hover:shadow-amber-500/20 transition-all text-xs sm:text-sm">
                        <i class="fa-solid fa-paper-plane"></i>
                        <span>Launch Follow-up Batch</span>
                    </button>
                </div>
            </div>

            <!-- Follow-up Live Execution Container (Hidden by default) -->
            <div id="fu-live-container" class="hidden bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-5">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 id="fu-live-title" class="font-bold text-slate-900 text-base">Follow-up Batch Running...</h3>
                        <p id="fu-live-sub" class="text-xs text-slate-500 mt-0.5">Dispatching smart contextual follow-up messages</p>
                    </div>
                    <span id="fu-live-counter" class="text-sm font-extrabold text-amber-600 bg-amber-50 px-3 py-1 rounded-lg">0 / 0</span>
                </div>

                <!-- Progress Bar -->
                <div class="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                    <div id="fu-progress-bar" class="bg-amber-600 h-3 rounded-full transition-all duration-300" style="width: 0%"></div>
                </div>

                <!-- Delay Countdown Badge -->
                <div id="fu-countdown-badge" class="hidden p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs font-semibold flex items-center space-x-2">
                    <span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
                    <span id="fu-countdown-text">Anti-ban safe cooldown: 35s remaining...</span>
                </div>

                <!-- Live Log Feed -->
                <div class="space-y-1.5">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Follow-up Live Logs</span>
                    </div>
                    <div id="fu-live-logs" class="log-box bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-xs h-48 overflow-y-auto space-y-1 border border-slate-800">
                    </div>
                </div>
            </div>

            <!-- View Switcher Tabs: 1) Pending Follow-up Queue, 2) Dead Leads Vault -->
            <div class="flex items-center space-x-2 border-b border-slate-200 pb-2">
                <button onclick="switchFollowupSubView('queue')" id="subbtn-fu-queue" class="px-4 py-2 font-bold text-xs rounded-xl bg-indigo-600 text-white shadow transition-all flex items-center space-x-1.5">
                    <i class="fa-solid fa-list-check"></i>
                    <span>Pending Follow-up Queue (<span id="count-queue-badge">0</span>)</span>
                </button>
                <button onclick="switchFollowupSubView('dead')" id="subbtn-fu-dead" class="px-4 py-2 font-bold text-xs rounded-xl text-slate-600 hover:text-slate-900 transition-all flex items-center space-x-1.5">
                    <i class="fa-solid fa-skull text-rose-500"></i>
                    <span>Dead Leads Blacklist Vault (<span id="count-dead-badge">0</span>)</span>
                </button>
            </div>

            <!-- SUB-VIEW 1: FOLLOW-UP QUEUE TABLE -->
            <div id="subview-fu-queue" class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 space-y-4">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 class="text-base font-bold text-slate-900">Leads Awaiting Next Follow-up</h3>
                        <p class="text-xs text-slate-500 mt-0.5">Contacts who were sent an initial pitch and haven't replied yet.</p>
                    </div>
                </div>

                <div class="overflow-x-auto rounded-xl border border-slate-200">
                    <table class="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr class="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                                <th class="p-3">#</th>
                                <th class="p-3">Business / Agency</th>
                                <th class="p-3">Phone</th>
                                <th class="p-3">WhatsApp Read Receipt</th>
                                <th class="p-3">Next Action</th>
                                <th class="p-3">Waiting Time</th>
                                <th class="p-3 text-center">Quick Action</th>
                            </tr>
                        </thead>
                        <tbody id="fu-queue-table-body" class="divide-y divide-slate-100">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- SUB-VIEW 2: DEAD LEADS BLACKLIST VAULT -->
            <div id="subview-fu-dead" class="hidden bg-white rounded-2xl p-6 shadow-sm border border-slate-200 space-y-4">
                
                <!-- Notice Banner -->
                <div class="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900 flex items-start space-x-3">
                    <div class="w-6 h-6 rounded-lg bg-rose-500 text-white flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                        <i class="fa-solid fa-ban"></i>
                    </div>
                    <div>
                        <h4 class="font-bold text-rose-950">Strict Outreach Blacklist Vault</h4>
                        <p class="mt-0.5 text-rose-800 leading-relaxed">
                            These numbers completed all follow-up cycles without any reply or were identified as unresponsive. 
                            <strong>They are strictly blacklisted from all future scraper campaigns and cold pitches.</strong>
                            <br>
                            <em>Auto-Revival:</em> If any contact from this list replies back on WhatsApp at any time, they are automatically unlocked and removed from the dead list! You can also manually revive them using the button below.
                        </p>
                    </div>
                </div>

                <div class="overflow-x-auto rounded-xl border border-slate-200">
                    <table class="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr class="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                                <th class="p-3">#</th>
                                <th class="p-3">Business / Lead Name</th>
                                <th class="p-3">Phone Number</th>
                                <th class="p-3">Blacklist Reason</th>
                                <th class="p-3">Date Added</th>
                                <th class="p-3 text-center">Action</th>
                            </tr>
                        </thead>
                        <tbody id="fu-dead-table-body" class="divide-y divide-slate-100">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>

        </div>

    </main>

    <!-- Send Test Message Modal -->
    <div id="test-modal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 class="font-bold text-slate-900 text-base flex items-center space-x-2">
                    <i class="fa-solid fa-vial text-indigo-600"></i>
                    <span>Send Test WhatsApp Message</span>
                </h3>
                <button onclick="closeTestModal()" class="text-slate-400 hover:text-slate-600">
                    <i class="fa-solid fa-xmark text-lg"></i>
                </button>
            </div>
            <p class="text-xs text-slate-500">Send a sample website pitch to your own phone number to confirm your WhatsApp connection is active.</p>
            
            <div class="space-y-2">
                <label class="block text-xs font-bold text-slate-700">Your Phone Number (with Country Code):</label>
                <input type="text" id="test-phone-input" placeholder="e.g. 9812345678 or 919812345678" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-indigo-500 text-xs sm:text-sm outline-none">
            </div>

            <div id="test-msg-status" class="hidden text-xs p-3 rounded-xl"></div>

            <div class="flex items-center justify-end space-x-3 pt-3">
                <button onclick="closeTestModal()" class="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
                <button onclick="sendTestWhatsApp()" id="btn-do-test" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow">Send Now</button>
            </div>
        </div>
    </div>

        <!-- WhatsApp QR Pairing Modal -->
    <div id="wa-pair-modal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4 text-center">
            <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 class="font-bold text-slate-900 text-base flex items-center space-x-2">
                    <i class="fa-brands fa-whatsapp text-emerald-600 text-xl"></i>
                    <span>Link WhatsApp Web</span>
                </h3>
                <button onclick="closePairModal()" class="text-slate-400 hover:text-slate-600">
                    <i class="fa-solid fa-xmark text-lg"></i>
                </button>
            </div>

            <div class="text-left text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200/80 space-y-1">
                <p class="font-bold text-slate-800">How to link:</p>
                <p>1. Open WhatsApp on your phone</p>
                <p>2. Tap <strong>Linked Devices &rarr; Link a Device</strong></p>
                <p>3. Point your camera at this QR code</p>
            </div>

            <!-- Live QR Container -->
            <div id="pair-qr-container" class="flex flex-col items-center justify-center p-4 bg-white border border-slate-200 rounded-2xl w-60 h-60 mx-auto shadow-inner">
                <div id="pair-qr-loading" class="text-xs text-slate-400 flex flex-col items-center space-y-2">
                    <i class="fa-solid fa-spinner fa-spin text-2xl text-emerald-600"></i>
                    <span>Generating live QR code...</span>
                </div>
                <img id="pair-qr-img" class="hidden w-52 h-52 rounded-lg object-contain" alt="WhatsApp QR Code">
            </div>

            <div id="pair-status-text" class="text-xs font-semibold text-slate-500">
                Waiting for scanner...
            </div>

            <div class="flex items-center justify-end pt-2 border-t border-slate-100">
                <button onclick="closePairModal()" class="px-4 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
            </div>
        </div>
    </div>

<!-- Reset & Backup Modal -->
    <div id="reset-modal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl max-w-lg w-full p-6 sm:p-7 shadow-2xl border border-slate-200 space-y-5">
            <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 class="font-bold text-slate-900 text-base flex items-center space-x-2">
                    <div class="w-8 h-8 rounded-lg bg-rose-100 text-rose-600 flex items-center justify-center">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                    </div>
                    <span>System Reset &amp; Auto-Backup</span>
                </h3>
                <button onclick="closeResetModal()" class="text-slate-400 hover:text-slate-600">
                    <i class="fa-solid fa-xmark text-lg"></i>
                </button>
            </div>
            
            <div class="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 leading-relaxed">
                <strong>Safety Guarantee:</strong> Before resetting, a complete timestamped ZIP archive containing all current scraped leads, Master CRM Excel files, WhatsApp sent history, and dead leads will be automatically created in <code>./backups/</code>.
            </div>

            <div class="space-y-3 text-xs text-slate-600">
                <p class="font-semibold text-slate-700">Choose action:</p>
                
                <div class="p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between gap-3">
                    <div>
                        <h4 class="font-bold text-slate-800">1. Instant Backup Only</h4>
                        <p class="text-[11px] text-slate-500">Creates a full ZIP archive without deleting any current leads or history.</p>
                    </div>
                    <button onclick="doCreateBackupOnly()" id="btn-do-backup" class="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg whitespace-nowrap shadow text-xs">
                        <i class="fa-solid fa-floppy-disk mr-1"></i> Backup Now
                    </button>
                </div>

                <div class="p-3.5 rounded-xl border border-rose-200 bg-rose-50 flex items-center justify-between gap-3">
                    <div>
                        <h4 class="font-bold text-rose-950">2. Full Backup + Reset Workspace</h4>
                        <p class="text-[11px] text-rose-700">Creates backup archive first, then resets CRM, leads &amp; history to clean state.</p>
                    </div>
                    <button onclick="doBackupAndReset()" id="btn-do-reset" class="px-3.5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-lg whitespace-nowrap shadow text-xs">
                        <i class="fa-solid fa-arrows-rotate mr-1"></i> Backup &amp; Reset
                    </button>
                </div>
            </div>

            <!-- Status / Result Message -->
            <div id="reset-status-box" class="hidden p-3.5 rounded-xl text-xs"></div>

            <!-- Existing Backups List -->
            <div class="pt-2 border-t border-slate-100">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-xs font-bold text-slate-700">Saved System Backups</span>
                    <button onclick="loadBackupsList()" class="text-[11px] text-indigo-600 font-semibold hover:underline">Refresh</button>
                </div>
                <div id="backups-list-box" class="max-h-28 overflow-y-auto space-y-1.5 text-xs">
                    <!-- Populated dynamically -->
                </div>
            </div>

            <div class="flex items-center justify-end pt-1">
                <button onclick="closeResetModal()" class="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg">Close</button>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        PropLead &amp; WhatsApp Hub &bull; Unified Real Estate Intelligence &amp; Outreach Command Center
    </footer>

    <!-- JavaScript logic -->
    <script>
        let allCrmRecords = [];
        let waFiles = [];
        let fuQueueList = [];
        let fuDeadList = {};

        function switchTab(tab) {
            const tabScraper = document.getElementById('tab-scraper');
            const tabCrm = document.getElementById('tab-crm');
            const tabWa = document.getElementById('tab-whatsapp');
            const tabFu = document.getElementById('tab-followup');

            const btnScraper = document.getElementById('tab-btn-scraper');
            const btnCrm = document.getElementById('tab-btn-crm');
            const btnWa = document.getElementById('tab-btn-whatsapp');
            const btnFu = document.getElementById('tab-btn-followup');

            tabScraper.classList.add('hidden');
            tabCrm.classList.add('hidden');
            tabWa.classList.add('hidden');
            tabFu.classList.add('hidden');

            btnScraper.className = "px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg text-indigo-200 hover:text-white transition-all flex items-center space-x-1.5 whitespace-nowrap";
            btnCrm.className = "px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg text-indigo-200 hover:text-white transition-all flex items-center space-x-1.5 whitespace-nowrap";
            btnWa.className = "px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg text-emerald-300 hover:text-white transition-all flex items-center space-x-1.5 whitespace-nowrap";
            btnFu.className = "px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg text-amber-300 hover:text-white transition-all flex items-center space-x-1.5 whitespace-nowrap";

            if (tab === 'scraper') {
                tabScraper.classList.remove('hidden');
                btnScraper.className = "px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg bg-indigo-600 text-white shadow transition-all flex items-center space-x-1.5 whitespace-nowrap";
            } else if (tab === 'crm') {
                tabCrm.classList.remove('hidden');
                btnCrm.className = "px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg bg-indigo-600 text-white shadow transition-all flex items-center space-x-1.5 whitespace-nowrap";
                loadCrmData();
            } else if (tab === 'whatsapp') {
                tabWa.classList.remove('hidden');
                btnWa.className = "px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg bg-emerald-600 text-white shadow transition-all flex items-center space-x-1.5 whitespace-nowrap";
                loadWhatsAppStatus();
            } else if (tab === 'followup') {
                tabFu.classList.remove('hidden');
                btnFu.className = "px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-semibold rounded-lg bg-amber-600 text-white shadow transition-all flex items-center space-x-1.5 whitespace-nowrap";
                loadFollowupData();
            }
        }

        function handleNicheChange() {
            const select = document.getElementById('target-niche');
            const customDiv = document.getElementById('custom-niche-container');
            if (select.value === 'custom') {
                customDiv.classList.remove('hidden');
                document.getElementById('custom-niche-input').focus();
            } else {
                customDiv.classList.add('hidden');
            }
        }

        function setCity(city) {
            document.getElementById('target-city').value = city;
        }

        function appendLog(boxId, msg) {
            const box = document.getElementById(boxId);
            if (!box) return;
            const row = document.createElement('div');
            row.textContent = msg;
            box.appendChild(row);
            box.scrollTop = box.scrollHeight;
        }

        
        function escapeHtml(str) {
            if (!str && str !== 0) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        /* ------------------ SCRAPER LOGIC ------------------ */
        function startScrape(event) {
            event.preventDefault();
            const city = document.getElementById('target-city').value.trim();
            const maxLeads = document.getElementById('max-leads').value;
            const checkEmails = document.getElementById('check-emails').checked;
            const syncCrm = document.getElementById('sync-crm').checked;

            const nicheSelect = document.getElementById('target-niche');
            let niche = nicheSelect ? nicheSelect.value : 'Property dealers';
            if (niche === 'custom') {
                niche = (document.getElementById('custom-niche-input').value || '').trim() || 'Local Businesses';
            }

            if (!city) return;

            document.getElementById('start-btn').disabled = true;
            document.getElementById('start-btn').classList.add('opacity-50', 'cursor-not-allowed');
            document.getElementById('progress-container').classList.remove('hidden');
            document.getElementById('completion-box').classList.add('hidden');
            document.getElementById('results-table-container').classList.add('hidden');
            document.getElementById('live-logs').innerHTML = '';
            document.getElementById('progress-bar').style.width = '5%';
            document.getElementById('progress-percent').innerText = '5%';
            document.getElementById('progress-title').innerText = `Extracting ${niche} in '${city}'...`;

            appendLog('live-logs', `[Start] Searching for '${niche}' in: ${city}`);
            appendLog('live-logs', `[Config] Target: up to ${maxLeads} leads | Email Crawl: ${checkEmails} | CRM Sync: ${syncCrm}`);

            const params = new URLSearchParams({
                city: city,
                niche: niche,
                max: maxLeads,
                emails: checkEmails ? '1' : '0',
                crm: syncCrm ? '1' : '0'
            });

            const eventSource = new EventSource(`/api/scrape/stream?${params.toString()}`);

            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);

                if (data.type === 'log') {
                    appendLog('live-logs', data.message);
                } else if (data.type === 'progress') {
                    document.getElementById('progress-bar').style.width = `${data.percent}%`;
                    document.getElementById('progress-percent').innerText = `${data.percent}%`;
                    if (data.subtitle) {
                        document.getElementById('progress-sub').innerText = data.subtitle;
                    }
                } else if (data.type === 'done') {
                    eventSource.close();
                    document.getElementById('progress-bar').style.width = '100%';
                    document.getElementById('progress-percent').innerText = '100%';
                    document.getElementById('progress-sub').innerText = 'Completed!';
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('start-btn').classList.remove('opacity-50', 'cursor-not-allowed');

                    // Completion Box
                    document.getElementById('completion-box').classList.remove('hidden');
                    document.getElementById('completion-summary').innerText = 
                        `Extracted ${data.stats.total} total leads (${data.stats.phone} phone numbers, ${data.stats.email} emails, ${data.stats.web} websites).`;

                    document.getElementById('btn-download-excel').href = `/download/${data.excel_file}`;
                    document.getElementById('btn-download-csv').href = `/download/${data.csv_file}`;

                    renderSessionTable(data.results);
                } else if (data.type === 'error') {
                    eventSource.close();
                    appendLog('live-logs', `[ERROR] ${data.message}`);
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('start-btn').classList.remove('opacity-50', 'cursor-not-allowed');
                }
            };

            eventSource.onerror = function() {
                eventSource.close();
                document.getElementById('start-btn').disabled = false;
                document.getElementById('start-btn').classList.remove('opacity-50', 'cursor-not-allowed');
            };
        }

        function renderSessionTable(results) {
            const tableBody = document.getElementById('session-table-body');
            tableBody.innerHTML = '';
            document.getElementById('results-count-badge').innerText = `${results.length} Leads`;
            document.getElementById('results-table-container').classList.remove('hidden');

            results.forEach((r, idx) => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50 transition-colors";
                
                const waLink = r["WhatsApp Link"] || (r["Phone Number"] ? `https://wa.me/91${r["Phone Number"].replace(/\\D/g,'')}?text=Hi` : '#');
                const businessName = r["Dealer / Agency Name"] || r["Business Name"] || r["Agency Name"] || r["Name"] || 'N/A';
                const fullAddress = r["Full Address"] || r["Address"] || r["Location"] || '-';

                tr.innerHTML = `
                    <td class="p-3 text-slate-400 font-mono">${idx + 1}</td>
                    <td class="p-3 font-bold text-slate-900">${escapeHtml(businessName)}</td>
                    <td class="p-3 font-semibold text-slate-700">${r["Phone Number"] || '-'}</td>
                    <td class="p-3 text-slate-600">${r["Email Address"] || '-'}</td>
                    <td class="p-3 text-indigo-600 truncate max-w-[140px]">${r["Website"] ? `<a href="${r["Website"]}" target="_blank" class="underline">${r["Website"].replace(/^https?:\\/\\//,'')}</a>` : '-'}</td>
                    <td class="p-3 text-slate-500 truncate max-w-[160px]" title="${escapeHtml(fullAddress)}">${escapeHtml(fullAddress)}</td>
                    <td class="p-3 font-bold text-amber-600">${r["Rating"] ? `${r["Rating"]}` : '-'}</td>
                    <td class="p-3 text-center">
                        ${r["Phone Number"] ? `
                            <a href="${waLink}" target="_blank" class="inline-flex items-center space-x-1 px-2.5 py-1 bg-emerald-50 text-emerald-700 hover:bg-emerald-600 hover:text-white rounded-lg font-semibold transition-all text-[11px]">
                                <i class="fa-brands fa-whatsapp"></i>
                                <span>Chat</span>
                            </a>
                        ` : '-'}
                    </td>
                `;
                tableBody.appendChild(tr);
            });
        }

        /* ------------------ MASTER CRM LOGIC ------------------ */
        function loadCrmData() {
            fetch('/api/master-leads')
                .then(res => res.json())
                .then(data => {
                    allCrmRecords = data.records || [];
                    document.getElementById('kpi-total').innerText = data.kpis.total;
                    document.getElementById('kpi-phone').innerText = data.kpis.with_phone;
                    document.getElementById('kpi-email').innerText = data.kpis.with_email;
                    document.getElementById('kpi-web').innerText = data.kpis.with_web;
                    renderCrmTable(allCrmRecords);
                })
                .catch(err => console.error('Error fetching CRM data:', err));
        }

        function filterCrmTable() {
            const query = (document.getElementById('crm-search').value || '').toLowerCase();
            const statusFilter = document.getElementById('crm-status-filter').value;
            const waFilter = document.getElementById('crm-wa-filter').value;
            const nicheFilter = (document.getElementById('crm-niche-filter')?.value || '').toLowerCase();

            const filtered = allCrmRecords.filter(r => {
                const matchQuery = 
                    (r["Agency Name"] || '').toLowerCase().includes(query) ||
                    (r["Phone Number"] || '').toLowerCase().includes(query) ||
                    (r["Source Area / Query"] || '').toLowerCase().includes(query) ||
                    (r["Category"] || '').toLowerCase().includes(query) ||
                    (r["Lead Status"] || '').toLowerCase().includes(query);

                const matchStatus = !statusFilter || (r["Lead Status"] === statusFilter);

                let matchWa = true;
                if (waFilter === 'sent') matchWa = Boolean(r.whatsapp_sent);
                if (waFilter === 'unsent') matchWa = !r.whatsapp_sent;

                let matchNiche = true;
                if (nicheFilter) {
                    const area = (r["Source Area / Query"] || '').toLowerCase();
                    const cat = (r["Category"] || '').toLowerCase();
                    const name = (r["Agency Name"] || '').toLowerCase();
                    matchNiche = area.includes(nicheFilter) || cat.includes(nicheFilter) || name.includes(nicheFilter);
                }

                return matchQuery && matchStatus && matchWa && matchNiche;
            });

            renderCrmTable(filtered);
        }

        function renderCrmTable(records) {
            const tbody = document.getElementById('crm-table-body');
            tbody.innerHTML = '';

            records.forEach((r, idx) => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50 transition-colors";

                const currentStatus = r["Lead Status"] || "New Lead";
                const isSent = Boolean(r.whatsapp_sent);
                const waTime = r.whatsapp_sent_time ? new Date(r.whatsapp_sent_time).toLocaleDateString() : '';

                tr.innerHTML = `
                    <td class="p-3 text-slate-400 font-mono">${idx + 1}</td>
                    <td class="p-3">
                        <select onchange="updateLeadStatus('${r["Phone Number"]}', this.value)" class="px-2 py-1 bg-white border border-slate-200 rounded-lg text-xs font-semibold outline-none">
                            <option value="New Lead" ${currentStatus === 'New Lead' ? 'selected' : ''}>New Lead</option>
                            <option value="Contacted" ${currentStatus === 'Contacted' ? 'selected' : ''}>Contacted</option>
                            <option value="Follow Up" ${currentStatus === 'Follow Up' ? 'selected' : ''}>Follow Up</option>
                            <option value="Meeting Scheduled" ${currentStatus === 'Meeting Scheduled' ? 'selected' : ''}>Meeting Scheduled</option>
                            <option value="Converted" ${currentStatus === 'Converted' ? 'selected' : ''}>Converted</option>
                            <option value="Not Interested" ${currentStatus === 'Not Interested' ? 'selected' : ''}>Not Interested</option>
                        </select>
                    </td>
                    <td class="p-3">
                        ${isSent ? `
                            <span class="inline-flex items-center space-x-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md text-[11px] font-bold">
                                <i class="fa-solid fa-check-double"></i>
                                <span>Sent ${waTime ? `(${waTime})` : ''}</span>
                            </span>
                        ` : `
                            <span class="inline-flex items-center space-x-1 px-2 py-0.5 bg-slate-100 text-slate-500 rounded-md text-[11px] font-medium">
                                <span>Unsent</span>
                            </span>
                        `}
                    </td>
                    <td class="p-3 font-bold text-slate-900">${r["Dealer / Agency Name"] || r["Business Name"] || r["Agency Name"] || r["Name"] || 'N/A'}</td>
                    <td class="p-3 font-semibold text-slate-700">${r["Phone Number"] || '-'}</td>
                    <td class="p-3">
                        ${r["Phone Number"] ? `
                            <a href="${r["WhatsApp Link"] || '#'}" target="_blank" class="inline-flex items-center space-x-1 text-emerald-600 hover:text-emerald-800 font-bold">
                                <i class="fa-brands fa-whatsapp text-sm"></i>
                                <span>Open</span>
                            </a>
                        ` : '-'}
                    </td>
                    <td class="p-3 text-slate-600">${r["Email Address"] || '-'}</td>
                    <td class="p-3 text-indigo-600 truncate max-w-[120px]">${r["Website"] ? `<a href="${r["Website"]}" target="_blank" class="underline">${r["Website"].replace(/^https?:\\/\\//,'')}</a>` : '-'}</td>
                    <td class="p-3 text-slate-500">${r["Source Area"] || r["Source Area / Query"] || '-'}</td>
                    <td class="p-3 text-slate-400 text-[11px]">${r["Date Added"] || '-'}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function updateLeadStatus(phone, newStatus) {
            fetch('/api/update-lead-status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone: phone, status: newStatus })
            }).catch(err => console.error('Status update error:', err));
        }

        /* ------------------ WHATSAPP OUTREACH LOGIC ------------------ */
        function loadWhatsAppStatus() {
            fetch('/api/whatsapp/status')
                .then(res => res.json())
                .then(data => {
                    const stats = data.stats || {};
                    document.getElementById('wa-total-sent').innerText = stats.totalMessaged || 0;
                    document.getElementById('wa-success-sent').innerText = stats.successful || 0;
                    document.getElementById('wa-failed-sent').innerText = stats.failed || 0;

                    const btnLogout = document.getElementById('btn-wa-logout');
                    const btnPair = document.getElementById('btn-open-pair');
                    const pairText = document.getElementById('btn-pair-text');

                    if (data.authSessionExists) {
                        document.getElementById('wa-auth-status').innerText = 'Authenticated & Active';
                        document.getElementById('wa-auth-status').className = 'text-sm font-extrabold text-emerald-600 mt-0.5';
                        if (btnLogout) btnLogout.classList.remove('hidden');
                        if (pairText) pairText.innerText = 'Switch No.';
                    } else {
                        document.getElementById('wa-auth-status').innerText = 'QR Link Required';
                        document.getElementById('wa-auth-status').className = 'text-sm font-extrabold text-amber-600 mt-0.5';
                        if (btnLogout) btnLogout.classList.add('hidden');
                        if (pairText) pairText.innerText = 'Scan QR';
                    }

                    // Populate Files Dropdown
                    const select = document.getElementById('wa-target-file');
                    select.innerHTML = '';
                    (data.files || []).forEach(f => {
                        const opt = document.createElement('option');
                        opt.value = f.name;
                        opt.textContent = `${f.name} (${f.sizeKB} KB)`;
                        if (f.name.includes('Master_CRM')) opt.selected = true;
                        select.appendChild(opt);
                    });
                })
                .catch(err => console.error('Error fetching WA status:', err));
        }

        function runDryRunPreview() {
            const fileName = document.getElementById('wa-target-file').value;
            const onlyNoWeb = document.getElementById('wa-filter-noweb').checked;

            document.getElementById('wa-dryrun-container').classList.remove('hidden');
            document.getElementById('wa-dryrun-meta').innerText = 'Analyzing eligible contacts and generating message previews...';
            document.getElementById('wa-dryrun-samples').innerHTML = '<div class="text-xs text-slate-500 py-4"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Loading preview...</div>';

            fetch(`/api/whatsapp/dry-run?file=${encodeURIComponent(fileName)}&only_no_web=${onlyNoWeb ? '1' : '0'}`)
                .then(res => res.json())
                .then(res => {
                    if (res.type === 'error') {
                        document.getElementById('wa-dryrun-meta').innerText = `Error: ${res.message}`;
                        return;
                    }

                    document.getElementById('wa-dryrun-meta').innerText = 
                        `File: ${res.filename} | Total: ${res.totalInFile} | No Website: ${res.filteredCount} | Already Sent: ${res.alreadySent} | Dead Skipped: ${res.deadSkipped || 0}`;
                    document.getElementById('wa-dryrun-ready-badge').innerText = `${res.readyToSend} Ready to Message`;

                    const container = document.getElementById('wa-dryrun-samples');
                    container.innerHTML = '';

                    if (!res.samples || res.samples.length === 0) {
                        container.innerHTML = '<div class="text-xs text-slate-500 p-4">No eligible uncontacted leads found in this file.</div>';
                        return;
                    }

                    res.samples.forEach(s => {
                        const card = document.createElement('div');
                        card.className = "p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2 text-xs";
                        card.innerHTML = `
                            <div class="flex items-center justify-between font-bold text-slate-900">
                                <span>#${s.index} ${s.name}</span>
                                <span class="text-emerald-700 font-mono">${s.formattedPhone}</span>
                            </div>
                            <div class="text-slate-500 truncate text-[11px]"><i class="fa-solid fa-location-dot mr-1 text-slate-400"></i>${s.address}</div>
                            <div class="p-3 bg-white rounded-lg border border-slate-200/80 font-mono text-[11px] text-slate-700 whitespace-pre-wrap leading-relaxed">${s.message}</div>
                        `;
                        container.appendChild(card);
                    });
                })
                .catch(err => {
                    document.getElementById('wa-dryrun-meta').innerText = `Preview failed: ${err.message}`;
                });
        }

        function startWhatsAppCampaign() {
            const fileName = document.getElementById('wa-target-file').value;
            const batchLimit = document.getElementById('wa-batch-limit').value || '20';
            const minDelay = document.getElementById('wa-min-delay').value || '25';
            const maxDelay = document.getElementById('wa-max-delay').value || '50';
            const onlyNoWeb = document.getElementById('wa-filter-noweb').checked;
            const senderName = document.getElementById('wa-sender-name').value || 'Deepaktusir';

            if (!confirm(`Start live WhatsApp campaign to message up to ${batchLimit} leads from '${fileName}'?\\n\\nAnti-ban safe delay: ${minDelay}s - ${maxDelay}s.`)) {
                return;
            }

            const btn = document.getElementById('btn-start-campaign');
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');

            const container = document.getElementById('wa-live-container');
            container.classList.remove('hidden');
            document.getElementById('wa-live-logs').innerHTML = '';
            document.getElementById('wa-progress-bar').style.width = '2%';
            document.getElementById('wa-live-counter').innerText = `Starting...`;
            document.getElementById('wa-live-title').innerText = `Running Campaign: ${fileName}`;

            appendLog('wa-live-logs', `[Init] Connecting to WhatsApp Web Client with saved session...`);

            const params = new URLSearchParams({
                file: fileName,
                batch: batchLimit,
                min_delay: minDelay,
                max_delay: maxDelay,
                only_no_web: onlyNoWeb ? '1' : '0',
                sender: senderName
            });

            const eventSource = new EventSource(`/api/whatsapp/campaign/stream?${params.toString()}`);

            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);

                if (data.type === 'log') {
                    appendLog('wa-live-logs', data.message);
                } else if (data.type === 'campaign_start') {
                    appendLog('wa-live-logs', `[Campaign] Target: ${data.batchSize} contacts (out of ${data.totalQueue} ready in queue)`);
                    document.getElementById('wa-live-counter').innerText = `0 / ${data.batchSize}`;
                } else if (data.type === 'contact_progress') {
                    document.getElementById('wa-live-counter').innerText = `${data.index} / ${data.total}`;
                    const pct = Math.round((data.index / data.total) * 100);
                    document.getElementById('wa-progress-bar').style.width = `${pct}%`;
                    appendLog('wa-live-logs', `[${data.index}/${data.total}] Sending to: ${data.name} (${data.phone})...`);
                    document.getElementById('wa-countdown-badge').classList.add('hidden');
                } else if (data.type === 'contact_result') {
                    if (data.status === 'success') {
                        appendLog('wa-live-logs', `  Successfully sent pitch to ${data.name}!`);
                    } else {
                        appendLog('wa-live-logs', `  Skipped/Failed for ${data.name}: ${data.reason}`);
                    }
                } else if (data.type === 'delay_start') {
                    document.getElementById('wa-countdown-badge').classList.remove('hidden');
                    document.getElementById('wa-countdown-text').innerText = `Anti-ban safe cooldown: ${data.seconds}s remaining...`;
                } else if (data.type === 'delay_tick') {
                    document.getElementById('wa-countdown-text').innerText = `Anti-ban safe cooldown: ${data.secondsRemaining}s remaining...`;
                } else if (data.type === 'campaign_complete') {
                    eventSource.close();
                    document.getElementById('wa-countdown-badge').classList.add('hidden');
                    document.getElementById('wa-progress-bar').style.width = '100%';
                    appendLog('wa-live-logs', `\\n${data.message}`);
                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                    loadWhatsAppStatus();
                } else if (data.type === 'error') {
                    eventSource.close();
                    appendLog('wa-live-logs', `[ERROR] ${data.message}`);
                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            };

            eventSource.onerror = function() {
                eventSource.close();
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            };
        }

        /* ------------------ FOLLOW-UPS & DEAD LEADS LOGIC ------------------ */
        function switchFollowupSubView(view) {
            const vQueue = document.getElementById('subview-fu-queue');
            const vDead = document.getElementById('subview-fu-dead');
            const bQueue = document.getElementById('subbtn-fu-queue');
            const bDead = document.getElementById('subbtn-fu-dead');

            if (view === 'queue') {
                vQueue.classList.remove('hidden');
                vDead.classList.add('hidden');
                bQueue.className = "px-4 py-2 font-bold text-xs rounded-xl bg-indigo-600 text-white shadow transition-all flex items-center space-x-1.5";
                bDead.className = "px-4 py-2 font-bold text-xs rounded-xl text-slate-600 hover:text-slate-900 transition-all flex items-center space-x-1.5";
            } else {
                vQueue.classList.add('hidden');
                vDead.classList.remove('hidden');
                bDead.className = "px-4 py-2 font-bold text-xs rounded-xl bg-rose-600 text-white shadow transition-all flex items-center space-x-1.5";
                bQueue.className = "px-4 py-2 font-bold text-xs rounded-xl text-slate-600 hover:text-slate-900 transition-all flex items-center space-x-1.5";
            }
        }

        function loadFollowupData() {
            // Fetch stats
            fetch('/api/whatsapp/status')
                .then(res => res.json())
                .then(data => {
                    const stats = data.stats || {};
                    document.getElementById('fu-kpi-fu1').innerText = stats.needsFollowUp1 || 0;
                    document.getElementById('fu-kpi-fu2').innerText = stats.needsFollowUp2 || 0;
                    document.getElementById('fu-kpi-replied').innerText = stats.clientReplied || 0;
                    document.getElementById('fu-kpi-dead').innerText = stats.deadCount || 0;
                })
                .catch(err => console.error(err));

            // Fetch follow-up queue
            fetch('/api/whatsapp/followup-queue')
                .then(res => res.json())
                .then(data => {
                    fuQueueList = data.queue || [];
                    document.getElementById('count-queue-badge').innerText = fuQueueList.length;
                    renderFollowupQueueTable(fuQueueList);
                })
                .catch(err => console.error(err));

            // Fetch dead leads
            fetch('/api/whatsapp/dead-leads')
                .then(res => res.json())
                .then(data => {
                    fuDeadList = data.deadLeads || {};
                    const deadCount = Object.keys(fuDeadList).length;
                    document.getElementById('count-dead-badge').innerText = deadCount;
                    renderDeadLeadsTable(fuDeadList);
                })
                .catch(err => console.error(err));
        }

        function renderFollowupQueueTable(queue) {
            const tbody = document.getElementById('fu-queue-table-body');
            tbody.innerHTML = '';

            if (queue.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400">No leads currently in the follow-up queue.</td></tr>`;
                return;
            }

            queue.forEach((item, idx) => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50 transition-colors";

                const isSeen = item.chat_seen;
                const fuNum = item.next_followup_num;
                const hoursWait = item.hours_elapsed || 0;
                const waLink = `https://wa.me/${item.phone}?text=Hi`;

                tr.innerHTML = `
                    <td class="p-3 text-slate-400 font-mono">${idx + 1}</td>
                    <td class="p-3 font-bold text-slate-900">${item.name || 'Business'}</td>
                    <td class="p-3 font-semibold text-slate-700 font-mono">${item.phone}</td>
                    <td class="p-3">
                        ${isSeen ? `
                            <span class="inline-flex items-center space-x-1 px-2.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded-md font-bold text-[11px]">
                                <i class="fa-solid fa-check-double text-blue-600"></i>
                                <span>Seen (Blue Tick)</span>
                            </span>
                        ` : `
                            <span class="inline-flex items-center space-x-1 px-2.5 py-0.5 bg-slate-100 text-slate-600 rounded-md font-medium text-[11px]">
                                <i class="fa-solid fa-check text-slate-400"></i>
                                <span>Unopened / Delivered</span>
                            </span>
                        `}
                    </td>
                    <td class="p-3">
                        ${fuNum === 1 ? `
                            <span class="px-2 py-0.5 bg-amber-50 text-amber-700 font-bold rounded-md border border-amber-200 text-[11px]">Follow-up #1 (Bump)</span>
                        ` : `
                            <span class="px-2 py-0.5 bg-purple-50 text-purple-700 font-bold rounded-md border border-purple-200 text-[11px]">Follow-up #2 (Breakup / Final)</span>
                        `}
                    </td>
                    <td class="p-3 text-slate-500 font-medium">${hoursWait} hrs ago</td>
                    <td class="p-3 text-center">
                        <a href="${waLink}" target="_blank" class="inline-flex items-center space-x-1 px-2.5 py-1 bg-emerald-50 text-emerald-700 hover:bg-emerald-600 hover:text-white rounded-lg font-bold text-[11px] transition-all">
                            <i class="fa-brands fa-whatsapp"></i>
                            <span>Chat</span>
                        </a>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function renderDeadLeadsTable(deadLeads) {
            const tbody = document.getElementById('fu-dead-table-body');
            tbody.innerHTML = '';

            const keys = Object.keys(deadLeads);
            if (keys.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">Dead leads vault is empty.</td></tr>`;
                return;
            }

            keys.forEach((phone, idx) => {
                const item = deadLeads[phone];
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50 transition-colors";

                const dateStr = item.added_at ? new Date(item.added_at).toLocaleString() : '-';

                tr.innerHTML = `
                    <td class="p-3 text-slate-400 font-mono">${idx + 1}</td>
                    <td class="p-3 font-bold text-slate-900">${item.name || 'Unknown'}</td>
                    <td class="p-3 font-semibold text-slate-700 font-mono">${item.phone || phone}</td>
                    <td class="p-3">
                        <span class="px-2.5 py-0.5 bg-rose-50 text-rose-700 border border-rose-200 rounded-md font-semibold text-[11px]">
                            ${item.reason || 'Max 2 follow-ups with no reply'}
                        </span>
                    </td>
                    <td class="p-3 text-slate-500">${dateStr}</td>
                    <td class="p-3 text-center">
                        <button onclick="reviveLead('${item.phone || phone}')" class="inline-flex items-center space-x-1 px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-[11px] shadow transition-all">
                            <i class="fa-solid fa-arrow-rotate-left"></i>
                            <span>Revive Lead</span>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function reviveLead(phone) {
            if (!confirm(`Revive lead '${phone}'? They will be removed from the Dead Leads list and restored to active CRM.`)) {
                return;
            }

            fetch('/api/whatsapp/revive-lead', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone: phone })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    alert(`Lead ${phone} successfully revived and unblacklisted!`);
                    loadFollowupData();
                } else {
                    alert(`Failed to revive: ${res.error || 'Unknown error'}`);
                }
            })
            .catch(err => alert(`Error: ${err.message}`));
        }

        function scanWhatsAppChats() {
            const btn = document.getElementById('btn-scan-chats');
            const statusBox = document.getElementById('scan-status-box');

            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-indigo-600"></i><span>Scanning WhatsApp Chats...</span>`;
            statusBox.className = "p-4 rounded-xl text-xs font-semibold bg-indigo-50 text-indigo-800 border border-indigo-200 block";
            statusBox.innerHTML = `
                <div class="flex items-center space-x-3">
                    <span class="w-2.5 h-2.5 rounded-full bg-indigo-600 animate-ping"></span>
                    <span>Connecting to WhatsApp Web, inspecting read receipts (blue ticks) and detecting replies... Please wait 10-20 seconds.</span>
                </div>
            `;

            fetch('/api/whatsapp/scan-chats')
                .then(res => res.json())
                .then(res => {
                    btn.disabled = false;
                    btn.innerHTML = `<i class="fa-solid fa-satellite-dish text-indigo-600"></i><span>Scan WhatsApp for Replies &amp; Blue Ticks</span>`;

                    if (res.type === 'error') {
                        statusBox.className = "p-4 rounded-xl text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200 block";
                        statusBox.innerHTML = `Error during scan: ${res.message}`;
                        return;
                    }

                    statusBox.className = "p-4 rounded-xl text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 block";
                    statusBox.innerHTML = `
                        <div class="flex items-center justify-between">
                            <span><strong>Scan Finished!</strong> Found <strong>${res.updatedReplies || 0}</strong> client replies, <strong>${res.updatedSeen || 0}</strong> seen messages (blue ticks), and auto-revived <strong>${res.revivedCount || 0}</strong> dead leads.</span>
                        </div>
                    `;

                    loadFollowupData();
                })
                .catch(err => {
                    btn.disabled = false;
                    btn.innerHTML = `<i class="fa-solid fa-satellite-dish text-indigo-600"></i><span>Scan WhatsApp for Replies &amp; Blue Ticks</span>`;
                    statusBox.className = "p-4 rounded-xl text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200 block";
                    statusBox.innerHTML = `Scan failed: ${err.message}`;
                });
        }

        function startFollowupCampaign() {
            const batchLimit = document.getElementById('fu-batch-limit').value || '10';
            const minDelay = document.getElementById('fu-min-delay').value || '25';
            const maxDelay = document.getElementById('fu-max-delay').value || '50';
            const senderName = document.getElementById('fu-sender-name').value || 'Deepaktusir';

            if (fuQueueList.length === 0) {
                alert('No leads are currently pending in the follow-up queue!');
                return;
            }

            if (!confirm(`Start automated Follow-up outreach for up to ${batchLimit} leads?\\n\\nAnti-ban safe delay: ${minDelay}s - ${maxDelay}s.\\nNote: Leads reaching 2 follow-ups with no reply will be moved to Dead List.`)) {
                return;
            }

            const btn = document.getElementById('btn-start-followup');
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');

            const container = document.getElementById('fu-live-container');
            container.classList.remove('hidden');
            document.getElementById('fu-live-logs').innerHTML = '';
            document.getElementById('fu-progress-bar').style.width = '2%';
            document.getElementById('fu-live-counter').innerText = 'Starting...';

            appendLog('fu-live-logs', `[Init] Connecting to WhatsApp Web for Follow-up dispatch...`);

            const params = new URLSearchParams({
                batch: batchLimit,
                min_delay: minDelay,
                max_delay: maxDelay,
                sender: senderName
            });

            const eventSource = new EventSource(`/api/whatsapp/followup/stream?${params.toString()}`);

            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);

                if (data.type === 'log') {
                    appendLog('fu-live-logs', data.message);
                } else if (data.type === 'followup_start') {
                    appendLog('fu-live-logs', `[Batch] Target: ${data.batchSize} follow-up contacts (out of ${data.totalQueue} ready)`);
                    document.getElementById('fu-live-counter').innerText = `0 / ${data.batchSize}`;
                } else if (data.type === 'followup_progress') {
                    document.getElementById('fu-live-counter').innerText = `${data.index} / ${data.total}`;
                    const pct = Math.round((data.index / data.total) * 100);
                    document.getElementById('fu-progress-bar').style.width = `${pct}%`;
                    const seenTag = data.isSeen ? '[SEEN/BLUE TICK]' : '[UNSEEN/BUMP]';
                    appendLog('fu-live-logs', `[${data.index}/${data.total}] Follow-up #${data.followUpNum} ${seenTag} -> ${data.name} (${data.phone})...`);
                    document.getElementById('fu-countdown-badge').classList.add('hidden');
                } else if (data.type === 'followup_result') {
                    if (data.status === 'success') {
                        appendLog('fu-live-logs', `  Successfully sent follow-up #${data.followUpNum} to ${data.name}!`);
                    } else {
                        appendLog('fu-live-logs', `  Failed for ${data.name}: ${data.reason}`);
                    }
                } else if (data.type === 'delay_start') {
                    document.getElementById('fu-countdown-badge').classList.remove('hidden');
                    document.getElementById('fu-countdown-text').innerText = `Anti-ban safe cooldown: ${data.seconds}s remaining...`;
                } else if (data.type === 'delay_tick') {
                    document.getElementById('fu-countdown-text').innerText = `Anti-ban safe cooldown: ${data.secondsRemaining}s remaining...`;
                } else if (data.type === 'followup_complete') {
                    eventSource.close();
                    document.getElementById('fu-countdown-badge').classList.add('hidden');
                    document.getElementById('fu-progress-bar').style.width = '100%';
                    appendLog('fu-live-logs', `\\n${data.message}`);
                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                    loadFollowupData();
                } else if (data.type === 'error') {
                    eventSource.close();
                    appendLog('fu-live-logs', `[ERROR] ${data.message}`);
                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            };

            eventSource.onerror = function() {
                eventSource.close();
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            };
        }

        /* ------------------ TEST MODAL LOGIC ------------------ */
        function openTestModal() {
            document.getElementById('test-modal').classList.remove('hidden');
            document.getElementById('test-msg-status').className = 'hidden';
        }

        function closeTestModal() {
            document.getElementById('test-modal').classList.add('hidden');
        }

        function sendTestWhatsApp() {
            const phone = document.getElementById('test-phone-input').value.trim();
            const sender = document.getElementById('wa-sender-name').value || 'Deepaktusir';

            if (!phone) {
                alert('Please enter a valid phone number.');
                return;
            }

            const btn = document.getElementById('btn-do-test');
            btn.disabled = true;
            btn.innerText = 'Sending...';

            const statusBox = document.getElementById('test-msg-status');
            statusBox.className = 'text-xs p-3 rounded-xl bg-indigo-50 text-indigo-700 block';
            statusBox.innerText = 'Initializing WhatsApp and sending test message...';

            fetch('/api/whatsapp/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone: phone, sender: sender })
            })
            .then(res => res.json())
            .then(res => {
                btn.disabled = false;
                btn.innerText = 'Send Now';
                if (res.success) {
                    statusBox.className = 'text-xs p-3 rounded-xl bg-emerald-50 text-emerald-800 font-bold block';
                    statusBox.innerText = 'Test message sent successfully! Check your WhatsApp.';
                } else {
                    statusBox.className = 'text-xs p-3 rounded-xl bg-rose-50 text-rose-800 font-bold block';
                    statusBox.innerText = `Error: ${res.error}`;
                }
            })
            .catch(err => {
                btn.disabled = false;
                btn.innerText = 'Send Now';
                statusBox.className = 'text-xs p-3 rounded-xl bg-rose-50 text-rose-800 font-bold block';
                statusBox.innerText = `Failed: ${err.message}`;
            });
        }

        
        /* ------------------ WHATSAPP QR PAIRING LOGIC ------------------ */
        let pairEventSource = null;
        let pairPollInterval = null;

        function handlePairData(data) {
            if (data.type === 'qr' && data.qrImage) {
                document.getElementById('pair-qr-loading').classList.add('hidden');
                const img = document.getElementById('pair-qr-img');
                img.src = data.qrImage;
                img.classList.remove('hidden');
                document.getElementById('pair-status-text').innerText = 'Scan the QR code with WhatsApp on your phone';
            } else if (data.type === 'authenticated') {
                document.getElementById('pair-status-text').innerText = 'Authenticated! Initializing connection...';
            } else if (data.type === 'ready') {
                document.getElementById('pair-status-text').innerText = 'Connected successfully!';
                if (pairEventSource) { pairEventSource.close(); pairEventSource = null; }
                if (pairPollInterval) { clearInterval(pairPollInterval); pairPollInterval = null; }
                setTimeout(() => {
                    closePairModal();
                    loadWhatsAppStatus();
                }, 1200);
            } else if (data.type === 'error') {
                document.getElementById('pair-status-text').innerText = 'Error: ' + data.message;
            }
        }

        function openPairModal() {
            document.getElementById('wa-pair-modal').classList.remove('hidden');
            document.getElementById('pair-qr-loading').classList.remove('hidden');
            document.getElementById('pair-qr-img').classList.add('hidden');
            document.getElementById('pair-status-text').innerText = 'Initializing client & generating QR code...';

            if (pairEventSource) {
                pairEventSource.close();
            }
            if (pairPollInterval) {
                clearInterval(pairPollInterval);
            }

            pairEventSource = new EventSource('/api/whatsapp/pair/stream');

            pairEventSource.onmessage = function(e) {
                try {
                    const data = JSON.parse(e.data);
                    handlePairData(data);
                } catch(err) {}
            };

            pairEventSource.onerror = function() {
                // Do not immediately terminate; proxy buffering fallback is active
                console.log('SSE connection waiting or blip, polling active...');
            };

            // Fast fallback: poll /api/whatsapp/pair/poll every 1.5s in case reverse proxy (Cloudflare) buffers SSE
            pairPollInterval = setInterval(() => {
                const img = document.getElementById('pair-qr-img');
                if (img.classList.contains('hidden')) {
                    fetch('/api/whatsapp/pair/poll')
                        .then(r => r.json())
                        .then(data => {
                            if (data.hasQr && data.qrImage) {
                                handlePairData({ type: 'qr', qrImage: data.qrImage });
                            } else if (data.status === 'authenticated' || data.status === 'ready') {
                                handlePairData({ type: data.status });
                            }
                        })
                        .catch(() => {});
                }
            }, 1500);
        }

        function closePairModal() {
            if (pairEventSource) {
                pairEventSource.close();
                pairEventSource = null;
            }
            if (pairPollInterval) {
                clearInterval(pairPollInterval);
                pairPollInterval = null;
            }
            document.getElementById('wa-pair-modal').classList.add('hidden');
        }

        function logoutWhatsApp() {
            if (!confirm('Disconnect current WhatsApp session? You will need to scan QR code again.')) {
                return;
            }

            fetch('/api/whatsapp/logout', { method: 'POST' })
                .then(res => res.json())
                .then(res => {
                    alert('WhatsApp session disconnected.');
                    loadWhatsAppStatus();
                })
                .catch(err => alert('Error: ' + err.message));
        }

        /* ------------------ SYSTEM BACKUP & RESET LOGIC ------------------ */
        function openResetModal() {
            document.getElementById('reset-modal').classList.remove('hidden');
            document.getElementById('reset-status-box').className = 'hidden';
            loadBackupsList();
        }

        function closeResetModal() {
            document.getElementById('reset-modal').classList.add('hidden');
        }

        function loadBackupsList() {
            const box = document.getElementById('backups-list-box');
            box.innerHTML = '<div class="text-[11px] text-slate-400 py-1">Loading saved backups...</div>';

            fetch('/api/system/backups')
                .then(res => res.json())
                .then(list => {
                    box.innerHTML = '';
                    if (!list || list.length === 0) {
                        box.innerHTML = '<div class="text-[11px] text-slate-400 py-1">No prior backups found.</div>';
                        return;
                    }
                    list.forEach(b => {
                        const row = document.createElement('div');
                        row.className = "flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200/80 text-[11px]";
                        row.innerHTML = `
                            <div class="flex items-center space-x-2 truncate">
                                <i class="fa-solid fa-file-zipper text-indigo-500"></i>
                                <span class="font-mono text-slate-700 truncate" title="${b.filename}">${b.filename}</span>
                                <span class="text-slate-400">(${b.size_kb} KB)</span>
                            </div>
                            <a href="/download/backup/${b.filename}" class="px-2 py-0.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-600 hover:text-white rounded font-bold transition-all ml-2 flex items-center space-x-1">
                                <i class="fa-solid fa-download text-[10px]"></i>
                                <span>Get</span>
                            </a>
                        `;
                        box.appendChild(row);
                    });
                })
                .catch(() => {
                    box.innerHTML = '<div class="text-[11px] text-slate-400 py-1">Could not fetch backups.</div>';
                });
        }

        function doCreateBackupOnly() {
            const btn = document.getElementById('btn-do-backup');
            const statusBox = document.getElementById('reset-status-box');

            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Creating...`;
            statusBox.className = "p-3 rounded-xl bg-indigo-50 text-indigo-800 text-xs block";
            statusBox.innerText = "Creating timestamped ZIP archive of all leads, CRM and history...";

            fetch('/api/system/backup', { method: 'POST' })
                .then(res => res.json())
                .then(res => {
                    btn.disabled = false;
                    btn.innerHTML = `<i class="fa-solid fa-floppy-disk mr-1"></i> Backup Now`;

                    if (res.success) {
                        statusBox.className = "p-3 rounded-xl bg-emerald-50 text-emerald-800 text-xs font-semibold block";
                        statusBox.innerHTML = `
                            <div class="flex items-center justify-between">
                                <span>Backup created successfully: <strong>${res.backup.zip_filename}</strong></span>
                                <a href="/download/backup/${res.backup.zip_filename}" class="ml-2 px-2.5 py-1 bg-emerald-600 text-white font-bold rounded-lg hover:bg-emerald-700">Download ZIP</a>
                            </div>
                        `;
                        loadBackupsList();
                    } else {
                        statusBox.className = "p-3 rounded-xl bg-rose-50 text-rose-800 text-xs block";
                        statusBox.innerText = `Backup error: ${res.error}`;
                    }
                })
                .catch(err => {
                    btn.disabled = false;
                    btn.innerHTML = `<i class="fa-solid fa-floppy-disk mr-1"></i> Backup Now`;
                    statusBox.className = "p-3 rounded-xl bg-rose-50 text-rose-800 text-xs block";
                    statusBox.innerText = `Error: ${err.message}`;
                });
        }

        function doBackupAndReset() {
            if (!confirm("ARE YOU SURE?\\n\\nThis will:\\n1. Create a complete ZIP backup of all current data.\\n2. Reset all leads, Master CRM, and WhatsApp sent history.\\n\\nYou can start fresh with a clean slate.")) {
                return;
            }

            const btn = document.getElementById('btn-do-reset');
            const statusBox = document.getElementById('reset-status-box');

            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Resetting...`;
            statusBox.className = "p-3 rounded-xl bg-amber-50 text-amber-800 text-xs block";
            statusBox.innerText = "Creating full backup archive and resetting workspace...";

            fetch('/api/system/reset', { method: 'POST' })
                .then(res => res.json())
                .then(res => {
                    btn.disabled = false;
                    btn.innerHTML = `<i class="fa-solid fa-arrows-rotate mr-1"></i> Backup & Reset`;

                    if (res.success) {
                        statusBox.className = "p-3 rounded-xl bg-emerald-50 text-emerald-800 text-xs font-semibold block";
                        statusBox.innerHTML = `
                            <div class="space-y-1">
                                <div><strong>Reset Complete! Workspace is now fresh and clean.</strong></div>
                                <div class="text-[11px] text-emerald-700 flex items-center justify-between">
                                    <span>All data safely preserved in: <strong>${res.backup.zip_filename}</strong></span>
                                    <a href="/download/backup/${res.backup.zip_filename}" class="px-2.5 py-1 bg-emerald-600 text-white font-bold rounded-lg hover:bg-emerald-700">Download ZIP</a>
                                </div>
                            </div>
                        `;
                        loadBackupsList();
                        // Refresh current views
                        loadCrmData();
                        loadWhatsAppStatus();
                        loadFollowupData();
                    } else {
                        statusBox.className = "p-3 rounded-xl bg-rose-50 text-rose-800 text-xs block";
                        statusBox.innerText = `Reset error: ${res.error}`;
                    }
                })
                .catch(err => {
                    btn.disabled = false;
                    btn.innerHTML = `<i class="fa-solid fa-arrows-rotate mr-1"></i> Backup & Reset`;
                    statusBox.className = "p-3 rounded-xl bg-rose-50 text-rose-800 text-xs block";
                    statusBox.innerText = `Error: ${err.message}`;
                });
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    local_ip = get_local_ip()
    network_url = f"http://{local_ip}:5000"
    return render_template_string(HTML_TEMPLATE, network_url=network_url)


@app.route('/api/master-leads')
def api_master_leads():
    records = crm_manager.load_master_records()
    total = len(records)
    with_phone = sum(1 for r in records if r.get("Phone Number"))
    with_email = sum(1 for r in records if r.get("Email Address"))
    with_web = sum(1 for r in records if r.get("Website"))
    
    # Enrich with WhatsApp sent history
    history = load_sent_history()
    for r in records:
        name_val = r.get("Dealer / Agency Name") or r.get("Agency Name") or r.get("Business Name") or r.get("Name") or ""
        r["Dealer / Agency Name"] = name_val
        r["Agency Name"] = name_val
        r["Business Name"] = name_val
        
        addr_val = r.get("Full Address") or r.get("Address") or ""
        r["Full Address"] = addr_val
        r["Address"] = addr_val

        phone_raw = str(r.get("Phone Number", ""))
        digits = re.sub(r'\D', '', phone_raw)
        key10 = digits[-10:] if len(digits) >= 10 else digits
        
        r["whatsapp_sent"] = False
        r["whatsapp_sent_time"] = ""
        
        if key10:
            for clean_k, v in history.items():
                if v.get("status") == "SUCCESS":
                    if clean_k.endswith(key10):
                        r["whatsapp_sent"] = True
                        r["whatsapp_sent_time"] = v.get("timestamp", "")
                        break
                        
    return jsonify({
        "records": records,
        "kpis": {
            "total": total,
            "with_phone": with_phone,
            "with_email": with_email,
            "with_web": with_web
        }
    })


@app.route('/api/update-lead-status', methods=['POST'])
def api_update_lead_status():
    data = request.json or {}
    phone = data.get("phone", "")
    new_status = data.get("status", "New Lead")
    if not phone:
        return jsonify({"success": False, "error": "Phone required"}), 400
        
    success = crm_manager.update_lead_status(phone, new_status)
    return jsonify({"success": success})


def make_sse_response(generator):
    """Creates a standards-compliant SSE Response configured to prevent reverse proxy buffering (Cloudflare, Nginx)."""
    resp = Response(generator, mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache, no-transform"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Connection"] = "keep-alive"
    return resp


@app.route('/api/scrape/stream')
def api_scrape_stream():
    """Server-Sent Events endpoint to stream live scraper progress."""
    city = request.args.get('city', 'South Delhi')
    niche = request.args.get('niche', 'Property dealers')
    max_leads = int(request.args.get('max', 30))
    check_emails = request.args.get('emails', '1') == '1'
    sync_crm = request.args.get('crm', '1') == '1'
    
    target_query = f"{niche} in {city}"

    def event_stream():
        msg_queue = queue.Queue()
        
        def progress_cb(msg):
            msg_queue.put({"type": "log", "message": msg})
            
        def run_scraper_thread():
            try:
                msg_queue.put({"type": "progress", "percent": 10, "subtitle": f"Launching automated browser session for '{target_query}'..."})
                
                # Run the async scraper
                results = asyncio.run(scrape_property_dealers(
                    query=target_query,
                    max_results=max_leads,
                    check_emails=check_emails,
                    progress_callback=progress_cb
                ))
                
                # Tag each lead with niche & query and ensure display aliases
                for r in results:
                    name_val = r.get("Dealer / Agency Name") or r.get("Agency Name") or r.get("Business Name") or r.get("Name") or ""
                    r["Dealer / Agency Name"] = name_val
                    r["Agency Name"] = name_val
                    r["Business Name"] = name_val

                    addr_val = r.get("Full Address") or r.get("Address") or ""
                    r["Full Address"] = addr_val
                    r["Address"] = addr_val

                    if not r.get("Category") or r.get("Category") in ("Real Estate Agency", "Business"):
                        r["Category"] = niche
                    r["Search Query"] = target_query
                
                msg_queue.put({"type": "progress", "percent": 85, "subtitle": "Formatting and building Excel file..."})
                
                # Export to Excel & CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_niche = "".join(c if c.isalnum() else "_" for c in niche).strip("_")
                safe_city = "".join(c if c.isalnum() else "_" for c in city).strip("_")
                output_dir = crm_manager.get_exports_dir()
                excel_filename = f"{safe_niche}_{safe_city}_{timestamp}.xlsx"
                excel_path = os.path.join(output_dir, excel_filename)
                
                export_to_excel(results, excel_path, search_query=target_query)
                csv_filename = excel_filename.replace('.xlsx', '.csv')
                
                # Sync with Master CRM if requested
                if sync_crm:
                    msg_queue.put({"type": "log", "message": "[CRM] Merging into Master CRM Database & deduplicating..."})
                    crm_stats = crm_manager.sync_to_master_crm(results, source_area=f"{niche} - {city}")
                    msg_queue.put({"type": "log", "message": f"[CRM] Sync complete! Total active CRM leads: {crm_stats['total_in_master']} (+{crm_stats['newly_added']} new)"})
                
                stats = {
                    "total": len(results),
                    "phone": sum(1 for r in results if r.get("Phone Number")),
                    "email": sum(1 for r in results if r.get("Email Address")),
                    "web": sum(1 for r in results if r.get("Website"))
                }
                
                msg_queue.put({
                    "type": "done",
                    "results": results,
                    "stats": stats,
                    "excel_file": excel_filename,
                    "csv_file": csv_filename
                })
            except Exception as e:
                msg_queue.put({"type": "error", "message": str(e)})
            finally:
                msg_queue.put(None)
                
        t = threading.Thread(target=run_scraper_thread, daemon=True)
        t.start()
        
        while True:
            item = msg_queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return make_sse_response(event_stream())


@app.route('/api/whatsapp/status')
def api_whatsapp_status():
    """Returns WhatsApp outreach statistics, file list, and session status."""
    try:
        cmd = ["node", "whatsapp_runner.js", "--status"]
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=10)
        for line in proc.stdout.splitlines():
            if line.startswith("{"):
                return jsonify(json.loads(line))
        return jsonify({"type": "status_info", "stats": {}, "files": [], "authSessionExists": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/whatsapp/dry-run')
def api_whatsapp_dry_run():
    """Runs a non-destructive outreach dry-run to preview contacts and messages."""
    filename = os.path.basename(request.args.get('file', 'Master_CRM_Leads.xlsx'))
    only_no_web = request.args.get('only_no_web', '1') == '1'
    filepath = os.path.join(crm_manager.get_exports_dir(), filename) if filename else 'master'
    
    try:
        cmd = ["node", "whatsapp_runner.js", "--dry-run", filepath, "true" if only_no_web else "false", "6"]
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=15)
        for line in proc.stdout.splitlines():
            if line.startswith("{") and "dry_run_result" in line:
                return jsonify(json.loads(line))
        return jsonify({"type": "error", "message": proc.stderr or "No dry-run data returned"})
    except Exception as e:
        return jsonify({"type": "error", "message": str(e)}), 500


@app.route('/api/whatsapp/test', methods=['POST'])
def api_whatsapp_test():
    """Sends a single test message using Node whatsapp runner."""
    data = request.json or {}
    raw_phone = data.get("phone", "")
    raw_sender = data.get("sender", "Deepaktusir")
    phone = re.sub(r'[^0-9+]', '', str(raw_phone)).strip()
    sender = re.sub(r'[^a-zA-Z0-9\s._-]', '', str(raw_sender)).strip().lstrip('-') or 'Deepaktusir'
    if not phone or not phone.lstrip('+').isdigit():
        return jsonify({"success": False, "error": "Invalid phone format"}), 400
        
    try:
        cmd = ["node", "whatsapp_runner.js", "--test", phone, sender]
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=40)
        success = False
        error_msg = ""
        for line in proc.stdout.splitlines():
            if line.startswith("{"):
                try:
                    ev = json.loads(line)
                    if ev.get("type") == "test_sent_success":
                        success = True
                    elif ev.get("type") == "error":
                        error_msg = ev.get("message")
                except Exception:
                    pass
        if success:
            return jsonify({"success": True})
        return jsonify({"success": False, "error": error_msg or proc.stderr or "Failed to send test message"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/whatsapp/campaign/stream')
def api_whatsapp_campaign_stream():
    """Server-Sent Events endpoint to stream live WhatsApp outreach campaign progress."""
    filename = os.path.basename(request.args.get('file', 'Master_CRM_Leads.xlsx'))
    batch = request.args.get('batch', '20')
    min_delay = request.args.get('min_delay', '25')
    max_delay = request.args.get('max_delay', '50')
    only_no_web = request.args.get('only_no_web', '1') == '1'
    sender = request.args.get('sender', 'Deepaktusir')
    
    filepath = os.path.join(crm_manager.get_exports_dir(), filename) if filename else 'master'

    def event_stream():
        cmd = [
            "node", "whatsapp_runner.js", "--campaign",
            filepath, batch, min_delay, max_delay,
            "true" if only_no_web else "false", sender
        ]
        proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            for line in iter(proc.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{") and line.endswith("}"):
                    try:
                        obj = json.loads(line)
                        yield f"data: {json.dumps(obj)}\n\n"
                    except Exception:
                        yield f"data: {json.dumps({'type': 'log', 'message': line})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'log', 'message': line})}\n\n"
            proc.stdout.close()
            proc.wait()
        except GeneratorExit:
            proc.terminate()
            
    return make_sse_response(event_stream())


@app.route('/api/whatsapp/followup-queue')
def api_whatsapp_followup_queue():
    """Returns the list of contacts currently waiting for a follow-up."""
    try:
        cmd = ["node", "whatsapp_runner.js", "--followup-queue"]
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=10)
        for line in proc.stdout.splitlines():
            if line.startswith("{") and "followup_queue" in line:
                return jsonify(json.loads(line))
        return jsonify({"type": "followup_queue", "count": 0, "queue": []})
    except Exception as e:
        return jsonify({"type": "error", "message": str(e)}), 500


@app.route('/api/whatsapp/dead-leads')
def api_whatsapp_dead_leads():
    """Returns the dictionary/list of blacklisted Dead Leads."""
    try:
        cmd = ["node", "whatsapp_runner.js", "--dead-leads"]
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=10)
        for line in proc.stdout.splitlines():
            if line.startswith("{") and "dead_leads" in line:
                return jsonify(json.loads(line))
        return jsonify({"type": "dead_leads", "count": 0, "deadLeads": {}})
    except Exception as e:
        return jsonify({"type": "error", "message": str(e)}), 500


@app.route('/api/whatsapp/revive-lead', methods=['POST'])
def api_whatsapp_revive_lead():
    """Revives a contact from the dead leads list back to active."""
    data = request.json or {}
    raw_phone = data.get("phone", "")
    phone = re.sub(r'[^0-9+]', '', str(raw_phone)).strip()
    if not phone or not phone.lstrip('+').isdigit():
        return jsonify({"success": False, "error": "Invalid phone format"}), 400
        
    try:
        cmd = ["node", "whatsapp_runner.js", "--revive", str(phone)]
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=10)
        return jsonify({"success": True, "phone": phone})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/api/whatsapp/pair/stream')
def api_whatsapp_pair_stream():
    """Server-Sent Events endpoint to stream real-time WhatsApp QR code to browser."""
    def event_stream():
        global latest_pair_state
        # Send initial SSE comment so proxy (Cloudflare/Nginx) flushes headers immediately
        yield ": ping\n\n"
        
        # If a fresh QR code was generated within the last 35 seconds, yield immediately
        if latest_pair_state.get("qrImage") and (time.time() - latest_pair_state.get("timestamp", 0) < 35):
            yield f"data: {json.dumps({'type': 'qr', 'qrImage': latest_pair_state['qrImage'], 'message': 'Point your phone at the screen to scan this QR code'})}\n\n"

        cmd = ["node", "whatsapp_runner.js", "--pair"]
        proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            for line in iter(proc.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{") and line.endswith("}"):
                    try:
                        obj = json.loads(line)
                        if obj.get("type") == "qr" and obj.get("qrImage"):
                            latest_pair_state["qrImage"] = obj.get("qrImage")
                            latest_pair_state["status"] = "qr"
                            latest_pair_state["timestamp"] = time.time()
                        elif obj.get("type") in ("authenticated", "ready"):
                            latest_pair_state["status"] = obj.get("type")
                            latest_pair_state["qrImage"] = None
                        yield f"data: {json.dumps(obj)}\n\n"
                    except Exception:
                        pass
            proc.stdout.close()
            proc.wait()
        except GeneratorExit:
            proc.terminate()

    return make_sse_response(event_stream())


@app.route('/api/whatsapp/pair/poll')
def api_whatsapp_pair_poll():
    """Poll endpoint as a backup if SSE is buffered by proxies or firewalls."""
    return jsonify({
        "status": latest_pair_state.get("status", "idle"),
        "qrImage": latest_pair_state.get("qrImage"),
        "hasQr": bool(latest_pair_state.get("qrImage"))
    })


@app.route('/api/whatsapp/logout', methods=['POST'])
def api_whatsapp_logout():
    """Disconnects and removes saved WhatsApp session."""
    global latest_pair_state
    latest_pair_state = {"status": "idle", "qrImage": None, "timestamp": 0}
    try:
        cmd = ["node", "whatsapp_runner.js", "--logout"]
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=10)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/whatsapp/scan-chats')
def api_whatsapp_scan_chats():
    """Scans all existing WhatsApp chats to detect client replies and read receipts (blue ticks)."""
    try:
        cmd = ["node", "whatsapp_runner.js", "--scan-chats"]
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=90)
        for line in proc.stdout.splitlines():
            if line.startswith("{") and "scan_complete" in line:
                return jsonify(json.loads(line))
        return jsonify({"type": "scan_complete", "updatedReplies": 0, "updatedSeen": 0, "revivedCount": 0})
    except Exception as e:
        return jsonify({"type": "error", "message": str(e)}), 500


@app.route('/api/whatsapp/followup/stream')
def api_whatsapp_followup_stream():
    """Server-Sent Events endpoint to stream live WhatsApp follow-up campaign execution."""
    batch = request.args.get('batch', '10')
    min_delay = request.args.get('min_delay', '25')
    max_delay = request.args.get('max_delay', '50')
    sender = request.args.get('sender', 'Deepaktusir')

    def event_stream():
        yield ": ping\n\n"
        cmd = [
            "node", "whatsapp_runner.js", "--run-followup",
            batch, min_delay, max_delay, sender
        ]
        proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            for line in iter(proc.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{") and line.endswith("}"):
                    try:
                        obj = json.loads(line)
                        yield f"data: {json.dumps(obj)}\n\n"
                    except Exception:
                        yield f"data: {json.dumps({'type': 'log', 'message': line})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'log', 'message': line})}\n\n"
            proc.stdout.close()
            proc.wait()
        except GeneratorExit:
            proc.terminate()

    return make_sse_response(event_stream())


@app.route('/download/<path:filename>')
def download_file(filename):
    filename = os.path.basename(filename)
    exports_dir = crm_manager.get_exports_dir()
    return send_from_directory(exports_dir, filename, as_attachment=True)


@app.route('/download/master-crm')
def download_master_crm():
    exports_dir = crm_manager.get_exports_dir()
    return send_from_directory(exports_dir, crm_manager.MASTER_FILE_NAME, as_attachment=True)


@app.route('/api/system/backup', methods=['POST'])
def api_system_backup():
    """Generates an instant full backup archive."""
    try:
        res = system_backup.create_system_backup()
        return jsonify({"success": True, "backup": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/system/reset', methods=['POST'])
def api_system_reset():
    """Creates a full backup archive, then resets workspace data to clean state."""
    try:
        res = system_backup.reset_system()
        return jsonify({"success": True, "backup": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/system/backups')
def api_system_backups():
    """Lists all available ZIP backups."""
    try:
        backups = system_backup.list_backups()
        return jsonify(backups)
    except Exception as e:
        return jsonify([]), 500


@app.route('/download/backup/<path:filename>')
def download_backup_file(filename):
    filename = os.path.basename(filename)
    """Download a backup ZIP archive."""
    backups_dir = os.path.join(BASE_DIR, "backups")
    return send_from_directory(backups_dir, filename, as_attachment=True)


if __name__ == "__main__":
    ip = get_local_ip()
    port = 5000
    print("\n" + "=" * 70)
    print("      PROPLEAD & WHATSAPP HUB - UNIFIED COMMAND CENTER")
    print("=" * 70)
    print(f"[*] Access from this computer: http://localhost:{port}")
    print(f"[*] Access from other devices: http://{ip}:{port}")
    print("=" * 70 + "\n")
    
    app.run(host="0.0.0.0", port=port, debug=False)
