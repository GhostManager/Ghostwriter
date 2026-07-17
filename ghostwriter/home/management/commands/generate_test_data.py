"""Seed a realistic local Ghostwriter demo database."""

# Standard Libraries
import json
import os
import shutil
from collections import Counter
from contextlib import contextmanager, nullcontext
from datetime import date, datetime, time, timedelta
from pathlib import Path

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db import transaction
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import (
    BloodHoundConfiguration,
    CompanyInformation,
    ExtraFieldModel,
    ExtraFieldSpec,
    ReportConfiguration,
)
from ghostwriter.home.models import UserProfile
from ghostwriter.oplog.models import Oplog, OplogEntry
from ghostwriter.reporting.models import (
    Evidence,
    Finding,
    FindingType,
    Observation,
    Report,
    ReportFindingLink,
    ReportObservationLink,
    Severity,
)
from ghostwriter.rolodex.models import (
    Client,
    ClientContact,
    Deconfliction,
    DeconflictionStatus,
    ObjectivePriority,
    ObjectiveStatus,
    Project,
    ProjectAssignment,
    ProjectContact,
    ProjectObjective,
    ProjectRole,
    ProjectScope,
    ProjectSubTask,
    ProjectTarget,
    ProjectType,
    WhiteCard,
)
from ghostwriter.shepherd.models import (
    ActivityType,
    Domain,
    DomainServerConnection,
    DomainStatus,
    HealthStatus,
    History,
    ServerHistory,
    ServerProvider,
    ServerRole,
    ServerStatus,
    StaticServer,
    TransientServer,
    WhoisStatus,
)

DEMO_MARKER_KEY = "demo_seed"
DEMO_MARKER_VALUE = "ghostbusters"
DEMO_PASSWORD = "SuperNaturalReporting!"
DEMO_BLOODHOUND_RESULTS_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "demo_bloodhound_results.json"
)
DEFAULT_TEMPLATE_DIR = (
    Path(__file__).resolve().parents[3] / "reporting" / "templates" / "reports"
)
DEFAULT_TEMPLATE_FILENAMES = ("template.docx", "template.pptx")
DEMO_EVIDENCE_DIR = Path(__file__).resolve().parents[4] / "DOCS" / "example-data"
DEMO_EVIDENCE_TEXT_SAMPLES = [
    {
        "path": DEMO_EVIDENCE_DIR / "evidence_nmap_portal_gbi.txt",
        "friendly_name": "Nmap Service Scan - portal.gbi.example",
        "caption": "Nmap service detection for portal.gbi.example (10.40.20.20).",
        "description": "Sanitized Nmap output captured while validating the approved GBI customer portal target.",
        "tags": ["nmap", "network", "service-enumeration"],
    },
    {
        "path": DEMO_EVIDENCE_DIR / "evidence_burp_portal_gbi_response.txt",
        "friendly_name": "Burp Response - GBI Profile Notes",
        "caption": "Burp Proxy capture showing an unencoded stored note in the GBI portal response.",
        "description": "Sanitized HTTP request and response retained during validation of stored cross-site scripting behavior.",
        "tags": ["burp", "http", "web-application"],
    },
    {
        "path": DEMO_EVIDENCE_DIR / "evidence_rubeus_asktgs.txt",
        "friendly_name": "Rubeus Ticket Request - GBI.LOCAL",
        "caption": "Sanitized Rubeus service-ticket and Kerberoast output from GBI.LOCAL.",
        "description": "Sanitized command output captured while validating service-account exposure in the GBI domain.",
        "tags": ["rubeus", "kerberos", "credential-access"],
    },
]
INITIAL_FIXTURES = [
    "ghostwriter/commandcenter/fixtures/initial.json",
    "ghostwriter/reporting/fixtures/initial.json",
    "ghostwriter/rolodex/fixtures/initial.json",
    "ghostwriter/shepherd/fixtures/initial.json",
]

COMPANY_INFORMATION = {
    "company_name": "SpecterOps",
    "company_short_name": "SO",
    "company_address": "14 N Moore St, New York, NY 10013",
    "company_twitter": "@specterops",
    "company_email": "info@specterops.io",
}

REPORT_CONFIGURATION = {
    "enable_borders": True,
    "border_weight": 12700,
    "border_color": "2D2B6B",
    "prefix_figure": " \u2013 ",
    "label_figure": "Figure ",
    "figure_caption_location": "bottom",
    "evidence_image_alignment": "CENTER",
    "evidence_image_width": 6.5,
    "prefix_table": " \u2013 ",
    "label_table": "Table",
    "table_caption_location": "top",
    "report_filename": '{{now|format_datetime("Y-m-d_His")}} {{company.name}} - {{client.name}} {{project.type}} Report',
    "project_filename": '{{now|format_datetime("Y-m-d_His")}} {{company.name}} - {{client.name}} {{project.type}} Report',
    "title_case_captions": True,
    "title_case_exceptions": "a,as,at,an,and,of,the,is,to,by,for,in,on,but,or",
    "target_delivery_date": 5,
    "default_cvss_version": "4.0",
    "outline_tags": "report,evidence,cred*,detect*",
    "default_docx_template": None,
    "default_pptx_template": None,
}

EXTRA_FIELD_MODELS = [
    Client,
    Project,
    Domain,
    StaticServer,
    Finding,
    Report,
    ReportFindingLink,
    Observation,
    ReportObservationLink,
    OplogEntry,
]

EXTRA_FIELD_SPECS = [
    {
        "internal_name": "workflow_metadata",
        "display_name": "Workflow Metadata",
        "description": "Structured metadata used by internal review and delivery workflows.",
        "type": "json",
        "user_default_value": '{"classification": "internal", "status": "active"}',
        "seed_value": {"classification": "internal", "status": "active"},
    },
    {
        "internal_name": "tracking_reference",
        "display_name": "Tracking Reference",
        "description": "Internal reference used to correlate the record with supporting workflows.",
        "type": "single_line_text",
        "user_default_value": "OPS-001",
        "seed_value": "OPS-{label}",
    },
    {
        "internal_name": "reviewed",
        "display_name": "Reviewed",
        "description": "Indicates the record has completed an internal review.",
        "type": "checkbox",
        "user_default_value": "",
        "seed_value": True,
    },
    {
        "internal_name": "confidence_score",
        "display_name": "Confidence Score",
        "description": "Analyst confidence in the accuracy of the recorded information.",
        "type": "float",
        "user_default_value": "8.0",
        "seed_value": 8.5,
    },
    {
        "internal_name": "review_round",
        "display_name": "Review Round",
        "description": "Current round of internal review for this record.",
        "type": "integer",
        "user_default_value": "1",
        "seed_value": 1,
    },
    {
        "internal_name": "analyst_notes",
        "display_name": "Analyst Notes",
        "description": "Internal context and review notes for this record.",
        "type": "rich_text",
        "user_default_value": "",
        "seed_value": "<p>{label} has been reviewed and is ready for the next workflow stage.</p>",
    },
]

PROJECT_EXTRA_FIELD_SPECS = [
    {
        "internal_name": "assessment_parameters",
        "display_name": "Assessment Parameters",
        "description": "Structured parameters used by assessment and reporting workflows.",
        "type": "json",
        "user_default_value": '{"methodology": "threat-informed", "reporting_cadence": "weekly"}',
        "seed_value": {
            "methodology": "threat-informed",
            "reporting_cadence": "weekly",
        },
    },
    {
        "internal_name": "entity_tested",
        "display_name": "Entity Tested",
        "description": "Business unit, environment, application, or organization being tested.",
        "type": "single_line_text",
        "user_default_value": "",
        "seed_value": "Enterprise identity and external attack surface",
    },
    {
        "internal_name": "include_cvss",
        "display_name": "Include CVSS",
        "description": "Include CVSS scores and vectors in generated reports for this project.",
        "type": "checkbox",
        "user_default_value": "",
        "seed_value": True,
    },
    {
        "internal_name": "estimated_coverage",
        "display_name": "Estimated Coverage",
        "description": "Estimated percentage of the approved scope covered by testing.",
        "type": "float",
        "user_default_value": "80",
        "seed_value": 85.0,
    },
    {
        "internal_name": "retest_round",
        "display_name": "Retest Round",
        "description": "Current remediation retest cycle for the project.",
        "type": "integer",
        "user_default_value": "0",
        "seed_value": 1,
    },
    {
        "internal_name": "testing_notes",
        "display_name": "Testing Notes",
        "description": "Engagement-specific context for operators and report authors.",
        "type": "rich_text",
        "user_default_value": "",
        "seed_value": "<p>Testing prioritizes identity controls, remote access paths, and the approved external attack surface.</p>",
    },
]

