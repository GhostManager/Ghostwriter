"""This contains utilities and values used by the ``TemplateLinter`` class."""

# Example JSON reporting data for loading into templates for rendering tests
LINTER_CONTEXT = {
    "report_date": "March 25, 2021",
    "project": {
        "id": 1,
        "name": "2021-03-01 Kabletown, Inc. Red Team (KABLE-01)",
        "type": "Red Team",
        "start_date": "June 25, 2021",
        "start_month": "March",
        "start_day": 1,
        "start_year": 2021,
        "end_date": "June 25, 2021",
        "end_month": "June",
        "end_day": 25,
        "end_year": 2021,
        "codename": "KABLE-01",
        "note": "<p>This is an assessment for Kabletown but targets NBC assets. The goal is to answer specific questions prior to Kabletown absorbing NBC.</p>",
        "slack_channel": "#ghostwriter",
        "complete": False,
    },
    "client": {
        "id": 1,
        "contacts": [
            {
                "name": "Hank Hooper",
                "job_title": "CEO",
                "email": "dad@kabletown.family",
                "phone": "(212) 664-4444",
                "note": '<p>A self-described "family man," Vietnam veteran, and head of Kabletown. He always seems happy on the surface (laughing incessantly), while directing thinly-veiled insults and threats to subordinates. Handle with care.</p>',
            },
            {
                "name": "John Francis Donaghy",
                "job_title": "Vice President of East Coast Television",
                "email": "jack@nbc.com",
                "phone": "(212) 664-4444",
                "note": '<p>Prefers to go by "Jack."</p>',
            },
        ],
        "name": "Kabletown, Inc.",
        "short_name": "KTOWN",
        "codename": "Totally Not Comcast",
        "note": "<p>Philadelphia-based cable company Kabletown, a fictionalized depiction of the acquisition of NBC Universal by Comcast.</p>",
    },
    "team": [
        {
            "role": "Assessment Lead",
            "name": "Benny the Ghost",
            "email": "benny@ghostwriter.wiki",
            "start_date": "March 1, 2021",
            "end_date": "June 25, 2021",
            "note": "<p>Benny will lead the assessment for the full duration.</p>",
        },
        {
            "role": "Assessment Oversight",
            "name": "Christopher Maddalena",
            "email": "cmaddalena@specterops.io",
            "start_date": "March 1, 2021",
            "end_date": "June 25, 2021",
            "note": "<p>Christopher will provide oversight and assistance (as needed).</p>",
        },
    ],
    "objectives": [
        {
            "priority": "Primary",
            "status": "Active",
            "deadline": "June 25, 2021",
            "percent_complete": 50.0,
            "tasks": [
                {
                    "deadline": "June 25, 2021",
                    "marked_complete": "",
                    "task": "Extract information about Kenneth Parcell",
                    "complete": False,
                },
                {
                    "deadline": "June 4, 2021",
                    "marked_complete": "March 22, 2021",
                    "task": "Locate information about Kenneth Parcell to begin the search (Page Program subnet)",
                    "complete": True,
                },
            ],
            "objective": "Discover Kenneth Parcell's true identity",
            "description": '<p>It is unclear if this is a jest and part of an HR-related "flag" or a real request. The client was light on details. The objective is wide open; asking the team to find any and all information related to Kenneth Parcel, a member of NBC\'s Page Program.</p>',
            "complete": False,
            "marked_complete": "",
            "position": 1,
        },
        {
            "priority": "Secondary",
            "status": "Active",
            "deadline": "June 25, 2021",
            "percent_complete": 0.0,
            "tasks": [
                {
                    "deadline": "March 16, 2021",
                    "marked_complete": "",
                    "task": "Locate systems and data repositories used by HR and contract teams",
                    "complete": False,
                }
            ],
            "objective": "Access hosts and files containing celebrity PII",
            "description": "<p>The team may find methods of accessing data related to celebrities that appear on NBC programs. Use any discovered methods to access this information and capture evidence.</p>",
            "complete": False,
            "marked_complete": "",
            "position": 1,
        },
        {
            "priority": "Primary",
            "status": "Active",
            "deadline": "April 23, 2021",
            "percent_complete": 0.0,
            "tasks": [
                {
                    "deadline": "March 24, 2021",
                    "marked_complete": "",
                    "task": "Run BloodHound!",
                    "complete": False,
                }
            ],
            "objective": "Escalate privileges in the NBC domain to Domain Administrator or equivalent",
            "description": "<p>Active Directory is a key component of the assessment, and client is keen to learn how many attack paths may be discovered to escalate privileges within the network.</p>",
            "complete": False,
            "marked_complete": "",
            "position": 2,
        },
    ],
    "targets": [
        {
            "ip_address": "12.31.13.90",
            "hostname": "PP00001.NBC.LOCAL",
            "note": "<p>Computer known to be used by Kenneth Parcell. May contain celebrity PII (Parcell performs tasks for Tracy Morgan) or provide information for the Parcell objective.</p>",
            "compromised": False,
        }
    ],
    "scope": [
        {
            "total": 1,
            "scope": ["10.6.0.125"],
            "name": "Executive Computer",
            "description": "<p>This is Jack Donaghy's computer and should not be touched.</p>",
            "disallowed": True,
            "requires_caution": False,
        },
        {
            "total": 4,
            "scope": ["192.168.1.0/24", "10.100.0.0/16", "*.nbc.com", "NBC.LOCAL"],
            "name": "NBC Allowlist",
            "description": "<p>All hosts and domains in this list are allowed and related to core objectives.</p>",
            "disallowed": False,
            "requires_caution": False,
        },
        {
            "total": 1,
            "scope": ["12.31.13.0/24"],
            "name": "NBC Page Program",
            "description": "<p>Client advises caution while accessing this network and avoid detection. It is unclear why, but they have said it is related to the Kenneth Parcell objective.</p>",
            "disallowed": False,
            "requires_caution": True,
        },
    ],
    "infrastructure": {
        "domains": [
            {
                "activity": "Phishing",
                "domain": "getghostwriter.io",
                "start_date": "March 1, 2021",
                "end_date": "June 25, 2021",
                "dns": [
                    {
                        "static_server": "172.67.132.12",
                        "transient_server": "",
                        "endpoint": "sketchy-endpoint.azureedge.net",
                        "subdomain": "code",
                    }
                ],
                "note": "<p>Domain for the first phishing campaign</p>",
            },
            {
                "activity": "Command and Control",
                "domain": "ghostwriter.wiki",
                "start_date": "March 1, 2021",
                "end_date": "June 25, 2021",
                "dns": [
                    {
                        "static_server": "104.236.176.100",
                        "transient_server": "",
                        "endpoint": "",
                        "subdomain": "www",
                    }
                ],
                "note": "<p>Domain for long-haul C2 comms</p>",
            },
            {
                "activity": "Command and Control",
                "domain": "specterops.io",
                "start_date": "March 1, 2021",
                "end_date": "June 25, 2021",
                "dns": [
                    {
                        "static_server": "",
                        "transient_server": "30.49.38.30",
                        "endpoint": "",
                        "subdomain": "smtp",
                    }
                ],
                "note": "<p>Domain for the short-haul C2 comms (phishing)</p>",
            },
        ],
        "servers": [
            {
                "name": "CC-01",
                "ip_address": "104.236.176.100",
                "provider": "Digital Ocean",
                "activity": "Command and Control",
                "role": "Team Server / C2 Server",
                "start_date": "March 1, 2021",
                "end_date": "June 25, 2021",
                "dns": [
                    {"domain": "ghostwriter.wiki", "endpoint": "", "subdomain": "www"}
                ],
                "note": "<p>Long-haul C2 server</p>",
            },
            {
                "name": "CC-02",
                "ip_address": "172.67.132.12",
                "provider": "Microsoft Azure",
                "activity": "Command and Control",
                "role": "Team Server / C2 Server",
                "start_date": "March 1, 2021",
                "end_date": "June 25, 2021",
                "dns": [
                    {
                        "domain": "getghostwriter.io",
                        "endpoint": "sketchy-endpoint.azureedge.net",
                        "subdomain": "code",
                    }
                ],
                "note": "<p>Short-haul C2 server for phishing</p>",
            },
        ],
        "cloud": [
            {
                "activity": "Phishing",
                "role": "SMTP",
                "provider": "Amazon Web Services",
                "dns": [{"domain": "specterops.io", "endpoint": "", "subdomain": "smtp"}],
                "ip_address": "30.49.38.30",
                "name": "SMTP01",
                "note": "<p>SMTP server for phishing emails; running Gophish</p>",
            }
        ],
    },
    "findings": [
        {
            "assigned_to": "Benny the Ghost",
            "finding_type": "Network",
            "severity": "Critical",
            "severity_rt": "Critical",
            "severity_color": "966FD6",
            "severity_color_rgb": [150, 111, 214],
            "severity_color_hex": ["0x96", "0x6f", "0xd6"],
            "recommendation": "",
            "recommendation_rt": "",
            "evidence": [
                {
                    "id": 1,
                    "file_path": "evidence/2/ghost.png",
                    "url": "/media/evidence/2/ghost.png",
                    "document": "/media/evidence/2/ghost.png",
                    "friendly_name": "Ghostwriter",
                    "upload_date": "2021-03-22",
                    "caption": "Brief Caption for This Evidence",
                    "description": "",
                }
            ],
            "title": "Critical Network Finding",
            "position": 1,
            "affected_entities": "",
            "affected_entities_rt": "",
            "description": "",
            "description_rt": "",
            "impact": "",
            "impact_rt": "",
            "replication_steps": "",
            "replication_steps_rt": "",
            "host_detection_techniques": "",
            "host_detection_techniques_rt": "",
            "network_detection_techniques": "",
            "network_detection_techniques_rt": "",
            "references": "",
            "references_rt": "",
            "finding_guidance": "",
            "complete": False,
        },
    ],
    "docx_template": {
        "id": 1,
        "document": "/media/template_oxnfkmX.docx",
        "name": "Default Word Template",
        "doc_type": 1,
    },
    "pptx_template": {
        "id": 2,
        "document": "/media/app/ghostwriter/media/templates/template.pptx",
        "name": "Default PowerPoint Template",
        "doc_type": 2,
    },
    "company": {
        "name": "SpecterOps",
        "twitter": "@specterops",
        "email": "info@specterops.io",
    },
    "title": "Kabletown, Inc. Red Team (2021-03-01) Report",
    "complete": False,
    "archived": False,
    "delivered": False,
    "totals": {
        "objectives": 3,
        "objectives_completed": 0,
        "findings": 7,
        "scope": 6,
        "team": 2,
        "targets": 1,
    },
}
