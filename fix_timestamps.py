import os
import time
import datetime

oldest_supported = datetime.datetime(1980, 1, 1).timestamp()
fixed_count = 0

for root, dirs, files in os.walk('.'):
    # Skip virtual environment and reflex hidden dirs
    if '.venv' in root or '.web' in root or '.git' in root:
        continue
        
    for f in files:
        path = os.path.join(root, f)
        try:
            mtime = os.path.getmtime(path)
            if mtime < oldest_supported:
                print(f"Fixing old file: {path} - {datetime.datetime.fromtimestamp(mtime)}")
                # update to current time
                os.utime(path, None)
                fixed_count += 1
        except Exception as e:
            print(f"Error accessing {path}: {e}")

print(f"Finished. Fixed {fixed_count} files.")
