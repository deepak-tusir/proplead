"""
Property Dealer & Multi-Niche Business Lead Scraper
Extracts names, phone numbers, websites, emails, addresses, ratings, and Google Maps links.
Exports into a formatted Excel (.xlsx) workbook and CSV.
"""

import os
import sys
import re
import time
import asyncio
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from playwright.async_api import async_playwright

# Set stdout encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Disable SSL warnings for requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
EXCLUDED_EMAIL_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.js', '.css', '.woff', '.ttf', '.ico')
EXCLUDED_DOMAINS = (
    'sentry.io', 'wixpress.com', 'googleapis.com', 'gstatic.com',
    'cloudflare.com', 'schema.org', 'example.com', 'w3.org', 'wordpress.org', 'github.com'
)
EXCLUDED_PREFIXES = ('sentry', 'noreply', 'no-reply', 'mailer-daemon', 'donotreply')
SKIP_WEBSITE_DOMAINS = ('facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'linkedin.com', 'youtube.com')


def clean_phone(text: str) -> str:
    """Format and clean phone number text, stripping icon artifacts."""
    if not text:
        return ""
    # Strip any leading icon symbols (e.g. \ue0b0 or \u202d or similar glyphs)
    cleaned = re.sub(r'^[^\d\+]+', '', text)
    cleaned = re.sub(r'[^\d\+\-\s\(\)]', '', cleaned).strip()
    return cleaned


def clean_address(text: str) -> str:
    """Clean location address string."""
    if not text:
        return ""
    # Strip leading icon symbols (e.g. \ue0c8 or )
    cleaned = re.sub(r'^[\s\ue0c8]+', '', text).strip()
    return cleaned


def is_valid_email(email: str) -> bool:
    """Validate that the extracted email is legitimate and not a code artifact or placeholder."""
    email = email.strip().lower()
    if '@' not in email:
        return False
    user, domain = email.split('@', 1)
    if not user or not domain or '.' not in domain:
        return False
    
    # Exclude tracking domains
    for d in EXCLUDED_DOMAINS:
        if d in domain:
            return False
            
    # Exclude dummy/generic prefixes
    for p in EXCLUDED_PREFIXES:
        if user.startswith(p):
            return False
            
    # Exclude assets ending with file extensions
    for ext in EXCLUDED_EMAIL_EXTS:
        if email.endswith(ext):
            return False
            
    # Exclude npm / library versions like 'leaflet@1.9.4'
    if re.search(r'@\d+\.\d+', email):
        return False

    return True



def is_safe_url(url: str) -> bool:
    """Blocks loopbacks, private IPs, and non-http schemes to prevent SSRF."""
    try:
        import ipaddress
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ('localhost', '127.0.0.1', '0.0.0.0', '::1'):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass  # Valid domain name
        return True
    except Exception:
        return False

def extract_emails_from_website(url: str, timeout: int = 7) -> str:
    """
    Crawls business website homepage and contact/about page to harvest email addresses.
    """
    if not url or not url.startswith('http') or not is_safe_url(url):
        return ""
        
    for skip_d in SKIP_WEBSITE_DOMAINS:
        if skip_d in url.lower():
            return ""
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    
    found_emails = set()
    pages_to_check = [url]
    
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, verify=False)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. Search mailto: links
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.lower().startswith('mailto:'):
                    clean = href.split(':', 1)[1].split('?')[0].strip()
                    if is_valid_email(clean):
                        found_emails.add(clean.lower())
                        
            # 2. Search regex in HTML body
            for match in EMAIL_REGEX.findall(resp.text):
                if is_valid_email(match):
                    found_emails.add(match.lower())
                    
            # 3. If no email on homepage, check for Contact or About links
            if not found_emails:
                for a in soup.find_all('a', href=True):
                    href = a['href'].lower()
                    if any(k in href for k in ('contact', 'about', 'reach-us', 'contact-us')):
                        target_url = urllib.parse.urljoin(url, a['href'])
                        if target_url != url:
                            pages_to_check.append(target_url)
                            break
    except Exception:
        pass
        
    # Check secondary contact page if found and homepage had none
    if len(pages_to_check) > 1 and not found_emails:
        try:
            resp = requests.get(pages_to_check[1], headers=headers, timeout=timeout, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.lower().startswith('mailto:'):
                        clean = href.split(':', 1)[1].split('?')[0].strip()
                        if is_valid_email(clean):
                            found_emails.add(clean.lower())
                for match in EMAIL_REGEX.findall(resp.text):
                    if is_valid_email(match):
                        found_emails.add(match.lower())
        except Exception:
            pass
            
    return ", ".join(list(found_emails)[:3])


async def scrape_property_dealers(
    query: str,
    max_results: int = 30,
    check_emails: bool = True,
    progress_callback=None
) -> list[dict]:
    """
    Main scraping function using Playwright to query Google Maps and retrieve multi-niche business leads.
    """
    results = []
    
    # Format search query dynamically for multi-niche intelligence
    clean_query = query.strip()
    if " in " in clean_query.lower():
        # Complete query provided e.g. "Interior Designers in South Delhi"
        search_term = clean_query
    elif any(k in clean_query.lower() for k in (
        'designer', 'interior', 'architect', 'clinic', 'dental', 'hospital',
        'hotel', 'resort', 'banquet', 'coaching', 'institute', 'builder',
        'developer', 'wedding', 'planner', 'car', 'solar', 'furniture',
        'travel', 'property', 'real estate', 'realtor', 'broker', 'manufacturer'
    )):
        search_term = clean_query
    else:
        # Fallback only when a lone city was provided
        search_term = f"Property dealers in {clean_query}"
        
    maps_search_url = f"https://www.google.com/maps/search/{urllib.parse.quote(search_term)}"
    
    if progress_callback:
        progress_callback(f"Opening browser to search: '{search_term}'...")
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = await context.new_page()
        
        try:
            await page.goto(maps_search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3500)
            
            feed_locator = page.locator('div[role="feed"]')
            if await feed_locator.count() == 0:
                if progress_callback:
                    progress_callback("Waiting for results list to render...")
                await page.wait_for_timeout(4000)
                
            # Scroll feed to collect enough place URLs
            place_urls = []
            seen_urls = set()
            scroll_attempts = 0
            max_scrolls = max(8, (max_results // 3) + 4)
            
            if progress_callback:
                progress_callback("Scanning listings and scrolling down for more results...")
                
            while len(place_urls) < max_results and scroll_attempts < max_scrolls:
                links = await page.locator('div[role="feed"] a[href*="/maps/place/"]').all()
                for link in links:
                    href = await link.get_attribute("href")
                    if href and href not in seen_urls:
                        seen_urls.add(href)
                        place_urls.append(href)
                        if len(place_urls) >= max_results:
                            break
                            
                if len(place_urls) >= max_results:
                    break
                    
                # Scroll down in the results container
                await page.locator('div[role="feed"]').evaluate('el => el.scrollBy(0, 1200)')
                await page.wait_for_timeout(1400)
                scroll_attempts += 1
                
                # Check for "You've reached the end of the list"
                end_el = page.locator("text=You've reached the end of the list")
                if await end_el.count() > 0:
                    break

            total_found = len(place_urls)
            if progress_callback:
                progress_callback(f"Found {total_found} business listings. Extracting complete details...")
                
            # Extract detailed information for each place
            detail_page = await context.new_page()
            
            for index, url in enumerate(place_urls, 1):
                try:
                    await detail_page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await detail_page.wait_for_timeout(1800)
                    
                    # Business Name
                    name = ""
                    title_el = detail_page.locator('h1.DUwDvf, div.lMbq3e h1, h1')
                    for t in await title_el.all():
                        t_text = await t.inner_text()
                        if t_text and t_text != "Results":
                            name = t_text.strip()
                            break
                    if not name:
                        # Fallback from URL
                        match = re.search(r'/maps/place/([^/]+)/', url)
                        name = urllib.parse.unquote(match.group(1)).replace('+', ' ') if match else "Business"
                        
                    # Phone
                    phone_el = detail_page.locator('button[data-item-id*="phone:"], button[aria-label*="Phone:"]')
                    raw_phone = await phone_el.first.inner_text() if await phone_el.count() > 0 else ""
                    phone = clean_phone(raw_phone)
                    
                    # Website
                    web_el = detail_page.locator('a[data-item-id="authority"], a[aria-label*="Website:"]')
                    website = await web_el.first.get_attribute("href") if await web_el.count() > 0 else ""
                    
                    # Full Address
                    addr_el = detail_page.locator('button[data-item-id="address"], button[aria-label*="Address:"]')
                    raw_addr = await addr_el.first.inner_text() if await addr_el.count() > 0 else ""
                    address = clean_address(raw_addr)
                    
                    # Rating & Review Count
                    rating_el = detail_page.locator('div.F7nice span[aria-hidden="true"]').first
                    rating = await rating_el.inner_text() if await rating_el.count() > 0 else ""
                    
                    rev_el = detail_page.locator('div.F7nice span[aria-label*="reviews"]')
                    reviews = await rev_el.inner_text() if await rev_el.count() > 0 else ""
                    reviews = reviews.replace('(', '').replace(')', '').strip()
                    
                    # Category / Business Type
                    cat_el = detail_page.locator('button[jsaction*="category"]')
                    category = await cat_el.first.inner_text() if await cat_el.count() > 0 else "Business"
                    
                    # Email harvesting from website
                    emails = ""
                    if check_emails and website:
                        if progress_callback:
                            progress_callback(f"[{index}/{total_found}] {name} - Checking website for email...")
                        emails = extract_emails_from_website(website)
                    else:
                        if progress_callback:
                            progress_callback(f"[{index}/{total_found}] {name}")
                            
                    item = {
                        "Dealer / Agency Name": name,
                        "Phone Number": phone,
                        "Email Address": emails,
                        "Website": website,
                        "Full Address": address,
                        "Rating": rating,
                        "Reviews Count": reviews,
                        "Category": category,
                        "Google Maps Link": url
                    }
                    results.append(item)
                    
                except Exception as ex:
                    if progress_callback:
                        progress_callback(f"[{index}/{total_found}] Skipped listing due to timeout: {ex}")
                    continue
                    
            await detail_page.close()
        finally:
            await browser.close()
            
    return results


def export_to_excel(data: list[dict], output_path: str, search_query: str = "") -> str:
    """
    Saves extracted records into a professionally styled Excel workbook.
    """
    if not output_path.endswith('.xlsx'):
        output_path += '.xlsx'
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Business Leads"
    
    # Title Block
    ws.merge_cells("A1:I1")
    title_cell = ws["A1"]
    title_cell.value = f"Business Directory - {search_query.title() if search_query else 'Leads'}"
    title_cell.font = Font(name="Segoe UI", size=15, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36
    
    # Subtitle / Metadata Row
    ws.merge_cells("A2:I2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Generated on {datetime.now().strftime('%d %B %Y, %I:%M %p')} | Total Records: {len(data)}"
    sub_cell.font = Font(name="Segoe UI", size=10, italic=True, color="4A5568")
    sub_cell.fill = PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20
    
    # Headers
    headers = [
        "S.No",
        "Dealer / Agency Name",
        "Phone Number",
        "Email Address",
        "Website",
        "Full Address",
        "Rating",
        "Reviews Count",
        "Category",
        "Google Maps Link"
    ]
    
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    thin_border_side = Side(border_style="thin", color="CBD5E0")
    card_border = Border(top=thin_border_side, left=thin_border_side, right=thin_border_side, bottom=thin_border_side)
    
    ws.row_dimensions[4].height = 28
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = card_border

    # Data Rows Styling
    zebra_even = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
    zebra_odd = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    regular_font = Font(name="Segoe UI", size=10)
    link_font = Font(name="Segoe UI", size=10, color="0000EE", underline="single")
    
    for row_idx, item in enumerate(data, 5):
        ws.row_dimensions[row_idx].height = 22
        fill = zebra_even if row_idx % 2 == 0 else zebra_odd
        
        row_values = [
            row_idx - 4,
            item.get("Dealer / Agency Name", ""),
            item.get("Phone Number", ""),
            item.get("Email Address", ""),
            item.get("Website", ""),
            item.get("Full Address", ""),
            item.get("Rating", ""),
            item.get("Reviews Count", ""),
            item.get("Category", ""),
            item.get("Google Maps Link", "")
        ]
        
        for col_idx, val in enumerate(row_values, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = card_border
            cell.fill = fill
            cell.font = regular_font
            
            # Alignments
            if col_idx == 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.value = val
            elif col_idx in (3, 7, 8):
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.value = val
            elif col_idx == 5 and val: # Website link
                cell.value = val
                cell.font = link_font
                cell.hyperlink = val
                cell.alignment = Alignment(horizontal="left", vertical="center")
            elif col_idx == 10 and val: # Maps link
                cell.value = "View on Maps"
                cell.font = link_font
                cell.hyperlink = val
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.value = val
                
    # Auto-adjust column widths
    column_widths = {
        1: 8,   # S.No
        2: 34,  # Business Name
        3: 18,  # Phone Number
        4: 28,  # Email
        5: 32,  # Website
        6: 45,  # Address
        7: 10,  # Rating
        8: 14,  # Reviews
        9: 22,  # Category
        10: 16  # Maps Link
    }
    for col_idx, width in column_widths.items():
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    # Add Summary Sheet
    summary_ws = wb.create_sheet(title="Summary Statistics")
    summary_ws.column_dimensions['A'].width = 25
    summary_ws.column_dimensions['B'].width = 20
    
    summary_ws["A1"] = "Metric"
    summary_ws["B1"] = "Count"
    summary_ws["A1"].font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    summary_ws["B1"].font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    summary_ws["A1"].fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    summary_ws["B1"].fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    
    total = len(data)
    with_phone = sum(1 for d in data if d.get("Phone Number"))
    with_web = sum(1 for d in data if d.get("Website"))
    with_email = sum(1 for d in data if d.get("Email Address"))
    with_addr = sum(1 for d in data if d.get("Full Address"))
    
    metrics = [
        ("Total Leads Collected", total),
        ("With Phone Numbers", with_phone),
        ("With Websites", with_web),
        ("With Email Addresses", with_email),
        ("With Full Addresses", with_addr)
    ]
    for r_idx, (m, c) in enumerate(metrics, 2):
        summary_ws.cell(row=r_idx, column=1, value=m)
        summary_ws.cell(row=r_idx, column=2, value=c)
        summary_ws.cell(row=r_idx, column=1).border = card_border
        summary_ws.cell(row=r_idx, column=2).border = card_border

    wb.save(output_path)
    
    # Also save CSV backup
    csv_path = output_path.rsplit('.', 1)[0] + '.csv'
    import pandas as pd
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    return output_path
