#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Standard Libraries
import json
import random
import socket
import string
import struct
import sys

try:
    import requests  # noqa isort:skip
except Exception:
    print("[!] Need the `requests` library installed\n\n" "\tpython install -U requests")
    exit()


def show_help():
    message = (
        "\nActivity Log Example\n"
        "\nThere are three required, positional arguments:\n\n"
        "\tpython3 post_activity_logs.py <api_key> <oplog_id> <count> <server>\n\n"
        "Provide your API key, the related Oplog's ID, and how many entries to create.\n\n"
        "You can also provide an optional fourth argument, the address of your server. "
        "The default is: http://127.0.0.1:8000"
    )
    print(message)


if len(sys.argv) >= 3:
    api_key = sys.argv[1]

    oplog_id = sys.argv[2]
    if not oplog_id.isdigit():
        print(f"[!] Your Oplog ID argument must be an integer. You provided: {oplog_id}")
        show_help()
        exit()

    count = sys.argv[3]
    if not count.isdigit():
        print(f"[!] Your `count` argument must be an integer. You provided: {count}")
        show_help()
        exit()
    else:
        count = int(count)

    if len(sys.argv) > 4:
        server = sys.argv[4].rstrip("/")
    else:
        server = "http://127.0.0.1:8000"

    url = f"{server}/oplog/api/entries/"
    test_url = f"{server}/oplog/api/oplogs/{oplog_id}"

    print(
        f'[+] Creating {count} entries for Oplog ID #{oplog_id} with the key "{api_key}"'
    )
    print(f"[*] Testing the key with your server: {test_url}")

    headers = {
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ghostwriter/2.2",
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {api_key}",
    }

    resp = requests.get(test_url, headers=headers)
    if resp.status_code == 200:
        print("[*] Ghostwriter returned a 200 response (all good)")
    elif resp.status_code == 403:
        print("[!] Ghostwriter returned a 403 response (bad API key)")
        exit()
    elif resp.status_code == 404:
        print("[!] Ghostwriter returned a 404 response for your Oplog ID (doesn't exist)")
        exit()
    else:
        print("[!] Failed to connect and authenticate!")
        exit()

    print("[*] Proceeding with log creation and making some random data...")

    # Generate some test data
    domain = "GW"
    fqdn = "GHOSTWRITER.LOCAL"

    addresses = []
    hostnames = []
    random_hosts = []

    total = 20
    letters = string.ascii_uppercase

    for i in range(total):
        addresses.append(
            socket.inet_ntoa(struct.pack(">I", random.randint(1, 0xFFFFFFFF)))
        )

    for i in range(total):
        hostname = "".join(random.choice(letters) for i in range(8))
        rand_digit = random.randint(1, 9)
        hostname += str(rand_digit)
        hostnames.append(hostname)

    for i in addresses:
        index = random.choice(range(len(hostnames)))
        host = f"{hostnames[index]}@{fqdn} ({i})"
        random_hosts.append(host)
        del hostnames[index]

    tools = ["Beacon", "Mythic", "Covenant"]
    users = [
        "SYSTEM *",
        ".\\ADMINISTRATOR",
        f"{domain}\\PATSY",
        f"{domain}\\VICTIM",
        f"{domain}\\_VULN_SERVICE01",
        f"{domain}\\DFM",
        f"{domain}\\JFRANK",
    ]
    commands = [
        "ls C:/Windows/System32",
        f"ls \\\\{fqdn}\\sysvol",
        "mimikatz sekurlsa::logonpasswords",
        "download C:\\Users\\dfm\\_secret\\passwords.txt",
        "execute_assembly /tmp/Seatbelt.exe logonevents",
        "execute_assembly SharpDPAPI_4.0.exe triage",
        "rev2self",
        f"make_token {random.choice(users)} Password124",
        "screenshot 5248 x64",
        "./rm rf *",
        "shell whoami",
        "jobs",
        "spawnto x64 C:\\Windows\\System32\\dllhost.exe",
        f"execute_assembly Rubeus_4.0.exe asktgt /user:{random.choice(users)} /rc4:D37F36A61B28659DEAE644DE4915D42A /ptt",
        f"execute_assembly /home/hacker/sick_payloads/letsgo.exe computername={random.choice(random_hosts)}@{fqdn}",
        f"pth {random.choice(users)} E77069B0C87148840559580DBBDD00AD",
    ]
    operators = [
        "cmaddalena",
        "benny",
        "aghost",
        "achiles",
        "dheinsen",
        "pvenkman",
        "rstantz",
        "espengler",
        "wzeddmore",
    ]

    # POST data template dict
    data = {
        "start_date": None,
        "end_date": None,
        "source_ip": "",
        "dest_ip": "",
        "tool": "",
        "user_context": "",
        "command": "",
        "description": "",
        "output": "",
        "comments": "",
        "operator_name": "",
        "oplog_id": f"{oplog_id}",
    }

    for i in range(count):
        data["source_ip"] = random.choice(random_hosts)
        data["dest_ip"] = random.choice(random_hosts)
        data["tool"] = random.choice(tools)
        data["user_context"] = random.choice(users)
        data["command"] = random.choice(commands)
        data["operator_name"] = random.choice(operators)
        data["comments"] = f"Sample log entry #{i}"
        resp = requests.post(url, headers=headers, data=json.dumps(data))

        if not resp.status_code == 201:
            print(
                f"[!] Log creation failed – Received code {resp.status_code}: {resp.text}"
            )
            exit()

        print(f"... Created {i}/{count} log entries")
else:
    show_help()