REPORT_EXTRA_FIELD_SPECS = [
    {
        "internal_name": "delivery_metadata",
        "display_name": "Delivery Metadata",
        "description": "Structured information used by report delivery workflows.",
        "type": "json",
        "user_default_value": '{"classification": "confidential", "delivery": "secure portal"}',
        "seed_value": {
            "classification": "confidential",
            "delivery": "secure portal",
        },
    },
    {
        "internal_name": "report_version",
        "display_name": "Report Version",
        "description": "Human-readable version included in the report review workflow.",
        "type": "single_line_text",
        "user_default_value": "1.0",
        "seed_value": "1.0",
    },
    {
        "internal_name": "reviewed",
        "display_name": "Reviewed",
        "description": "Indicates the report has completed an internal quality review.",
        "type": "checkbox",
        "user_default_value": "",
        "seed_value": True,
    },
    {
        "internal_name": "quality_score",
        "display_name": "Quality Score",
        "description": "Internal quality score recorded during report review.",
        "type": "float",
        "user_default_value": "8.0",
        "seed_value": 9.0,
    },
    {
        "internal_name": "revision_number",
        "display_name": "Revision Number",
        "description": "Current internal revision number for the report.",
        "type": "integer",
        "user_default_value": "1",
        "seed_value": 1,
    },
    {
        "internal_name": "attack_path_narrative",
        "display_name": "Attack Path Narrative",
        "description": "Narrative connecting individual findings into the demonstrated attack path.",
        "type": "rich_text",
        "user_default_value": "",
        "seed_value": "<p>The team combined valid remote access, identity reconnaissance, and delegated privileges to demonstrate a path to sensitive systems without disrupting production services.</p>",
    },
    {
        "internal_name": "executive_summary",
        "display_name": "Executive Summary",
        "description": "Executive-level summary of assessment outcomes, business impact, and priorities.",
        "type": "rich_text",
        "user_default_value": "",
        "seed_value": "<p>The assessment identified opportunities to strengthen identity assurance, privileged access, and monitoring while confirming several existing controls operated as intended.</p>",
    },
]

EXTRA_FIELD_SPECS_BY_MODEL = {
    Project: PROJECT_EXTRA_FIELD_SPECS,
    Report: REPORT_EXTRA_FIELD_SPECS,
}

USERS = [
    {
        "username": "cmaddalena",
        "name": "Christopher Maddalena",
        "email": "cmaddalena@getghostwriter.io",
        "phone": "+1 202 555 0101",
        "role": "admin",
        "timezone": "America/Los_Angeles",
    },
    {
        "username": "pstanz",
        "name": "Peter Venkman",
        "email": "pvenkman@ghostbusters.example",
        "phone": "+1 212 555 0102",
        "role": "manager",
        "timezone": "America/New_York",
    },
    {
        "username": "rstantz",
        "name": "Ray Stantz",
        "email": "rstantz@ghostbusters.example",
        "phone": "+1 212 555 0103",
        "role": "user",
        "timezone": "America/New_York",
        "enable_finding_create": True,
        "enable_finding_edit": True,
    },
    {
        "username": "espengler",
        "name": "Egon Spengler",
        "email": "espengler@ghostbusters.example",
        "phone": "+1 212 555 0104",
        "role": "user",
        "timezone": "America/New_York",
        "enable_finding_create": True,
        "enable_observation_create": True,
    },
    {
        "username": "wzeddemore",
        "name": "Winston Zeddemore",
        "email": "wzeddemore@ghostbusters.example",
        "phone": "+1 212 555 0105",
        "role": "user",
        "timezone": "America/New_York",
    },
    {
        "username": "jmelnitz",
        "name": "Janine Melnitz",
        "email": "jmelnitz@ghostbusters.example",
        "phone": "+1 212 555 0106",
        "role": "manager",
        "timezone": "America/New_York",
    },
]

CLIENTS = [
    {
        "name": "Ghostbusters International",
        "short_name": "GBI",
        "codename": "FIREHOUSE",
        "timezone": "America/New_York",
        "address": "14 North Moore Street\nNew York, NY 10013",
        "description": "<p>Global incident response and containment provider preparing for a coordinated adversary emulation exercise.</p>",
        "contacts": [
            (
                "Dana Barrett",
                "Chief Risk Officer",
                "dana.barrett@gbi.example",
                "+1 212 555 0180",
                True,
            ),
            (
                "Louis Tully",
                "Director of Compliance",
                "louis.tully@gbi.example",
                "+1 212 555 0181",
                False,
            ),
            (
                "Walter Peck",
                "Regulatory Liaison",
                "walter.peck@gbi.example",
                "+1 212 555 0182",
                False,
            ),
        ],
        "projects": [
            {
                "codename": "ECTO-SHIELD",
                "schedule": "current",
                "type": "Red Team",
                "description": "<p>Enterprise red team engagement focused on identity abuse, remote access paths, and executive reporting workflows.</p>",
                "slack": "#ecto-shield",
                "complete": False,
                "objectives": [
                    "Validate external exposure and identify initial access paths",
                    "Assess Active Directory privilege escalation opportunities",
                    "Exercise detection and response handoffs with the blue team",
                ],
                "scope": [
                    "vpn.gbi.example",
                    "mail.gbi.example",
                    "10.40.10.0/24",
                    "10.40.20.0/24",
                ],
                "targets": [
                    (
                        "10.40.10.12",
                        "dc01.gbi.local",
                        "Primary domain controller",
                        True,
                    ),
                    ("10.40.10.35", "fs01.gbi.local", "Finance file server", False),
                    ("10.40.20.20", "portal.gbi.example", "Customer portal", False),
                ],
            },
            {
                "codename": "PROTON-DRILL",
                "schedule": "past",
                "type": "Red Team",
                "description": "<p>Collaborative validation of endpoint detections for credential access and lateral movement.</p>",
                "slack": "#proton-drill",
                "complete": True,
                "objectives": [
                    "Replay credential access techniques in a monitored lab segment",
                    "Document detection gaps and tuning recommendations",
                    "Produce a prioritized remediation plan",
                ],
                "scope": ["10.41.30.0/24", "edr-lab.gbi.local"],
                "targets": [
                    (
                        "10.41.30.14",
                        "lab-wks-014.gbi.local",
                        "Workstation with EDR test policy",
                        True,
                    ),
                    (
                        "10.41.30.40",
                        "lab-srv-040.gbi.local",
                        "Application server",
                        False,
                    ),
                ],
            },
        ],
    },
    {
        "name": "Stay Puft Holdings",
        "short_name": "Stay Puft",
        "codename": "MARSHMALLOW",
        "timezone": "America/Chicago",
        "address": "100 Sugary Way\nChicago, IL 60601",
        "description": "<p>Consumer goods company requesting a realistic external and cloud security assessment ahead of a new product launch.</p>",
        "contacts": [
            (
                "Ivo Shandor",
                "VP of Technology",
                "ivo.shandor@staypuft.example",
                "+1 312 555 0110",
                True,
            ),
            (
                "Gozer Gozerian",
                "Cloud Platform Owner",
                "gozer@staypuft.example",
                "+1 312 555 0111",
                False,
            ),
            (
                "Zuul Vinz",
                "Security Operations Manager",
                "zuul.vinz@staypuft.example",
                "+1 312 555 0112",
                False,
            ),
        ],
        "projects": [
            {
                "codename": "PINK-SLIP",
                "schedule": "future",
                "type": "Penetration Test",
                "description": "<p>External network and web application assessment for the public ecommerce and partner access perimeter.</p>",
                "slack": "#pink-slip",
                "complete": False,
                "objectives": [
                    "Enumerate public attack surface and prioritize exploitable services",
                    "Assess partner portal authentication and session controls",
                    "Deliver actionable remediation evidence for launch readiness",
                ],
                "scope": [
                    "www.staypuft.example",
                    "partners.staypuft.example",
                    "198.51.100.0/28",
                ],
                "targets": [
                    ("198.51.100.24", "www.staypuft.example", "Marketing site", False),
                    (
                        "198.51.100.31",
                        "partners.staypuft.example",
                        "Partner portal",
                        True,
                    ),
                    (
                        "198.51.100.40",
                        "vpn.staypuft.example",
                        "Remote access gateway",
                        False,
                    ),
                ],
            },
            {
                "codename": "GOZER-GATE",
                "schedule": "past",
                "type": "Penetration Test",
                "description": "<p>Completed assessment of the manufacturing network and vendor remote-access boundary following an identity modernization project.</p>",
                "slack": "#gozer-gate",
                "complete": True,
                "objectives": [
                    "Validate segmentation between corporate and manufacturing systems",
                    "Review vendor remote-access controls and privileged account handling",
                    "Confirm remediation of previously identified perimeter exposures",
                ],
                "scope": [
                    "plant.staypuft.example",
                    "vendors.staypuft.example",
                    "10.62.40.0/24",
                ],
                "targets": [
                    (
                        "10.62.40.10",
                        "ops-jump.staypuft.local",
                        "Manufacturing operations jump host",
                        True,
                    ),
                    (
                        "10.62.40.25",
                        "batch.staypuft.local",
                        "Production scheduling server",
                        False,
                    ),
                    (
                        "198.51.100.61",
                        "vendors.staypuft.example",
                        "Vendor access gateway",
                        False,
                    ),
                ],
            },
        ],
    },
    {
        "name": "Spectral Research Labs",
        "short_name": "SRL",
        "codename": "TOBIN",
        "timezone": "America/Denver",
        "address": "550 Occult Reference Road\nBoulder, CO 80301",
        "description": "<p>Research organization with a mixed cloud and lab environment used for threat emulation development.</p>",
        "contacts": [
            (
                "Jillian Holtzmann",
                "Principal Engineer",
                "jillian.holtzmann@srl.example",
                "+1 720 555 0170",
                True,
            ),
            (
                "Erin Gilbert",
                "Program Sponsor",
                "erin.gilbert@srl.example",
                "+1 720 555 0171",
                False,
            ),
            (
                "Abby Yates",
                "Security Architect",
                "abby.yates@srl.example",
                "+1 720 555 0172",
                False,
            ),
        ],
        "projects": [
            {
                "codename": "PKE-METER",
                "schedule": "current",
                "type": "Red Team",
                "description": "<p>Threat-informed emulation mapped to likely intrusion paths against the research enclave.</p>",
                "slack": "#pke-meter",
                "complete": False,
                "objectives": [
                    "Simulate initial access through developer SaaS and VPN workflows",
                    "Evaluate cloud control-plane permissions and logging",
                    "Confirm report evidence supports executive and technical audiences",
                ],
                "scope": [
                    "research.srl.example",
                    "10.55.0.0/22",
                    "srl-lab.azure.example",
                ],
                "targets": [
                    ("10.55.1.20", "gitlab.srl.local", "Source control server", False),
                    (
                        "10.55.2.44",
                        "jump01.srl.local",
                        "Administrative jump host",
                        True,
                    ),
                    ("10.55.3.10", "sql01.srl.local", "Research database", False),
                ],
            },
            {
                "codename": "SLIME-LINE",
                "schedule": "future",
                "type": "Red Team",
                "description": "<p>Planned adversary simulation covering research partner access, cloud identity, and protected build infrastructure.</p>",
                "slack": "#slime-line",
                "complete": False,
                "objectives": [
                    "Evaluate research partner identity federation and access boundaries",
                    "Test detection coverage for cloud privilege escalation workflows",
                    "Exercise incident coordination for compromise of build infrastructure",
                ],
                "scope": [
                    "partners.srl.example",
                    "build.srl.example",
                    "10.56.0.0/23",
                ],
                "targets": [
                    (
                        "10.56.0.18",
                        "build01.srl.local",
                        "Protected build coordinator",
                        False,
                    ),
                    (
                        "10.56.0.42",
                        "idp-proxy.srl.local",
                        "Partner identity proxy",
                        False,
                    ),
                    (
                        "10.56.1.12",
                        "artifact.srl.local",
                        "Research artifact repository",
                        False,
                    ),
                ],
            },
        ],
    },
]

