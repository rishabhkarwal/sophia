import urllib.request
import re
import os

base_url = "http://tablebase.sesse.net/syzygy/3-4-5/"

try:
    with urllib.request.urlopen(base_url) as response: html = response.read().decode('utf-8')
except Exception as e:
    print(f"Error connecting to server: {e}")
    exit()

files = re.findall(r'href="([^"]+\.(?:rtbw|rtbz))"', html)

files = sorted(list(set(files)))

for i, filename in enumerate(files):
    full_url = base_url + filename
    
    if os.path.exists(filename):
        print(f"[{i + 1}/{len(files)}] {filename} exists, skipping...")
        continue
        
    print(f"[{i + 1}/{len(files)}] Downloading {filename}...")
    try:
        urllib.request.urlretrieve(full_url, filename)
    except Exception as e:
        print(f"Failed to download {filename}: {e}")

print("Complete")