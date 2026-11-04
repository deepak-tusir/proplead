"""
Master CRM Lead Database Manager
Handles deduplication, lead status management, WhatsApp link generation,
enrichment, and Excel data validation dropdowns.
"""

import os
import re
from datetime import datetime
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

MASTER_FILE_NAME = "Master_CRM_Leads.xlsx"
MASTER_CSV_NAME = "Master_CRM_Leads.csv"

CRM_STATUSES = [
    "New Lead",
    "Contacted",
    "Follow Up",
    "Meeting Scheduled",
    "Converted",
    "Not Interested"
]


def get_exports_dir() -> str:
    """Returns the exports directory path."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    exports_dir = os.path.join(current_dir, "exports")
    os.makedirs(exports_dir, exist_ok=True)
    return exports_dir


def get_master_excel_path() -> str:
    return os.path.join(get_exports_dir(), MASTER_FILE_NAME)


def get_master_csv_path() -> str:
    return os.path.join(get_exports_dir(), MASTER_CSV_NAME)


def normalize_phone_key(phone: str) -> str:
    """Extract standard digits for deduplication."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', phone)
    if len(digits) >= 10:
        return digits[-10:] # Last 10 digits
    return digits


def generate_whatsapp_link(phone: str) -> str:
    """Generates direct clickable WhatsApp link."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', phone)
    if not digits:
        return ""
    # If 10 digits, default prefix 91 (India)
    if len(digits) == 10:
        digits = "91" + digits
    return f"https://wa.me/{digits}?text=Hi,%20I%20am%20reaching%20out%20regarding%20property%20consultancy."


def load_master_records() -> list[dict]:
    """Loads existing master records from CSV or Excel."""
    csv_path = get_master_csv_path()
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, dtype=str).fillna("")
            return df.to_dict(orient="records")
        except Exception:
            pass
            
    xlsx_path = get_master_excel_path()
    if os.path.exists(xlsx_path):
        try:
            df = pd.read_excel(xlsx_path, dtype=str).fillna("")
            return df.to_dict(orient="records")
        except Exception:
            pass
            
    return []


def sync_to_master_crm(new_leads: list[dict], source_area: str = "") -> dict:
    """
    Syncs newly scraped leads into the Master CRM database.
    Performs smart deduplication by phone and agency name,
    enriches missing fields, and adds CRM management columns.
    """
    existing_records = load_master_records()
    
    # Map existing records by phone_key and name_key
    phone_map = {}
    name_map = {}
    for idx, rec in enumerate(existing_records):
        pk = normalize_phone_key(rec.get("Phone Number", ""))
        if pk:
            phone_map[pk] = idx
        name_key = rec.get("Dealer / Agency Name", "").strip().lower()
        if name_key:
            name_map[name_key] = idx
            
    new_added_count = 0
    updated_count = 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for lead in new_leads:
        raw_phone = lead.get("Phone Number", "")
        pk = normalize_phone_key(raw_phone)
        name_key = lead.get("Dealer / Agency Name", "").strip().lower()
        
        target_idx = None
        if pk and pk in phone_map:
            target_idx = phone_map[pk]
        elif name_key and name_key in name_map:
            target_idx = name_map[name_key]
            
        if target_idx is not None:
            # Existing lead: enrich missing fields
            existing = existing_records[target_idx]
            modified = False
            
            # Enrich email
            if not existing.get("Email Address") and lead.get("Email Address"):
                existing["Email Address"] = lead.get("Email Address")
                modified = True
            # Enrich website
            if not existing.get("Website") and lead.get("Website"):
                existing["Website"] = lead.get("Website")
                modified = True
            # Enrich address
            if not existing.get("Full Address") and lead.get("Full Address"):
                existing["Full Address"] = lead.get("Full Address")
                modified = True
            # Enrich ratings
            if not existing.get("Rating") and lead.get("Rating"):
                existing["Rating"] = lead.get("Rating")
                existing["Reviews Count"] = lead.get("Reviews Count", "")
                modified = True
                
            if modified:
                updated_count += 1
        else:
            # Brand new lead
            wa_link = generate_whatsapp_link(raw_phone)
            crm_entry = {
                "Lead Status": "New Lead",
                "Dealer / Agency Name": lead.get("Dealer / Agency Name", ""),
                "Phone Number": raw_phone,
                "WhatsApp Link": wa_link,
                "Email Address": lead.get("Email Address", ""),
                "Website": lead.get("Website", ""),
                "Full Address": lead.get("Full Address", ""),
                "Rating": lead.get("Rating", ""),
                "Reviews Count": lead.get("Reviews Count", ""),
                "Category": lead.get("Category", "Real Estate Agency"),
                "Source Area": source_area or "Web Scrape",
                "Date Added": today_str,
                "Notes / Remarks": "",
                "Google Maps Link": lead.get("Google Maps Link", "")
            }
            existing_records.append(crm_entry)
            new_idx = len(existing_records) - 1
            if pk:
                phone_map[pk] = new_idx
            if name_key:
                name_map[name_key] = new_idx
            new_added_count += 1

    # Save to Master Excel & CSV
    save_master_workbook(existing_records)
    
    return {
        "total_in_master": len(existing_records),
        "newly_added": new_added_count,
        "updated_existing": updated_count,
        "duplicates_skipped": len(new_leads) - new_added_count
    }


def save_master_workbook(records: list[dict]):
    """Saves records to the Master CRM Excel file with dropdowns, styling, and CSV."""
    excel_path = get_master_excel_path()
    csv_path = get_master_csv_path()
    
    # Save CSV
    df = pd.DataFrame(records)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # Build styled Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Master CRM Database"
    
    # Title Block
    ws.merge_cells("A1:N1")
    title_cell = ws["A1"]
    title_cell.value = "CENTRAL PROPERTY DEALER CRM DATABASE"
    title_cell.font = Font(name="Segoe UI", size=15, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="0F2942", end_color="0F2942", fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36
    
    # Subtitle
    ws.merge_cells("A2:N2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Last Synchronized: {datetime.now().strftime('%d %B %Y, %I:%M %p')} | Total Active Leads: {len(records)}"
    sub_cell.font = Font(name="Segoe UI", size=10, italic=True, color="4A5568")
    sub_cell.fill = PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20
    
    # Headers
    headers = [
        "S.No",
        "Lead Status",
        "Dealer / Agency Name",
        "Phone Number",
        "WhatsApp Direct",
        "Email Address",
        "Website",
        "Full Address",
        "Rating",
        "Reviews",
        "Category",
        "Source Area",
        "Date Added",
        "Notes / Remarks"
    ]
    
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
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

    # Data rows
    zebra_even = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
    zebra_odd = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    regular_font = Font(name="Segoe UI", size=10)
    link_font = Font(name="Segoe UI", size=10, color="0000EE", underline="single")
    wa_font = Font(name="Segoe UI", size=10, bold=True, color="25D366", underline="single")
    
    for row_idx, item in enumerate(records, 5):
        ws.row_dimensions[row_idx].height = 22
        fill = zebra_even if row_idx % 2 == 0 else zebra_odd
        
        status = str(item.get("Lead Status") or "New Lead")
        wa_url = item.get("WhatsApp Link") or generate_whatsapp_link(str(item.get("Phone Number", "")))
        web_url = str(item.get("Website", "")) if pd.notna(item.get("Website")) else ""
        if web_url == "nan":
            web_url = ""
            
        row_vals = [
            row_idx - 4,
            status,
            "" if pd.isna(item.get("Dealer / Agency Name")) else str(item.get("Dealer / Agency Name", "")),
            "" if pd.isna(item.get("Phone Number")) else str(item.get("Phone Number", "")),
            "Chat on WhatsApp" if wa_url else "",
            "" if pd.isna(item.get("Email Address")) else str(item.get("Email Address", "")),
            web_url,
            "" if pd.isna(item.get("Full Address")) else str(item.get("Full Address", "")),
            "" if pd.isna(item.get("Rating")) else str(item.get("Rating", "")),
            "" if pd.isna(item.get("Reviews Count")) else str(item.get("Reviews Count", "")),
            "" if pd.isna(item.get("Category")) else str(item.get("Category", "")),
            "" if pd.isna(item.get("Source Area")) else str(item.get("Source Area", "")),
            "" if pd.isna(item.get("Date Added")) else str(item.get("Date Added", "")),
            "" if pd.isna(item.get("Notes / Remarks")) else str(item.get("Notes / Remarks", ""))
        ]
        
        for col_idx, val in enumerate(row_vals, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = card_border
            cell.fill = fill
            cell.font = regular_font
            
            if col_idx == 1: # S.No
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.value = val
            elif col_idx == 2: # Lead Status
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.value = val
                # Status highlight
                if val == "Converted":
                    cell.fill = PatternFill(start_color="D1E7DD", end_color="D1E7DD", fill_type="solid")
                elif val == "Contacted":
                    cell.fill = PatternFill(start_color="CFF4FC", end_color="CFF4FC", fill_type="solid")
                elif val == "Follow Up":
                    cell.fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
            elif col_idx in (4, 9, 10, 13):
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.value = val
            elif col_idx == 5 and val and wa_url: # WhatsApp Link
                cell.value = val
                cell.font = wa_font
                cell.hyperlink = str(wa_url)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 7 and val and str(val).startswith("http"): # Website Link
                cell.value = val
                cell.font = link_font
                cell.hyperlink = str(val)
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.value = val

    # Setup Lead Status Data Validation Dropdown for column B
    status_formula = f'"{",".join(CRM_STATUSES)}"'
    dv = DataValidation(type="list", formula1=status_formula, allow_blank=True)
    dv.error = 'Your entry is not in the list'
    dv.errorTitle = 'Invalid Lead Status'
    dv.prompt = 'Select lead status from list'
    dv.promptTitle = 'Lead Status'
    max_row = max(len(records) + 5, 200)
    dv.add(f"B5:B{max_row}")
    ws.add_data_validation(dv)
    
    # Auto column widths
    widths = {
        1: 8,   # S.No
        2: 18,  # Lead Status
        3: 32,  # Dealer Name
        4: 18,  # Phone
        5: 20,  # WhatsApp
        6: 28,  # Email
        7: 30,  # Website
        8: 42,  # Address
        9: 10,  # Rating
        10: 12, # Reviews
        11: 22, # Category
        12: 18, # Source Area
        13: 14, # Date Added
        14: 30  # Notes
    }
    for col_idx, width in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width
        
    wb.save(excel_path)
