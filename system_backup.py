"""
System Backup & Clean Reset Engine
Creates a timestamped compressed ZIP archive of all current data (exports, CRM, sent history, dead leads)
before cleanly resetting the database and workspace back to a fresh starting state.
"""

import os
import shutil
import zipfile
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
SENT_HISTORY_FILE = os.path.join(BASE_DIR, "sent_history.json")
DEAD_LEADS_FILE = os.path.join(BASE_DIR, "dead_leads.json")


def create_system_backup():
    """Creates a full timestamped backup in ./backups and compresses it into a .zip."""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder_name = f"backup_{timestamp}"
    backup_folder_path = os.path.join(BACKUPS_DIR, backup_folder_name)
    os.makedirs(backup_folder_path, exist_ok=True)
    
    backed_items = []
    
    # 1. Backup exports folder
    if os.path.exists(EXPORTS_DIR):
        dest_exports = os.path.join(backup_folder_path, "exports")
        shutil.copytree(EXPORTS_DIR, dest_exports, ignore=shutil.ignore_patterns('*.tmp'))
        backed_items.append("exports_folder")
        
    # 2. Backup sent_history.json
    if os.path.exists(SENT_HISTORY_FILE):
        shutil.copy2(SENT_HISTORY_FILE, os.path.join(backup_folder_path, "sent_history.json"))
        backed_items.append("sent_history.json")
        
    # 3. Backup dead_leads.json
    if os.path.exists(DEAD_LEADS_FILE):
        shutil.copy2(DEAD_LEADS_FILE, os.path.join(backup_folder_path, "dead_leads.json"))
        backed_items.append("dead_leads.json")
        
    # 4. Save metadata manifest
    meta = {
        "timestamp": timestamp,
        "created_at": datetime.now().isoformat(),
        "backed_items": backed_items,
        "backup_name": backup_folder_name
    }
    with open(os.path.join(backup_folder_path, "backup_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        
    # 5. Create a portable .zip archive
    zip_filename = f"{backup_folder_name}.zip"
    zip_path = os.path.join(BACKUPS_DIR, zip_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(backup_folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, backup_folder_path)
                zipf.write(file_path, arcname)
                
    return {
        "backup_name": backup_folder_name,
        "zip_filename": zip_filename,
        "zip_path": zip_path,
        "timestamp": timestamp,
        "items": backed_items
    }


def list_backups():
    """List all available backup archives."""
    if not os.path.exists(BACKUPS_DIR):
        return []
    
    files = []
    for f in os.listdir(BACKUPS_DIR):
        if f.endswith('.zip') and f.startswith('backup_'):
            fp = os.path.join(BACKUPS_DIR, f)
            size_kb = round(os.path.getsize(fp) / 1024, 1)
            mtime = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
            files.append({
                "filename": f,
                "size_kb": size_kb,
                "date": mtime
            })
    return sorted(files, key=lambda x: x["date"], reverse=True)


def reset_system():
    """
    1. Creates a complete backup archive first.
    2. Resets sent_history.json to empty.
    3. Resets dead_leads.json to empty.
    4. Cleans files in ./exports (retaining empty Master CRM template).
    """
    # Step 1: Create full backup first!
    backup_result = create_system_backup()
    
    # Step 2: Reset sent_history.json
    with open(SENT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2)
        
    # Step 3: Reset dead_leads.json
    with open(DEAD_LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2)
        
    # Step 4: Clear files in exports/ (except .gitkeep)
    if os.path.exists(EXPORTS_DIR):
        for f in os.listdir(EXPORTS_DIR):
            if f in ('.gitkeep', 'sample_leads.csv'):
                continue
            fp = os.path.join(EXPORTS_DIR, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                elif os.path.isdir(fp):
                    shutil.rmtree(fp)
            except Exception:
                pass
                
    # Step 5: Save fresh empty Master CRM
    try:
        import crm_manager
        crm_manager.save_master_records([])
    except Exception:
        pass
        
    return backup_result
