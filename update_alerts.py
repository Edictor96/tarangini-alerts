#!/usr/bin/env python3
"""
Helper script to run the INCOIS scraper and update alerts.json
This can be run manually or scheduled as a cron job.

Usage:
    python update_alerts.py
"""

import sys
import subprocess

def main():
    print("=" * 60)
    print("Taranगिनी - Alert Update Script")
    print("=" * 60)
    print()
    
    try:
        # Run the scraper
        print("Running INCOIS scraper...")
        result = subprocess.run(
            [sys.executable, "incois_scraper.py"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("✅ Scraper completed successfully!")
            print()
            print("Output:")
            print(result.stdout)
            
            if result.stderr:
                print("\nWarnings/Errors:")
                print(result.stderr)
                
            print()
            print("=" * 60)
            print("✅ Alerts have been updated in alerts.json")
            print("The web server will automatically load the new alerts.")
            print("=" * 60)
            return 0
        else:
            print("❌ Scraper failed!")
            print("\nError output:")
            print(result.stderr)
            return 1
            
    except subprocess.TimeoutExpired:
        print("❌ Scraper timed out (>120 seconds)")
        return 1
    except Exception as e:
        print(f"❌ Error running scraper: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
