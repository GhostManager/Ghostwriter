import requests
import json

# Replace with a URL, API, and ID key for your instance
url = "http://127.0.0.1:8000/oplog/api/entries/"
api_key = "API_KEY"
oplog_id = 1

headers = {
    "user-agent": "Python",
    "Content-Type": "application/json",
    "Authorization": f"Api-Key {api_key}",
}

data = {
    "start_date": None,
    "end_date": None,
    "source_ip": "WIN10VM (10.20.10.10)",
    "dest_ip": "127.0.0.1",
    "tool": "Beacon",
    "user_context": "ADMIN",
    "command": "execute_assembly /tmp/Seatbelt.exe logonevents",
    "description": "",
    "output": "",
    "comments": "",
    "operator_name": "Benny",
    "oplog_id": "1",
}

print("[+] Sending request to Ghostwriter...")

resp = requests.post(url, headers=headers, data=json.dumps(data))

if resp.status_code == 201:
    print(f"[+] Received code 201, so log was created: {resp.text}")
else:
    print(
        f"[!] Received status code {resp.status_code}, so something went wrong: {resp.text}"
    )
