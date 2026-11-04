import os
import sys
import argparse
import asyncio
import subprocess
from datetime import datetime

# Set stdout encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from scraper import scrape_property_dealers, export_to_excel


def print_banner():
    banner = r"""
========================================================================
       PROPERTY DEALER & REAL ESTATE LEAD GENERATOR (EXCEL)
========================================================================
    Collects: Agency Name, Phone, Email, Website, Address, Rating, Reviews
------------------------------------------------------------------------
"""
    print(banner)


def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="Scrape property dealers and export to Excel.")
    parser.add_argument("-c", "--city", type=str, help="Target city or locality (e.g. 'South Delhi', 'Gurgaon', 'Mumbai')")
    parser.add_argument("-q", "--query", type=str, help="Custom search query (overrides city)")
    parser.add_argument("-m", "--max-results", type=int, default=0, help="Maximum number of leads to collect")
    parser.add_argument("-o", "--output", type=str, help="Custom output Excel filename/path")
    parser.add_argument("--no-email", action="store_true", help="Skip crawling websites for email addresses (faster)")
    parser.add_argument("--no-open", action="store_true", help="Do not automatically open the Excel file when completed")
    
    args = parser.parse_args()
    
    # 1. Determine search query
    query = args.query
    if not query:
        if args.city:
            query = f"Property dealers in {args.city}"
        else:
            print("Enter target city or locality (e.g., South Delhi, Gurgaon, Mumbai, London, Dubai):")
            user_city = input("Target City / Area > ").strip()
            if not user_city:
                user_city = "South Delhi"
                print(f"No city entered. Using default: {user_city}")
            query = f"Property dealers in {user_city}"
            
    # 2. Determine max results
    max_results = args.max_results
    if max_results <= 0:
        print("\nHow many leads would you like to collect? (e.g., 10, 25, 50, 100) [Default: 20]:")
        val = input("Max Results > ").strip()
        if val.isdigit() and int(val) > 0:
            max_results = int(val)
        else:
            max_results = 20
            
    # 3. Email extraction
    check_emails = not args.no_email
    
    # 4. Output filename
    if args.output:
        output_file = args.output
    else:
        # Create a clean filename from query and timestamp
        safe_name = "".join(c if c.isalnum() else "_" for c in query.replace("Property dealers in ", ""))
        safe_name = "_".join(filter(None, safe_name.split("_")))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{safe_name}_property_dealers_{timestamp}.xlsx")

    print(f"\n[+] Target Query: {query}")
    print(f"[+] Target Count: Up to {max_results} leads")
    print(f"[+] Email Scraping: {'Enabled' if check_emails else 'Disabled'}")
    print(f"[+] Destination: {output_file}\n")
    print("Starting data extraction... Please wait.\n")

    def progress_callback(msg):
        print(f" -> {msg}")

    start_time = datetime.now()
    results = asyncio.run(scrape_property_dealers(
        query=query,
        max_results=max_results,
        check_emails=check_emails,
        progress_callback=progress_callback
    ))
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    if not results:
        print("\n[!] No listings found or extraction was interrupted.")
        return

    print(f"\n[+] Extraction finished in {elapsed:.1f} seconds! Saving to Excel...")
    final_path = export_to_excel(results, output_file, search_query=query)
    csv_path = final_path.rsplit('.', 1)[0] + '.csv'
    
    print("\n" + "=" * 60)
    print("SUCCESSFULLY GENERATED LEAD FILES:")
    print(f"Excel File : {os.path.abspath(final_path)}")
    print(f"CSV Backup : {os.path.abspath(csv_path)}")
    print(f"Total Leads: {len(results)}")
    print(f"With Phone : {sum(1 for r in results if r.get('Phone Number'))}")
    print(f"With Email : {sum(1 for r in results if r.get('Email Address'))}")
    print(f"With Web   : {sum(1 for r in results if r.get('Website'))}")
    print("=" * 60 + "\n")
    
    if not args.no_open and sys.platform == "win32":
        try:
            os.startfile(os.path.abspath(final_path))
            print("[+] Opened Excel file automatically.")
        except Exception:
            pass


if __name__ == "__main__":
    main()
