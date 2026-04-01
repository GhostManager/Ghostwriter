"""
Seed script for populating Ghostwriter with test data.

Run via: docker compose -f local.yml exec django python manage.py shell < scripts/seed_test_data.py
"""

from datetime import date, timedelta
from django.contrib.auth import get_user_model
from ghostwriter.rolodex.models import (
    Client,
    ClientContact,
    ClientInvite,
    Project,
    ProjectAssignment,
    ProjectCollabNote,
    ProjectCollabNoteField,
    ProjectInvite,
    ProjectObjective,
    ProjectScope,
    ProjectTarget,
)
from ghostwriter.rolodex.models import ProjectType, ProjectRole
from ghostwriter.reporting.models import Severity, FindingType

User = get_user_model()

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
users = {}
user_specs = [
    ("alice", "alice@example.com", "Alice Rivera", "TestPass123!"),
    ("bob", "bob@example.com", "Bob Chen", "TestPass123!"),
    ("charlie", "charlie@example.com", "Charlie Okafor", "TestPass123!"),
]
for username, email, name, pw in user_specs:
    u, created = User.objects.get_or_create(
        username=username,
        defaults=dict(email=email, name=name, role="user"),
    )
    if created:
        u.set_password(pw)
        u.save()
        print(f"  Created user: {username} / {pw}")
    else:
        print(f"  User already exists: {username}")
    users[username] = u

mgr, created = User.objects.get_or_create(
    username="manager",
    defaults=dict(email="mgr@example.com", name="Morgan Taylor", role="manager"),
)
if created:
    mgr.set_password("TestPass123!")
    mgr.save()
    print("  Created manager: manager / TestPass123!")
else:
    print("  Manager already exists: manager")
users["manager"] = mgr

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
pt_pentest = ProjectType.objects.get(project_type="Penetration Test")
pt_webapp = ProjectType.objects.get(project_type="Web Application Assessment")
pt_redteam = ProjectType.objects.get(project_type="Red Team")

role_lead = ProjectRole.objects.get(project_role="Assessment Lead")
role_operator = ProjectRole.objects.get(project_role="Operator")

clients_data = [
    {
        "name": "Acme Corporation",
        "short_name": "ACME",
        "codename": "THUNDERBOLT",
        "contacts": [
            ("Jane Doe", "jane.doe@acme.example.com", "CISO", "555-0101"),
            ("John Smith", "john.smith@acme.example.com", "IT Director", "555-0102"),
        ],
        "projects": [
            {
                "codename": "IRON FALCON",
                "project_type": pt_pentest,
                "lead": "alice",
                "operators": ["bob"],
                "start": date.today() - timedelta(days=14),
                "end": date.today() + timedelta(days=16),
                "scopes": ["10.10.0.0/16", "web.acme.example.com", "api.acme.example.com"],
                "targets": ["Domain Controller (DC01)", "Exchange Server", "VPN Gateway"],
                "notes_tree": [
                    {"title": "Reconnaissance", "type": "folder", "children": [
                        {"title": "External Recon", "type": "note", "content": "<p>Ran subdomain enumeration against acme.example.com. Found 14 subdomains.</p>"},
                        {"title": "OSINT Findings", "type": "note", "content": "<p>LinkedIn reveals 3 IT admins. Password policy doc leaked on Pastebin (expired).</p>"},
                    ]},
                    {"title": "Exploitation", "type": "folder", "children": [
                        {"title": "Initial Access", "type": "note", "content": "<p>Phishing payload delivered via macro-enabled doc. User jane.doe clicked.</p>"},
                        {"title": "Lateral Movement", "type": "note", "content": "<p>Used Pass-the-Hash from workstation WS-042 to reach DC01.</p>"},
                    ]},
                    {"title": "Meeting Notes", "type": "note", "content": "<p>Kickoff call 2026-03-17. Client wants focus on AD attack paths.</p>"},
                ],
            },
        ],
    },
    {
        "name": "Globex Industries",
        "short_name": "GLOBEX",
        "codename": "NIGHTSHADE",
        "contacts": [
            ("Hank Scorpio", "hank@globex.example.com", "CEO", "555-0200"),
        ],
        "projects": [
            {
                "codename": "SHADOW NEXUS",
                "project_type": pt_webapp,
                "lead": "bob",
                "operators": ["charlie"],
                "start": date.today() - timedelta(days=7),
                "end": date.today() + timedelta(days=23),
                "scopes": ["https://portal.globex.example.com", "https://api.globex.example.com/v2"],
                "targets": ["Customer Portal", "REST API v2", "Admin Panel"],
                "notes_tree": [
                    {"title": "API Testing", "type": "folder", "children": [
                        {"title": "Authentication Bypass", "type": "note", "content": "<p>JWT validation can be bypassed by setting alg=none. Critical finding.</p>"},
                        {"title": "IDOR on /users endpoint", "type": "note", "content": "<p>Changing user_id in request allows access to other users' data.</p>"},
                    ]},
                    {"title": "Portal XSS", "type": "note", "content": "<p>Stored XSS in profile bio field. Payload: <code>&lt;img src=x onerror=alert(1)&gt;</code></p>"},
                ],
            },
        ],
    },
    {
        "name": "Initech",
        "short_name": "INIT",
        "codename": "REDSTAPLER",
        "contacts": [
            ("Bill Lumbergh", "bill@initech.example.com", "VP", "555-0300"),
            ("Milton Waddams", "milton@initech.example.com", "Facilities", "555-0301"),
        ],
        "projects": [
            {
                "codename": "CRIMSON TIDE",
                "project_type": pt_redteam,
                "lead": "charlie",
                "operators": ["alice", "bob"],
                "start": date.today(),
                "end": date.today() + timedelta(days=30),
                "scopes": ["*.initech.example.com", "10.20.0.0/16", "Physical: HQ Building"],
                "targets": ["CEO Laptop", "Financial Database", "Badge System"],
                "notes_tree": [
                    {"title": "Planning", "type": "folder", "children": [
                        {"title": "Rules of Engagement", "type": "note", "content": "<p>No DoS. No production DB modification. Physical access authorized M-F 8am-6pm only.</p>"},
                        {"title": "C2 Infrastructure", "type": "note", "content": "<p>Cobalt Strike teamserver on AWS. Redirector chain: CloudFront → Nginx → TS.</p>"},
                    ]},
                    {"title": "Execution Log", "type": "folder", "children": []},
                ],
            },
        ],
    },
]