DOMAINS = [
    ("ghostwriter.wiki", "Namecheap", "Reserved", "Healthy", "Enabled"),
    ("getghostwriter.io", "Hover", "Reserved", "Healthy", "Enabled"),
    ("specterops.io", "Gandi", "Reserved", "Healthy", "Enabled"),
    ("docs.mythic-c2.net", "Cloudflare", "Reserved", "Healthy", "Enabled"),
    ("ecto-analytics.com", "Namecheap", "Available", "Questionable", "Enabled"),
    ("containment-review.net", "Dynadot", "Available", "Healthy", "Enabled"),
    ("partner-validation.io", "Porkbun", "Reserved", "Healthy", "Enabled"),
    ("research-gateway.cloud", "Cloudflare", "Available", "Questionable", "Enabled"),
]

STATIC_SERVERS = [
    ("203.0.113.10", "ecto-rdr-01", "Amazon Web Services", "Reserved"),
    ("203.0.113.11", "ecto-c2-01", "Digital Ocean", "Reserved"),
    ("198.51.100.52", "puft-web-redirector", "Microsoft Azure", "Reserved"),
    ("192.0.2.33", "spectral-payloads", "Linode", "Available"),
]

FINDINGS = [
    {
        "title": "Weak Multi-Factor Authentication Enforcement on Remote Access",
        "severity": "High",
        "type": "Network",
        "cvss_score": 8.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N",
        "tags": ["identity", "remote-access", "mfa"],
        "description": "<p>Remote access workflows allowed authenticated users to reach sensitive applications without a consistent step-up challenge.</p>",
        "impact": "<p>An attacker with valid credentials could access internal services from an untrusted network and bypass expected identity assurance controls.</p>",
        "mitigation": "<p>Require phishing-resistant MFA for all remote access paths, enforce conditional access policies, and alert on legacy authentication attempts.</p>",
        "replication_steps": "<ol><li>Authenticate to the VPN portal with a test user.</li><li>Observe that access is granted without a second factor.</li><li>Browse to internal applications using the established session.</li></ol>",
        "host_detection_techniques": "<p>Review identity provider sign-in logs for remote sessions missing an MFA claim.</p>",
        "network_detection_techniques": "<p>Alert when VPN sessions originate from new geographies or unmanaged devices without an MFA event.</p>",
        "references": "<p>https://attack.mitre.org/techniques/T1078/</p>",
        "finding_guidance": "<p>Use this finding when the engagement demonstrates access from valid credentials without adequate second-factor enforcement.</p>",
    },
    {
        "title": "Kerberoastable Service Accounts with Excessive Privileges",
        "severity": "High",
        "type": "Host",
        "cvss_score": 8.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        "tags": ["active-directory", "kerberos", "credential-access"],
        "description": "<p>Several service accounts exposed service principal names and held privileges beyond their operational requirements.</p>",
        "impact": "<p>Offline password cracking could lead to privileged domain access and lateral movement across critical systems.</p>",
        "mitigation": "<p>Rotate service account passwords to long random values, move services to managed service accounts, and remove unnecessary group membership.</p>",
        "replication_steps": "<ol><li>Request Kerberos service tickets for SPN-enabled accounts.</li><li>Export the ticket material.</li><li>Attempt offline cracking with approved engagement tooling.</li></ol>",
        "host_detection_techniques": "<p>Monitor domain controllers for unusual TGS request volumes and service ticket requests from workstations.</p>",
        "network_detection_techniques": "<p>Correlate Kerberos ticket activity with systems that do not normally perform service account administration.</p>",
        "references": "<p>https://attack.mitre.org/techniques/T1558/003/</p>",
        "finding_guidance": "<p>Include cracked password evidence only in the restricted appendix or evidence vault.</p>",
    },
    {
        "title": "Over-Permissive Cloud Storage Bucket Policy",
        "severity": "Medium",
        "type": "Cloud",
        "cvss_score": 6.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "tags": ["cloud", "storage", "data-exposure"],
        "description": "<p>A cloud storage bucket allowed broad read access to internal artifacts that were not intended for public distribution.</p>",
        "impact": "<p>Sensitive build outputs, configuration files, or customer data could be accessed by unauthorized users.</p>",
        "mitigation": "<p>Restrict bucket policies to explicit principals, enable public access blocks, and add continuous monitoring for policy drift.</p>",
        "replication_steps": "<ol><li>Enumerate the bucket URL from public application responses.</li><li>Request object listings or known object paths without credentials.</li><li>Confirm access to non-public artifacts.</li></ol>",
        "host_detection_techniques": "<p>Review cloud audit logs for anonymous or cross-account object access.</p>",
        "network_detection_techniques": "<p>Inspect CDN and object storage logs for access patterns from unexpected autonomous systems.</p>",
        "references": "<p>https://attack.mitre.org/techniques/T1530/</p>",
        "finding_guidance": "<p>Capture only benign proof files unless the client approves controlled access to sensitive objects.</p>",
    },
    {
        "title": "Stored Cross-Site Scripting in Partner Portal Notes",
        "severity": "Medium",
        "type": "Web",
        "cvss_score": 6.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N",
        "tags": ["web", "xss", "partner-portal"],
        "description": "<p>The partner portal rendered user-controlled notes without sufficient output encoding.</p>",
        "impact": "<p>An attacker could execute JavaScript in another user's browser and perform actions in that user's session.</p>",
        "mitigation": "<p>Apply context-aware output encoding, sanitize rich text input, and add regression tests for stored user content.</p>",
        "replication_steps": "<ol><li>Create a partner note containing a harmless script payload.</li><li>Open the account details as another user.</li><li>Observe script execution in the browser context.</li></ol>",
        "host_detection_techniques": "<p>Review application logs for suspicious HTML or script tags in note fields.</p>",
        "network_detection_techniques": "<p>Monitor browser telemetry and proxy logs for unexpected callbacks from portal pages.</p>",
        "references": "<p>https://owasp.org/www-community/attacks/xss/</p>",
        "finding_guidance": "<p>Use a non-destructive payload such as a visible marker or console message in demo evidence.</p>",
    },
    {
        "title": "Insufficient EDR Alerting for Credential Dumping Simulation",
        "severity": "Low",
        "type": "Host",
        "cvss_score": 3.7,
        "cvss_vector": "CVSS:3.1/AV:L/AC:H/PR:H/UI:N/S:U/C:L/I:N/A:N",
        "tags": ["detection", "edr", "credential-access"],
        "description": "<p>Credential access simulation generated limited endpoint telemetry and did not produce a high-confidence alert.</p>",
        "impact": "<p>Operators may have a longer dwell time before defenders identify credential theft behavior.</p>",
        "mitigation": "<p>Tune endpoint detections for LSASS access, suspicious handle requests, and post-exploitation tooling patterns.</p>",
        "replication_steps": "<ol><li>Execute the approved credential access simulator on a monitored test host.</li><li>Collect endpoint and SIEM telemetry.</li><li>Compare observed alerts to the expected detection catalog.</li></ol>",
        "host_detection_techniques": "<p>Alert on non-standard processes requesting sensitive process handles or dumping protected memory.</p>",
        "network_detection_techniques": "<p>Correlate endpoint activity with outbound staging or command-and-control sessions.</p>",
        "references": "<p>https://attack.mitre.org/techniques/T1003/</p>",
        "finding_guidance": "<p>This finding is useful in purple team reports where the primary issue is detection coverage.</p>",
    },
]

