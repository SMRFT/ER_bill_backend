import time
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from pymongo import MongoClient
import pytz

class Command(BaseCommand):
    help = 'Automatically closes active shifts at midnight (IST)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Midnight Shift Closer (IST)...'))
        
        ist = pytz.timezone("Asia/Kolkata")
        
        mongo_url = os.getenv("GLOBAL_DB_HOST")
        if not mongo_url:
            self.stdout.write(self.style.ERROR('GLOBAL_DB_HOST not found in environment variables.'))
            return

        client = MongoClient(mongo_url)
        db = client["ER_Billing"]
        collection = db["er_shiftdetails"]

        while True:
            # Get current time in IST
            now_ist = datetime.now(ist)
            
            # Check if it's the midnight hour (00:xx:xx) in India
            if now_ist.hour == 0:
                self.stdout.write(f'[{now_ist}] Midnight (IST) detected. Closing all active shifts...')
                
                # We save in MongoDB as UTC usually, so we'll convert the closure time to UTC 
                # but based on the exact moment of midnight in IST.
                now_utc = now_ist.astimezone(pytz.utc)

                result = collection.update_many(
                    {"is_active": True},
                    {
                        "$set": {
                            "endtime": now_utc,
                            "closing_status": "Auto Closed",
                            "is_active": False
                        }
                    }
                )
                
                if result.modified_count > 0:
                    self.stdout.write(self.style.SUCCESS(f'Successfully closed {result.modified_count} shifts.'))
                else:
                    self.stdout.write('No active shifts found to close.')

                # Sleep for an hour to avoid multiple triggers within the same midnight hour
                self.stdout.write('Sleeping for 1 hour...')
                time.sleep(3600)
            else:
                # Check every minute
                time.sleep(60)