for cdata in clients_data:
    client, created = Client.objects.get_or_create(
        name=cdata["name"],
        defaults=dict(short_name=cdata["short_name"], codename=cdata["codename"]),
    )
    action = "Created" if created else "Exists"
    print(f"\n{action} client: {client.name}")

    for cname, cemail, ctitle, cphone in cdata["contacts"]:
        ClientContact.objects.get_or_create(
            client=client,
            email=cemail,
            defaults=dict(name=cname, job_title=ctitle, phone=cphone),
        )

    # Invite all users to the client
    for u in users.values():
        ClientInvite.objects.get_or_create(client=client, user=u)

    for pdata in cdata["projects"]:
        project, created = Project.objects.get_or_create(
            codename=pdata["codename"],
            defaults=dict(
                client=client,
                project_type=pdata["project_type"],
                start_date=pdata["start"],
                end_date=pdata["end"],
                complete=False,
            ),
        )
        action = "Created" if created else "Exists"
        print(f"  {action} project: {project.codename}")

        # Assignments
        lead_user = users[pdata["lead"]]
        ProjectAssignment.objects.get_or_create(
            project=project, operator=lead_user,
            defaults=dict(role=role_lead, start_date=pdata["start"], end_date=pdata["end"]),
        )
        for op_name in pdata["operators"]:
            op_user = users[op_name]
            ProjectAssignment.objects.get_or_create(
                project=project, operator=op_user,
                defaults=dict(role=role_operator, start_date=pdata["start"], end_date=pdata["end"]),
            )

        # Invite manager
        ProjectInvite.objects.get_or_create(project=project, user=users["manager"])

        # Scopes
        for i, scope_name in enumerate(pdata["scopes"]):
            ProjectScope.objects.get_or_create(
                project=project, name=scope_name,
                defaults=dict(scope=scope_name),
            )

        # Targets
        for i, target_name in enumerate(pdata["targets"]):
            ProjectTarget.objects.get_or_create(
                project=project, hostname=target_name,
            )

        # Collab notes tree
        def create_notes_tree(nodes, project, parent=None, pos_start=0):
            for i, node in enumerate(nodes):
                position = (pos_start + i) * 1000
                note, _ = ProjectCollabNote.objects.get_or_create(
                    project=project,
                    title=node["title"],
                    parent=parent,
                    defaults=dict(
                        node_type=node["type"],
                        content=node.get("content", ""),
                        position=position,
                    ),
                )
                if node["type"] == "note" and node.get("content"):
                    ProjectCollabNoteField.objects.get_or_create(
                        note=note,
                        position=0,
                        defaults=dict(
                            field_type="rich_text",
                            content=node["content"],
                        ),
                    )
                if "children" in node:
                    create_notes_tree(node["children"], project, parent=note)

        if created:
            create_notes_tree(pdata["notes_tree"], project)

print("\n" + "=" * 60)
print("SEED DATA COMPLETE")
print("=" * 60)
print(f"Users: {User.objects.count()} (login with TestPass123!)")
print(f"Clients: {Client.objects.count()}")
print(f"Projects: {Project.objects.count()}")
print(f"Collab Notes: {ProjectCollabNote.objects.count()}")
print(f"Collab Note Fields: {ProjectCollabNoteField.objects.count()}")
print("=" * 60)