OBSERVATIONS = [
    {
        "title": "Effective Security Team Coordination During Testing",
        "description": (
            "<p>The client security team maintained clear escalation paths, provided timely deconfliction, "
            "and used Ghostwriter evidence to track defensive observations during the engagement.</p>"
        ),
        "tags": ["positive", "process", "purple-team"],
    },
    {
        "title": "Centralized Logging Improved Investigation Speed",
        "description": (
            "<p>Authentication, endpoint, and network telemetry were available in a central platform, "
            "which reduced the time required to validate simulated adversary activity.</p>"
        ),
        "tags": ["positive", "logging", "detection"],
    },
]

OPLOG_STEPS = [
    (
        "nmap",
        "nmap -Pn -sV {target}",
        "Enumerated exposed services for the scoped host.",
        ["att&ck:T1046", "discovery"],
    ),
    (
        "httpx",
        "httpx -title -tech-detect -u https://{host}",
        "Captured web technology and title information.",
        ["att&ck:T1595", "discovery"],
    ),
    (
        "Mythic",
        "jobs",
        "Reviewed active agent jobs and task status.",
        ["att&ck:T1071", "detection"],
    ),
    (
        "SharpHound",
        "Invoke-BloodHound -CollectionMethod Session,Trusts,ACL",
        "Collected Active Directory relationship data.",
        ["att&ck:T1482", "discovery"],
    ),
    (
        "Rubeus",
        "Rubeus.exe kerberoast /nowrap",
        "Requested service tickets for approved Kerberoast validation.",
        ["att&ck:T1558", "creds"],
    ),
    (
        "PowerView",
        "Get-DomainGroupMember 'Domain Admins'",
        "Enumerated privileged group membership.",
        ["att&ck:T1069", "discovery"],
    ),
    (
        "curl",
        "curl -I https://{host}",
        "Validated redirect and response headers.",
        ["att&ck:T1071", "detection"],
    ),
    (
        "Manual Validation",
        "Reviewed captured evidence against reporting criteria.",
        "Correlated validated evidence with report findings and noted detection coverage.",
        ["detection"],
    ),
]


class Command(BaseCommand):
    help = "Seed a realistic Ghostwriter demo database for local testing, demos, and videos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="In append mode, remove prior demo seed data before seeding.",
        )
        parser.add_argument(
            "--append",
            action="store_true",
            help="Append or update demo seed data without wiping the database or reloading fixtures.",
        )
        parser.add_argument(
            "--quick",
            action="store_true",
            help="Create a smaller but complete demo dataset.",
        )
        parser.add_argument(
            "--clients",
            type=int,
            default=None,
            help="Number of demo clients to create.",
        )
        parser.add_argument(
            "--projects-per-client",
            type=int,
            default=None,
            help="Maximum number of projects to create for each selected client.",
        )

    def handle(self, *args, **options):
        self.append_mode = options["append"]
        self.stats = Counter()
        if options["reset"] and not self.append_mode:
            self.stdout.write(
                self.style.WARNING(
                    "--reset is only needed with --append; performing the default "
                    "full database and media rebuild."
                )
            )
        client_limit = self._bounded_count(
            options["clients"], 1 if options["quick"] else len(CLIENTS), 1, len(CLIENTS)
        )
        project_limit = self._bounded_count(
            options["projects_per_client"], 1 if options["quick"] else 10, 1, 10
        )

        trigger_context = (
            self._disabled_evidence_user_triggers()
            if not self._evidence_has_finding_column()
            else nullcontext()
        )

        try:
            if not options["append"]:
                self._reinstall_database()

            with trigger_context:
                with transaction.atomic():
                    if options["reset"] and self.append_mode:
                        self._reset_demo_data()

                    self._seed_extra_field_specs()
                    lookups = self._load_lookups()
                    users = self._seed_users()
                    domains = self._seed_domains(lookups, users)
                    servers = self._seed_static_servers(lookups, users)
                    findings = self._seed_findings(lookups)
                    observations = self._seed_observations()
                    clients, projects = self._seed_clients_and_projects(
                        lookups=lookups,
                        users=users,
                        domains=domains,
                        servers=servers,
                        findings=findings,
                        observations=observations,
                        client_limit=client_limit,
                        project_limit=project_limit,
                    )
                    self._assign_install_admin_to_active_project(lookups)
        except Exception as exc:
            raise CommandError(f"Demo data seed failed: {exc}") from exc

        self._print_summary(clients, projects)

    def _bounded_count(self, requested, default, minimum, maximum):
        value = default if requested is None else requested
        if value < minimum or value > maximum:
            raise CommandError(
                f"Requested count {value} is outside the supported range {minimum}-{maximum}."
            )
        return value

    def _demo_extra(self, model=None, label="", **extra):
        data = {
            DEMO_MARKER_KEY: DEMO_MARKER_VALUE,
        }
        specs = EXTRA_FIELD_SPECS_BY_MODEL.get(model, EXTRA_FIELD_SPECS)
        for spec in specs:
            value = spec["seed_value"]
            if isinstance(value, str):
                value = value.format(label=label)
            data[spec["internal_name"]] = value
        data.update(extra)
        return data

    def _reinstall_database(self):
        self._validate_media_reset()
        self._reset_media()
        call_command("flush", interactive=False, verbosity=0)
        self.stats["flushed"] += 1
        for fixture in INITIAL_FIXTURES:
            call_command("loaddata", fixture, force=True, verbosity=0)
            self.stats["fixtures"] += 1
        self._configure_install_admin()
        self._configure_company_information()
        self._configure_report_configuration()
        self._configure_bloodhound_configuration()

    def _media_root(self):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        if media_root == Path(media_root.anchor):
            raise CommandError(f"Refusing to clear unsafe MEDIA_ROOT: {media_root}")
        return media_root

    def _validate_media_reset(self):
        media_root = self._media_root()
        for filename in DEFAULT_TEMPLATE_FILENAMES:
            source = DEFAULT_TEMPLATE_DIR / filename
            if not source.is_file():
                raise CommandError(f"Default report template is missing: {source}")
        for sample in DEMO_EVIDENCE_TEXT_SAMPLES:
            if not sample["path"].is_file():
                raise CommandError(f"Demo evidence sample is missing: {sample['path']}")

        if media_root.exists() and not media_root.is_dir():
            raise CommandError(f"MEDIA_ROOT is not a directory: {media_root}")
        media_root.mkdir(parents=True, exist_ok=True)
        probe = media_root / ".ghostwriter-demo-reset-check"
        try:
            probe.touch(exist_ok=False)
            probe.unlink()
        except OSError as exc:
            raise CommandError(
                f"MEDIA_ROOT is not writable and cannot be reset: {media_root}: {exc}"
            ) from exc

    def _reset_media(self):
        media_root = self._media_root()
        child = media_root
        try:
            for child in media_root.iterdir():
                if child.is_symlink() or not child.is_dir():
                    child.unlink()
                else:
                    shutil.rmtree(child)
        except OSError as exc:
            raise CommandError(
                f"Could not clear media entry {child} under {media_root}: {exc}"
            ) from exc

        template_dir = media_root / "templates"
        template_dir.mkdir()
        for filename in DEFAULT_TEMPLATE_FILENAMES:
            source = DEFAULT_TEMPLATE_DIR / filename
            shutil.copy2(source, template_dir / filename)

    def _env_value(self, *names, default=""):
        for name in names:
            value = os.environ.get(name)
            if value:
                return value
        return default

    def _install_admin_username(self):
        return self._env_value("DJANGO_SUPERUSER_USERNAME", default="admin")

    def _get_install_admin(self):
        try:
            return get_user_model().objects.get(username=self._install_admin_username())
        except get_user_model().DoesNotExist:
            return None

    def _configure_install_admin(self):
        User = get_user_model()
        username = self._install_admin_username()
        email = self._env_value(
            "DJANGO_SUPERUSER_EMAIL", default="admin@ghostwriter.local"
        )
        password = self._env_value(
            "DJANGO_SUPERUSER_PASSWORD", "ADMIN_PASSWORD", default=DEMO_PASSWORD
        )
        admin, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "name": "Ghostwriter Administrator",
                "role": "admin",
                "is_active": True,
            },
        )
        if created:
            self.stats["created"] += 1
        else:
            self._update_object(
                admin,
                {
                    "email": email,
                    "role": "admin",
                    "is_active": True,
                    "require_mfa": False,
                },
            )
        admin.set_password(password)
        admin.save()
        self._ensure_user_profile(admin)

    def _ensure_user_profile(self, user):
        _, created = UserProfile.objects.get_or_create(user=user)
        if created:
            self.stats["created"] += 1

    def _assign_install_admin_to_active_project(self, lookups):
        admin = self._get_install_admin()
        if admin is None:
            return

        today = date.today()
        projects = Project.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
            complete=False,
            extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE},
        ).order_by("start_date", "codename")
        for project in projects:
            assignment, created = ProjectAssignment.objects.get_or_create(
                project=project,
                operator=admin,
                defaults={
                    "role": lookups["project_roles"]["Assessment Oversight"],
                    "start_date": project.start_date,
                    "end_date": project.end_date,
                    "description": f"<p>{admin.get_display_name()} assigned to {project.codename} for demo login visibility.</p>",
                },
            )
            if created:
                self.stats["created"] += 1
            else:
                self._update_object(
                    assignment,
                    {
                        "start_date": project.start_date,
                        "end_date": project.end_date,
                        "description": f"<p>{admin.get_display_name()} assigned to {project.codename} for demo login visibility.</p>",
                    },
                )

    def _configure_company_information(self):
        self._update_object(CompanyInformation.get_solo(), COMPANY_INFORMATION)

    def _configure_report_configuration(self):
        self._update_object(ReportConfiguration.get_solo(), REPORT_CONFIGURATION)

    def _configure_bloodhound_configuration(self):
        if not DEMO_BLOODHOUND_RESULTS_PATH.exists():
            raise CommandError(
                f"Demo BloodHound results fixture is missing: {DEMO_BLOODHOUND_RESULTS_PATH}"
            )
        with DEMO_BLOODHOUND_RESULTS_PATH.open() as results_file:
            bloodhound_results = json.load(results_file)
        self._update_object(
            BloodHoundConfiguration.get_solo(),
            {
                "allow_project_fallback": True,
                "bloodhound_api_root_url": "https://bloodhound.demo.local",
                "bloodhound_api_key_id": "demo-api-key-id",
                "bloodhound_api_key_token": "demo-api-key-token",
                "bloodhound_results": bloodhound_results,
            },
        )

    def _set_tags(self, obj, tags):
        if hasattr(obj, "tags"):
            obj.tags.set(tags)

    def _update_object(self, obj, defaults):
        changed = False
        for field, value in defaults.items():
            if getattr(obj, field) != value:
                setattr(obj, field, value)
                changed = True
        if changed:
            obj.save()
            self.stats["updated"] += 1
        else:
            self.stats["reused"] += 1
        return obj

    def _get_or_update(self, model, lookup, defaults):
        obj = model.objects.filter(
            **lookup,
            extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE},
        ).first()
        if obj is not None:
            return self._update_object(obj, defaults)

        if self.append_mode and model.objects.filter(**lookup).exists():
            description = ", ".join(f"{key}={value!r}" for key, value in lookup.items())
            raise CommandError(
                f"Cannot append demo {model._meta.verbose_name}: "
                f"an unrelated row already uses {description}."
            )

        obj = model.objects.create(**lookup, **defaults)
        self.stats["created"] += 1
        return obj

    def _table_has_column(self, table_name, column_name):
        cache_key = f"_has_column_{table_name}_{column_name}"
        cached = getattr(self, cache_key, None)
        if cached is not None:
            return cached
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, table_name
                )
            }
        has_column = column_name in columns
        setattr(self, cache_key, has_column)
        return has_column

    def _evidence_has_finding_column(self):
        return self._table_has_column("reporting_evidence", "finding_id")

    @contextmanager
    def _disabled_evidence_user_triggers(self):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE reporting_evidence DISABLE TRIGGER USER")
        try:
            yield
        finally:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE reporting_evidence ENABLE TRIGGER USER")

    def _seed_extra_field_specs(self):
        for model in EXTRA_FIELD_MODELS:
            extra_field_model, created = ExtraFieldModel.objects.get_or_create(
                model_internal_name=model._meta.label,
                defaults={
                    "model_display_name": model._meta.verbose_name.title(),
                    "is_collab_editable": model
                    in (Report, ReportFindingLink, ReportObservationLink, OplogEntry),
                },
            )
            if created:
                self.stats["created"] += 1
            else:
                self._update_object(
                    extra_field_model,
                    {
                        "model_display_name": model._meta.verbose_name.title(),
                        "is_collab_editable": model
                        in (
                            Report,
                            ReportFindingLink,
                            ReportObservationLink,
                            OplogEntry,
                        ),
                    },
                )

            model_specs = EXTRA_FIELD_SPECS_BY_MODEL.get(model, EXTRA_FIELD_SPECS)
            for position, spec_data in enumerate(model_specs, start=1):
                spec, created = ExtraFieldSpec.objects.get_or_create(
                    target_model=extra_field_model,
                    internal_name=spec_data["internal_name"],
                    defaults={
                        "display_name": spec_data["display_name"],
                        "description": spec_data["description"],
                        "type": spec_data["type"],
                        "user_default_value": spec_data["user_default_value"],
                        "position": position,
                    },
                )
                if created:
                    self.stats["created"] += 1
                else:
                    self._update_object(
                        spec,
                        {
                            "display_name": spec_data["display_name"],
                            "description": spec_data["description"],
                            "type": spec_data["type"],
                            "user_default_value": spec_data["user_default_value"],
                            "position": position,
                        },
                    )

    def _load_lookup_map(self, model, field_name, values):
        lookup = {}
        for value in values:
            try:
                lookup[value] = model.objects.get(**{field_name: value})
            except model.DoesNotExist as exc:
                raise CommandError(
                    f"Required fixture lookup {model._meta.label}.{field_name}={value!r} is missing. "
                    "Load the initial fixture files before running this command."
                ) from exc
        return lookup

    def _load_lookups(self):
        return {
            "severities": self._load_lookup_map(
                Severity,
                "severity",
                ["Critical", "High", "Medium", "Low", "Informational"],
            ),
            "finding_types": self._load_lookup_map(
                FindingType,
                "finding_type",
                ["Network", "Web", "Cloud", "Host"],
            ),
            "project_types": self._load_lookup_map(
                ProjectType,
                "project_type",
                ["Red Team", "Penetration Test"],
            ),
            "project_roles": self._load_lookup_map(
                ProjectRole,
                "project_role",
                ["Assessment Lead", "Assessment Oversight", "Operator"],
            ),
            "objective_statuses": self._load_lookup_map(
                ObjectiveStatus,
                "objective_status",
                ["Active", "In Progress", "On Hold"],
            ),
            "objective_priorities": self._load_lookup_map(
                ObjectivePriority,
                "priority",
                ["Primary", "Secondary", "Tertiary"],
            ),
            "deconfliction_statuses": self._load_lookup_map(
                DeconflictionStatus,
                "status",
                ["Undetermined", "Confirmed", "Unrelated"],
            ),
            "whois_statuses": self._load_lookup_map(
                WhoisStatus,
                "whois_status",
                ["Enabled", "Disabled", "Unknown"],
            ),
            "health_statuses": self._load_lookup_map(
                HealthStatus,
                "health_status",
                ["Healthy", "Burned", "Questionable"],
            ),
            "domain_statuses": self._load_lookup_map(
                DomainStatus,
                "domain_status",
                ["Available", "Reserved", "Unavailable"],
            ),
            "activity_types": self._load_lookup_map(
                ActivityType,
                "activity",
                ["Command and Control", "Phishing"],
            ),
            "server_statuses": self._load_lookup_map(
                ServerStatus,
                "server_status",
                ["Available", "Reserved", "Unavailable"],
            ),
            "server_providers": self._load_lookup_map(
                ServerProvider,
                "server_provider",
                ["Amazon Web Services", "Microsoft Azure", "Digital Ocean", "Linode"],
            ),
            "server_roles": self._load_lookup_map(
                ServerRole,
                "server_role",
                ["Team Server / C2 Server", "Redirector", "Payload Hosting"],
            ),
        }

    def _seed_users(self):
        User = get_user_model()
        users = {}
        for data in USERS:
            defaults = {
                "name": data["name"],
                "email": data["email"],
                "phone": data["phone"],
                "role": data["role"],
                "timezone": data["timezone"],
                "is_active": True,
                "enable_finding_create": data.get("enable_finding_create", False),
                "enable_finding_edit": data.get("enable_finding_edit", False),
                "enable_finding_delete": False,
                "enable_observation_create": data.get(
                    "enable_observation_create", False
                ),
                "enable_observation_edit": False,
                "enable_observation_delete": False,
                "require_mfa": False,
            }
            try:
                user = User.objects.get(username=data["username"])
                created = False
            except User.DoesNotExist:
                user = User.objects.create(username=data["username"], **defaults)
                created = True
            if created:
                self.stats["created"] += 1
                user.set_password(DEMO_PASSWORD)
                user.save()
            elif self.append_mode:
                self.stats["reused"] += 1
            else:
                self._update_object(user, defaults)
                user.set_password(DEMO_PASSWORD)
                user.save()
            self._ensure_user_profile(user)
            users[user.username] = user
        return users

    def _seed_domains(self, lookups, users):
        today = date.today()
        domains = {}
        operator = users["cmaddalena"]
        for index, (name, registrar, status, health, whois) in enumerate(
            DOMAINS, start=1
        ):
            defaults = {
                "registrar": registrar,
                "dns": {
                    "a": [f"203.0.113.{20 + index}"],
                    "mx": [f"mail.{name}"],
                    "txt": ["v=spf1 include:_spf.google.com ~all"],
                },
                "creation": today - timedelta(days=420 + (index * 31)),
                "expiration": today + timedelta(days=210 + (index * 17)),
                "last_health_check": today - timedelta(days=index),
                "categorization": {
                    "source": "demo",
                    "categories": ["business", "technology"],
                },
                "description": f"Demo domain reserved for realistic Ghostwriter walkthroughs and project infrastructure: {name}.",
                "burned_explanation": "",
                "auto_renew": True,
                "expired": False,
                "reset_dns": True,
                "whois_status": lookups["whois_statuses"][whois],
                "health_status": lookups["health_statuses"][health],
                "domain_status": lookups["domain_statuses"][status],
                "last_used_by": operator,
                "extra_fields": self._demo_extra(Domain, name, seed_index=index),
            }
            domain = self._get_or_update(Domain, {"name": name}, defaults)
            self._set_tags(domain, ["infrastructure", status.lower().replace(" ", "-")])
            domains[name] = domain
        return domains

    def _seed_static_servers(self, lookups, users):
        servers = {}
        operator = users["cmaddalena"]
        for index, (ip_address, name, provider, status) in enumerate(
            STATIC_SERVERS, start=1
        ):
            defaults = {
                "name": name,
                "description": f"Demo {name} server used for redirector, payload, and command-and-control walkthroughs.",
                "server_provider": lookups["server_providers"][provider],
                "server_status": lookups["server_statuses"][status],
                "last_used_by": operator,
                "extra_fields": self._demo_extra(StaticServer, name, seed_index=index),
            }
            server = self._get_or_update(
                StaticServer, {"ip_address": ip_address}, defaults
            )
            self._set_tags(server, ["infrastructure", provider.lower()])
            servers[ip_address] = server
        return servers

    def _seed_findings(self, lookups):
        findings = {}
        for data in FINDINGS:
            defaults = {
                "severity": lookups["severities"][data["severity"]],
                "finding_type": lookups["finding_types"][data["type"]],
                "cvss_score": data["cvss_score"],
                "cvss_vector": data["cvss_vector"],
                "description": data["description"],
                "impact": data["impact"],
                "mitigation": data["mitigation"],
                "replication_steps": data["replication_steps"],
                "host_detection_techniques": data["host_detection_techniques"],
                "network_detection_techniques": data["network_detection_techniques"],
                "references": data["references"],
                "finding_guidance": data["finding_guidance"],
                "extra_fields": self._demo_extra(Finding, data["title"]),
            }
            finding = self._get_or_update(Finding, {"title": data["title"]}, defaults)
            self._set_tags(finding, data["tags"])
            findings[data["title"]] = finding
        return findings

    def _seed_observations(self):
        observations = {}
        for data in OBSERVATIONS:
            observation = self._get_or_update(
                Observation,
                {"title": data["title"]},
                {
                    "description": data["description"],
                    "extra_fields": self._demo_extra(Observation, data["title"]),
                },
            )
            self._set_tags(observation, data["tags"])
            observations[data["title"]] = observation
        return observations

    def _seed_clients_and_projects(
        self,
        lookups,
        users,
        domains,
        servers,
        findings,
        observations,
        client_limit,
        project_limit,
    ):
        clients = []
        projects = []
        selected_clients = CLIENTS[:client_limit]
        for client_index, data in enumerate(selected_clients, start=1):
            client = self._seed_client(data, client_index)
            clients.append(client)
            self._replace_client_contacts(client, data)
            for project_index, project_data in enumerate(
                data["projects"][:project_limit], start=1
            ):
                project = self._seed_project(
                    client, project_data, client_index, project_index, lookups, users
                )
                projects.append(project)
                self._replace_project_children(
                    project,
                    project_data,
                    lookups,
                    users,
                    domains,
                    servers,
                    findings,
                    observations,
                )
        return clients, projects

    def _seed_client(self, data, index):
        defaults = {
            "short_name": data["short_name"],
            "codename": data["codename"],
            "description": data["description"],
            "timezone": data["timezone"],
            "address": data["address"],
            "extra_fields": self._demo_extra(Client, data["name"], seed_index=index),
        }
        client = self._get_or_update(Client, {"name": data["name"]}, defaults)
        self._set_tags(client, ["client", data["codename"].lower()])
        return client

    def _replace_client_contacts(self, client, data):
        ClientContact.objects.filter(client=client).delete()
        for name, title, email, phone, primary in data["contacts"]:
            ClientContact.objects.create(
                client=client,
                name=name,
                job_title=title,
                email=email,
                phone=phone,
                timezone=data["timezone"],
                description=f"<p>{name} is a demo stakeholder for {client.name}.</p>",
                primary=primary,
            )
            self.stats["created"] += 1

    def _seed_project(self, client, data, client_index, project_index, lookups, users):
        today = date.today()
        if data["schedule"] == "past":
            end_date = today - timedelta(days=20 + (client_index * 4) + project_index)
            start_date = end_date - timedelta(days=21 + (project_index * 7))
        elif data["schedule"] == "current":
            start_date = today - timedelta(days=8 + (client_index * 3) + project_index)
            end_date = today + timedelta(days=18 + (client_index * 4) + project_index)
        else:
            start_date = today + timedelta(days=12 + (client_index * 3) + project_index)
            end_date = start_date + timedelta(days=21 + (project_index * 7))
        operator = users["cmaddalena"] if project_index == 1 else users["pstanz"]
        defaults = {
            "client": client,
            "project_type": lookups["project_types"][data["type"]],
            "operator": operator,
            "start_date": start_date,
            "end_date": end_date,
            "description": data["description"],
            "slack_channel": data["slack"],
            "complete": data["complete"],
            "timezone": client.timezone,
            "start_time": time(9, 0),
            "end_time": time(17, 0),
            "collab_note": "<p>Demo notes: daily sync at 10:00 local, report QA every Friday.</p>",
            "bloodhound_api_root_url": "",
            "bloodhound_api_key_id": "",
            "bloodhound_api_key_token": "",
            "bloodhound_results": None,
            "extra_fields": self._demo_extra(
                Project, data["codename"], seed_index=f"{client_index}-{project_index}"
            ),
        }
        project = self._get_or_update(Project, {"codename": data["codename"]}, defaults)
        self._set_tags(project, ["project", data["type"].lower().replace(" ", "-")])
        return project

    def _replace_project_children(
        self, project, data, lookups, users, domains, servers, findings, observations
    ):
        self._delete_project_children(project)
        assignments = self._create_assignments(project, lookups, users)
        self._create_project_contacts(project)
        self._create_scope_and_targets(project, data)
        self._create_objectives(project, data, lookups)
        self._create_deconflictions_and_whitecards(project, lookups)
        histories, server_histories, transient_servers = self._create_infrastructure(
            project, lookups, users, domains, servers, assignments
        )
        self._create_domain_connections(
            project, histories, server_histories, transient_servers
        )
        report = self._create_report(project, users)
        report_findings = self._create_report_findings(
            report, data, lookups, users, findings
        )
        self._create_report_observations(report, users, observations)
        self._create_evidence(report_findings, users)
        self._create_oplog(project, data, assignments)

    def _delete_project_children(self, project):
        self._delete_project_evidence(project)
        self._delete_project_reports(project)
        Oplog.objects.filter(project=project).delete()
        DomainServerConnection.objects.filter(project=project).delete()
        History.objects.filter(project=project).delete()
        ServerHistory.objects.filter(project=project).delete()
        TransientServer.objects.filter(project=project).delete()
        Deconfliction.objects.filter(project=project).delete()
        WhiteCard.objects.filter(project=project).delete()
        ProjectContact.objects.filter(project=project).delete()
        ProjectAssignment.objects.filter(project=project).delete()
        ProjectScope.objects.filter(project=project).delete()
        ProjectTarget.objects.filter(project=project).delete()
        ProjectObjective.objects.filter(project=project).delete()

    def _delete_project_evidence(self, project):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT document FROM reporting_evidence
                WHERE report_id IN (
                    SELECT id FROM reporting_report WHERE project_id = %s
                )
                """,
                [project.pk],
            )
            document_paths = [row[0] for row in cursor.fetchall() if row[0]]

        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM reporting_evidence
                WHERE report_id IN (
                    SELECT id FROM reporting_report WHERE project_id = %s
                )
                """,
                [project.pk],
            )
        for document_path in document_paths:
            default_storage.delete(document_path)

    def _delete_project_reports(self, project):
        if self._evidence_has_finding_column():
            Report.objects.filter(project=project).delete()
            return

        using = connection.alias
        ReportFindingLink.objects.filter(report__project=project)._raw_delete(using)
        ReportObservationLink.objects.filter(report__project=project)._raw_delete(using)
        Report.objects.filter(project=project)._raw_delete(using)

    def _create_assignments(self, project, lookups, users):
        assignment_data = [
            ("cmaddalena", "Assessment Lead"),
            ("pstanz", "Operator"),
            ("rstantz", "Operator"),
            ("espengler", "Assessment Oversight"),
        ]
        admin = self._get_install_admin()
        today = date.today()
        project_is_active = (
            project.start_date <= today <= project.end_date and not project.complete
        )
        assigned_users = [users[username] for username, _ in assignment_data]
        if project_is_active and admin is not None and admin not in assigned_users:
            assignment_data[0] = (admin, "Assessment Lead")

        assignments = []
        for user_ref, role in assignment_data:
            operator = users[user_ref] if isinstance(user_ref, str) else user_ref
            assignment = ProjectAssignment.objects.create(
                project=project,
                operator=operator,
                role=lookups["project_roles"][role],
                start_date=project.start_date,
                end_date=project.end_date,
                description=f"<p>{operator.name} assigned as {role.lower()} for {project.codename}.</p>",
            )
            assignments.append(assignment)
            self.stats["created"] += 1
        return assignments

    def _create_project_contacts(self, project):
        primary = ClientContact.objects.filter(
            client=project.client, primary=True
        ).first()
        contacts = ClientContact.objects.filter(client=project.client).order_by("id")[
            :2
        ]
        for contact in contacts:
            ProjectContact.objects.create(
                project=project,
                name=contact.name,
                job_title=contact.job_title,
                email=contact.email,
                phone=contact.phone,
                timezone=contact.timezone,
                description=contact.description,
                primary=primary and contact.pk == primary.pk,
            )
            self.stats["created"] += 1

    def _create_scope_and_targets(self, project, data):
        ProjectScope.objects.create(
            project=project,
            name="Approved Assessment Scope",
            scope="\n".join(data["scope"]),
            description="Systems and hostnames approved for the demo engagement.",
            disallowed=False,
            requires_caution=False,
        )
        ProjectScope.objects.create(
            project=project,
            name="Restricted Systems",
            scope="payment-processing.internal\nexecutive-workstations.local",
            description="Demo examples of restricted systems requiring explicit approval.",
            disallowed=True,
            requires_caution=True,
        )
        self.stats["created"] += 2
        for ip_address, hostname, description, compromised in data["targets"]:
            ProjectTarget.objects.create(
                project=project,
                ip_address=ip_address,
                hostname=hostname,
                description=description,
                compromised=compromised,
            )
            self.stats["created"] += 1

    def _create_objectives(self, project, data, lookups):
        for index, objective_text in enumerate(data["objectives"], start=1):
            complete = project.complete and index < len(data["objectives"])
            objective = ProjectObjective.objects.create(
                project=project,
                objective=objective_text,
                description=f"<p>{objective_text}. Evidence and status are maintained in Ghostwriter for demo reporting.</p>",
                complete=complete,
                marked_complete=project.end_date if complete else None,
                deadline=project.start_date + timedelta(days=index * 5),
                position=index,
                result="<p>Completed with evidence captured.</p>" if complete else "",
                status=lookups["objective_statuses"][
                    "In Progress" if complete else "Active"
                ],
                priority=lookups["objective_priorities"][
                    "Primary" if index == 1 else "Secondary"
                ],
            )
            self.stats["created"] += 1
            for task_index, task in enumerate(
                [
                    "Prepare test plan",
                    "Execute approved activity",
                    "Attach evidence and notes",
                ],
                start=1,
            ):
                ProjectSubTask.objects.create(
                    parent=objective,
                    task=f"{task} for {objective_text.lower()}",
                    complete=complete or task_index == 1,
                    marked_complete=project.start_date + timedelta(days=task_index)
                    if complete
                    else None,
                    deadline=project.start_date
                    + timedelta(days=(index * 5) - 1 + task_index),
                    status=lookups["objective_statuses"][
                        "In Progress" if complete or task_index == 1 else "Active"
                    ],
                )
                self.stats["created"] += 1

    def _create_deconflictions_and_whitecards(self, project, lookups):
        base_time = timezone.make_aware(
            datetime.combine(project.start_date + timedelta(days=3), time(14, 30))
        )
        deconflictions = [
            (
                "EDR alert for PowerShell reconnaissance",
                "Client SOC reported PowerShell discovery activity from an approved test workstation.",
                "SentinelOne",
                "Confirmed",
                base_time,
                base_time + timedelta(minutes=12),
                base_time + timedelta(minutes=31),
            ),
            (
                "VPN login from test operator address",
                "Help desk requested confirmation for an unusual VPN login during the scheduled access window.",
                "Help Desk",
                "Unrelated",
                base_time + timedelta(days=2, hours=1),
                base_time + timedelta(days=2, hours=1, minutes=8),
                base_time + timedelta(days=2, hours=1, minutes=23),
            ),
        ]
        for (
            title,
            description,
            source,
            status,
            report_time,
            alert_time,
            response_time,
        ) in deconflictions:
            Deconfliction.objects.create(
                project=project,
                report_timestamp=report_time,
                alert_timestamp=alert_time,
                response_timestamp=response_time,
                title=title,
                description=description,
                alert_source=source,
                status=lookups["deconfliction_statuses"][status],
            )
            self.stats["created"] += 1

        whitecards = [
            (
                project.start_date + timedelta(days=2),
                "Client-provided VPN account enabled",
                "The client provisioned the assessment team account gbi-redteam-vpn and confirmed MFA enrollment for initial access testing.",
            ),
            (
                project.start_date + timedelta(days=6),
                "Client executed payload for initial access",
                "The project sponsor launched the approved launcher on a victim workstation to bootstrap the assumed-breach scenario.",
            ),
            (
                project.start_date + timedelta(days=10),
                "Test account unlocked by help desk",
                "Client help desk unlocked the delegated finance test account and confirmed the password reset window for continued validation.",
            ),
        ]
        for issued_date, title, description in whitecards:
            WhiteCard.objects.create(
                project=project,
                issued=timezone.make_aware(datetime.combine(issued_date, time(11, 15))),
                title=title,
                description=description,
            )
            self.stats["created"] += 1

    def _create_infrastructure(
        self, project, lookups, users, domains, servers, assignments
    ):
        activity_cycle = [
            lookups["activity_types"]["Command and Control"],
            lookups["activity_types"]["Phishing"],
        ]
        server_role_cycle = [
            lookups["server_roles"]["Team Server / C2 Server"],
            lookups["server_roles"]["Payload Hosting"],
            lookups["server_roles"]["Redirector"],
        ]
        selected_domains = list(domains.values())[:3]
        selected_servers = list(servers.values())[:3]
        histories = []
        server_histories = []
        transient_servers = []
        admin = self._get_install_admin()
        for index, domain in enumerate(selected_domains):
            operator = (
                admin
                if index == 0 and admin is not None
                else assignments[index % len(assignments)].operator
            )
            history = History.objects.create(
                domain=domain,
                client=project.client,
                project=project,
                operator=operator,
                activity_type=activity_cycle[index % len(activity_cycle)],
                start_date=project.start_date,
                end_date=project.end_date,
                description=f"Demo checkout for {project.codename} infrastructure.",
            )
            histories.append(history)
            if index == 0:
                domain.domain_status = lookups["domain_statuses"]["Unavailable"]
                domain.last_used_by = operator
                domain.save(update_fields=["domain_status", "last_used_by"])
            self.stats["created"] += 1

        for index, server in enumerate(selected_servers):
            operator = (
                admin
                if index == 0 and admin is not None
                else assignments[index % len(assignments)].operator
            )
            server_history = ServerHistory.objects.create(
                server=server,
                client=project.client,
                project=project,
                operator=operator,
                server_role=server_role_cycle[index % len(server_role_cycle)],
                activity_type=activity_cycle[index % len(activity_cycle)],
                start_date=project.start_date,
                end_date=project.end_date,
                description=f"Demo static server checkout for {project.codename}.",
            )
            server_histories.append(server_history)
            if index == 0:
                server.server_status = lookups["server_statuses"]["Unavailable"]
                server.last_used_by = operator
                server.save(update_fields=["server_status", "last_used_by"])
            self.stats["created"] += 1

        for index in range(2):
            transient = TransientServer.objects.create(
                project=project,
                operator=assignments[index].operator,
                server_provider=lookups["server_providers"][
                    "Amazon Web Services" if index == 0 else "Microsoft Azure"
                ],
                server_role=server_role_cycle[index],
                activity_type=activity_cycle[index],
                ip_address=f"10.{70 + index}.{project.pk % 250}.10",
                aux_address=[f"10.{70 + index}.{project.pk % 250}.11"],
                name=f"{project.codename.lower()}-vps-{index + 1}",
                description="Ephemeral demo VPS used for project activity.",
            )
            transient_servers.append(transient)
            self.stats["created"] += 1
        return histories, server_histories, transient_servers

    def _create_domain_connections(
        self, project, histories, server_histories, transient_servers
    ):
        for index, history in enumerate(histories):
            if index % 2 == 0:
                DomainServerConnection.objects.create(
                    project=project,
                    domain=history,
                    static_server=server_histories[index % len(server_histories)],
                    transient_server=None,
                    subdomain="cdn" if index else "*",
                    endpoint=f"{project.codename.lower()}-edge.cloudfront.example",
                )
            else:
                DomainServerConnection.objects.create(
                    project=project,
                    domain=history,
                    static_server=None,
                    transient_server=transient_servers[index % len(transient_servers)],
                    subdomain="login",
                    endpoint="",
                )
            self.stats["created"] += 1

    def _create_report(self, project, users):
        report = Report.objects.create(
            project=project,
            title=f"{project.client.short_name} {project.codename} Security Assessment Report",
            complete=project.complete,
            archived=False,
            created_by=users["cmaddalena"],
            delivered=project.complete,
            include_bloodhound_data=True,
            extra_fields=self._demo_extra(Report, project.codename),
        )
        self._set_tags(report, ["report", project.codename.lower()])
        self.stats["created"] += 1
        return report

    def _create_report_findings(self, report, data, lookups, users, findings):
        selected_findings = list(findings.values())[:3]
        if "partner" in data["description"].lower():
            selected_findings = list(findings.values())[1:4]
        report_findings = []
        targets = ProjectTarget.objects.filter(project=report.project).order_by(
            "hostname"
        )
        affected_entities = "<ul>{}</ul>".format(
            "".join(
                f"<li>{target.hostname or target.ip_address}</li>"
                for target in targets[:3]
            )
        )
        for position, finding in enumerate(selected_findings, start=1):
            report_finding = ReportFindingLink.objects.create(
                report=report,
                title=finding.title,
                position=position,
                affected_entities=affected_entities,
                description=finding.description,
                impact=finding.impact,
                mitigation=finding.mitigation,
                replication_steps=finding.replication_steps,
                host_detection_techniques=finding.host_detection_techniques,
                network_detection_techniques=finding.network_detection_techniques,
                references=finding.references,
                finding_guidance=finding.finding_guidance,
                complete=report.complete,
                added_as_blank=False,
                severity=finding.severity,
                finding_type=finding.finding_type,
                assigned_to=users["espengler"],
                cvss_score=finding.cvss_score,
                cvss_vector=finding.cvss_vector,
                extra_fields=self._demo_extra(
                    ReportFindingLink,
                    finding.title,
                    library_finding_id=finding.pk,
                ),
            )
            self._set_tags(report_finding, list(finding.tags.names()))
            report_findings.append(report_finding)
            self.stats["created"] += 1
        return report_findings

    def _create_report_observations(self, report, users, observations):
        for position, observation in enumerate(list(observations.values()), start=1):
            report_observation = ReportObservationLink.objects.create(
                report=report,
                title=observation.title,
                position=position,
                description=observation.description,
                added_as_blank=False,
                complete=report.complete,
                assigned_to=users["rstantz"],
                extra_fields=self._demo_extra(ReportObservationLink, observation.title),
            )
            self._set_tags(report_observation, list(observation.tags.names()))
            self.stats["created"] += 1

    def _create_evidence(self, report_findings, users):
        for index, report_finding in enumerate(report_findings, start=1):
            sample = DEMO_EVIDENCE_TEXT_SAMPLES[
                (index - 1) % len(DEMO_EVIDENCE_TEXT_SAMPLES)
            ]
            self._create_evidence_file(
                report=report_finding.report,
                sample=sample,
                uploaded_by=users["cmaddalena"],
            )

    def _create_evidence_file(self, report, sample, uploaded_by):
        content = sample["path"].read_bytes()
        filename = sample["path"].name
        if self._evidence_has_finding_column():
            evidence = Evidence(
                report=report,
                friendly_name=sample["friendly_name"],
                caption=sample["caption"],
                description=sample["description"],
                uploaded_by=uploaded_by,
            )
            evidence.document.save(filename, ContentFile(content), save=True)
            self._set_tags(evidence, ["evidence", *sample["tags"]])
        else:
            document_path = default_storage.save(
                f"evidence/{report.pk}/{filename}", ContentFile(content)
            )
            self._create_report_evidence_without_finding_column(
                report=report,
                document_path=document_path,
                friendly_name=sample["friendly_name"],
                caption=sample["caption"],
                description=sample["description"],
                uploaded_by=uploaded_by,
            )
        self.stats["created"] += 1

    def _create_report_evidence_without_finding_column(
        self, report, document_path, friendly_name, caption, description, uploaded_by
    ):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO reporting_evidence (
                    document,
                    friendly_name,
                    upload_date,
                    caption,
                    description,
                    report_id,
                    uploaded_by_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    document_path,
                    friendly_name,
                    date.today(),
                    caption,
                    description,
                    report.pk,
                    uploaded_by.pk,
                ],
            )

    def _create_oplog(self, project, data, assignments):
        log = Oplog.objects.create(
            project=project, name=f"{project.codename} Daily Activity Log"
        )
        self.stats["created"] += 1
        base_time = timezone.make_aware(
            datetime.combine(project.start_date, time(10, 0))
        )
        targets = list(
            ProjectTarget.objects.filter(project=project).order_by("hostname")
        )
        hosts = [target.hostname or target.ip_address for target in targets] or [
            "demo.local"
        ]
        for index, (tool, command, description, tags) in enumerate(
            OPLOG_STEPS, start=1
        ):
            target = targets[index % len(targets)] if targets else None
            host = hosts[index % len(hosts)]
            start_date = base_time + timedelta(hours=index * 3)
            entry = OplogEntry.objects.create(
                oplog_id=log,
                entry_identifier=f"{project.codename}-{index:03d}",
                start_date=start_date,
                end_date=start_date + timedelta(minutes=18 + index),
                source_ip=f"10.99.{project.pk % 250}.{20 + index}",
                dest_ip=(target.ip_address if target else host),
                tool=tool,
                user_context=r"DEMO\operator",
                operator_name=assignments[index % len(assignments)].operator.username,
                command=command.format(
                    target=target.ip_address if target else host, host=host
                ),
                description=description,
                output=f"Completed demo step {index} for {project.codename}; evidence reviewed.",
                comments="Reviewed during daily sync; no client-impacting issues observed.",
                extra_fields=self._demo_extra(
                    OplogEntry, f"{project.codename}-{index:03d}"
                ),
            )
            entry.tags.set(tags)
            self.stats["created"] += 1

    def _reset_demo_data(self):
        demo_projects = Project.objects.filter(
            extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}
        )
        for project in demo_projects:
            self._delete_project_children(project)
        deleted_projects, _ = demo_projects.delete()

        deleted_clients, _ = Client.objects.filter(
            extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}
        ).delete()
        deleted_findings, _ = Finding.objects.filter(
            extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}
        ).delete()
        deleted_observations, _ = Observation.objects.filter(
            extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}
        ).delete()
        deleted_domains, _ = Domain.objects.filter(
            extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}
        ).delete()
        deleted_servers, _ = StaticServer.objects.filter(
            extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}
        ).delete()
        self.stats["deleted"] += (
            deleted_projects
            + deleted_clients
            + deleted_findings
            + deleted_observations
            + deleted_domains
            + deleted_servers
        )

    def _print_summary(self, clients, projects):
        self.stdout.write(self.style.SUCCESS("Demo data seed complete."))
        self.stdout.write(
            f"  Users: {get_user_model().objects.filter(username__in=[user['username'] for user in USERS]).count()}"
        )
        self.stdout.write(f"  Clients: {len(clients)}")
        self.stdout.write(f"  Projects: {len(projects)}")
        self.stdout.write(
            f"  Domains: {Domain.objects.filter(extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}).count()}"
        )
        self.stdout.write(
            f"  Findings: {Finding.objects.filter(extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}).count()}"
        )
        self.stdout.write(
            f"  Reports: {Report.objects.filter(extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}).count()}"
        )
        self.stdout.write(f"  Evidence: {self._count_demo_evidence()}")
        self.stdout.write(
            f"  Oplog Entries: {OplogEntry.objects.filter(extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}).count()}"
        )
        self.stdout.write(
            "  Row operations: "
            f"created={self.stats['created']} "
            f"updated={self.stats['updated']} "
            f"reused={self.stats['reused']} "
            f"deleted={self.stats['deleted']} "
            f"fixtures={self.stats['fixtures']}"
        )

    def _count_demo_evidence(self):
        if self._evidence_has_finding_column():
            return Evidence.objects.filter(
                report__extra_fields__contains={DEMO_MARKER_KEY: DEMO_MARKER_VALUE}
            ).count()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM reporting_evidence evidence
                INNER JOIN reporting_report report ON evidence.report_id = report.id
                WHERE report.extra_fields @> %s::jsonb
                """,
                [f'{{"{DEMO_MARKER_KEY}": "{DEMO_MARKER_VALUE}"}}'],
            )
            return cursor.fetchone()[0]
