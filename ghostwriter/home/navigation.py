"""Build the application navigation shown in Ghostwriter's sidebar."""

# Standard Libraries
from collections import OrderedDict

# Django Imports
from django.urls import reverse

SIDEBAR_PREFERENCES_VERSION = 2

SIDEBAR_PANELS = (
    {
        "id": "working_context",
        "label": "Working context",
        "description": "Choose the report that receives library quick-adds",
        "icon": "fas fa-bullseye",
    },
    {
        "id": "pinned_work",
        "label": "Pinned work",
        "description": "Shortcuts to saved clients, projects, and reports",
        "icon": "fas fa-thumbtack",
    },
)

SIDEBAR_PANEL_BY_ID = {panel["id"]: panel for panel in SIDEBAR_PANELS}
DEFAULT_PANEL_ORDER = tuple(panel["id"] for panel in SIDEBAR_PANELS)
DEFAULT_VISIBLE_PANELS = DEFAULT_PANEL_ORDER

CORE_NAVIGATION = (
    {
        "id": "dashboard",
        "label": "Dashboard",
        "description": "Your operational overview",
        "icon": "fas fa-home",
        "url_name": "home:dashboard",
        "active_names": ("dashboard",),
    },
    {
        "id": "clients",
        "label": "Clients",
        "description": "Client workspaces and contacts",
        "icon": "fas fa-address-book",
        "url_name": "rolodex:clients",
        "active_prefixes": ("client",),
        "active_names": ("clients",),
    },
    {
        "id": "projects",
        "label": "Projects",
        "description": "Engagement planning and execution",
        "icon": "fas fa-project-diagram",
        "url_name": "rolodex:projects",
        "active_prefixes": ("project",),
        "active_names": ("projects",),
    },
    {
        "id": "reports",
        "label": "Reports",
        "description": "Report workspaces and delivery",
        "icon": "fas fa-file-alt",
        "url_name": "reporting:reports",
        "active_prefixes": ("report_", "generate_"),
        "active_names": ("reports",),
    },
)

OPTIONAL_NAVIGATION = (
    {
        "id": "findings",
        "label": "Findings",
        "description": "Reusable finding library",
        "icon": "fas fa-shield-alt",
        "url_name": "reporting:findings",
        "group": "Reporting",
        "active_prefixes": ("finding",),
        "active_names": ("findings",),
    },
    {
        "id": "templates",
        "label": "Templates",
        "description": "DOCX and PPTX report templates",
        "icon": "fas fa-layer-group",
        "url_name": "reporting:templates",
        "group": "Reporting",
        "active_prefixes": ("template",),
        "active_names": ("templates",),
    },
    {
        "id": "observations",
        "label": "Observations",
        "description": "Reusable observation library",
        "icon": "fas fa-binoculars",
        "url_name": "reporting:observations",
        "group": "Reporting",
        "active_prefixes": ("observation",),
        "active_names": ("observations",),
    },
    {
        "id": "archived_reports",
        "label": "Report Archive",
        "description": "Completed report archives",
        "icon": "fas fa-archive",
        "url_name": "reporting:archived_reports",
        "group": "Reporting",
        "active_names": ("archived_reports", "download_archive"),
    },
    {
        "id": "oplogs",
        "label": "Operation Logs",
        "description": "Timestamped operator activity",
        "icon": "fas fa-clipboard-list",
        "url_name": "oplog:index",
        "group": "Operations",
        "active_namespace": "oplog",
    },
    {
        "id": "active_assets",
        "label": "My Active Assets",
        "description": "Infrastructure checked out to you",
        "icon": "fas fa-boxes",
        "url_name": "shepherd:user_assets",
        "group": "Operations",
        "active_names": ("user_assets",),
    },
    {
        "id": "servers",
        "label": "Servers",
        "description": "Server inventory and checkouts",
        "icon": "fas fa-server",
        "url_name": "shepherd:servers",
        "group": "Infrastructure",
        "active_prefixes": ("server", "vps"),
        "active_names": ("servers",),
    },
    {
        "id": "domains",
        "label": "Domains",
        "description": "Domain inventory and health",
        "icon": "fas fa-globe",
        "url_name": "shepherd:domains",
        "group": "Infrastructure",
        "active_prefixes": ("domain", "history", "checkout", "burn"),
        "active_names": ("domains",),
    },
    {
        "id": "update_controls",
        "label": "Update Controls",
        "description": "Refresh infrastructure metadata",
        "icon": "fas fa-sync-alt",
        "url_name": "shepherd:update",
        "group": "Infrastructure",
        "active_names": ("update",),
    },
    {
        "id": "management",
        "label": "Configuration",
        "description": "Review Ghostwriter integrations",
        "icon": "fas fa-sliders-h",
        "url_name": "home:management",
        "group": "System",
        "permission": "privileged",
        "active_names": ("management",),
    },
    {
        "id": "admin",
        "label": "Admin Panel",
        "description": "Users, system data, and imports",
        "icon": "fas fa-user-cog",
        "url_name": "admin:index",
        "group": "System",
        "permission": "staff",
        "active_namespace": "admin",
    },
)

OPTIONAL_NAVIGATION_BY_ID = {item["id"]: item for item in OPTIONAL_NAVIGATION}
DEFAULT_OPTIONAL_ORDER = tuple(item["id"] for item in OPTIONAL_NAVIGATION)
DEFAULT_PINNED = ()


def _is_allowed(item, user):
    permission = item.get("permission")
    if permission == "privileged":
        return user.is_privileged
    if permission == "staff":
        return user.is_staff
    return True


def get_allowed_optional_ids(user):
    """Return allowed optional item IDs in canonical registry order."""
    return tuple(item["id"] for item in OPTIONAL_NAVIGATION if _is_allowed(item, user))


def normalize_sidebar_preferences(preferences, allowed_ids=None):
    """Return a safe, complete preference payload containing registry IDs only."""
    if allowed_ids is None:
        allowed_ids = DEFAULT_OPTIONAL_ORDER
    allowed_ids = tuple(
        item_id for item_id in allowed_ids if item_id in OPTIONAL_NAVIGATION_BY_ID
    )
    allowed_set = set(allowed_ids)

    if not isinstance(preferences, dict) or preferences.get("version") not in {
        1,
        SIDEBAR_PREFERENCES_VERSION,
    }:
        preferences = {}

    raw_order = preferences.get("order", ())
    if not isinstance(raw_order, (list, tuple)):
        raw_order = ()
    order = []
    for item_id in raw_order:
        if item_id in allowed_set and item_id not in order:
            order.append(item_id)
    order.extend(item_id for item_id in allowed_ids if item_id not in order)

    raw_pinned = preferences.get("pinned", DEFAULT_PINNED)
    if not isinstance(raw_pinned, (list, tuple)):
        raw_pinned = DEFAULT_PINNED
    pinned_set = {item_id for item_id in raw_pinned if item_id in allowed_set}
    pinned = [item_id for item_id in order if item_id in pinned_set]

    raw_panel_order = preferences.get("panel_order", DEFAULT_PANEL_ORDER)
    if not isinstance(raw_panel_order, (list, tuple)):
        raw_panel_order = DEFAULT_PANEL_ORDER
    panel_order = []
    for panel_id in raw_panel_order:
        if panel_id in SIDEBAR_PANEL_BY_ID and panel_id not in panel_order:
            panel_order.append(panel_id)
    panel_order.extend(
        panel_id for panel_id in DEFAULT_PANEL_ORDER if panel_id not in panel_order
    )

    raw_visible_panels = preferences.get("visible_panels", DEFAULT_VISIBLE_PANELS)
    if not isinstance(raw_visible_panels, (list, tuple)):
        raw_visible_panels = DEFAULT_VISIBLE_PANELS
    visible_panel_set = {
        panel_id for panel_id in raw_visible_panels if panel_id in SIDEBAR_PANEL_BY_ID
    }
    visible_panels = [
        panel_id for panel_id in panel_order if panel_id in visible_panel_set
    ]

    return {
        "version": SIDEBAR_PREFERENCES_VERSION,
        "pinned": pinned,
        "order": order,
        "panel_order": panel_order,
        "visible_panels": visible_panels,
    }


def _is_active(item, request):
    match = getattr(request, "resolver_match", None)
    if match is None:
        return False

    namespace = match.namespace or ""
    url_name = match.url_name or ""
    active_namespace = item.get("active_namespace")
    if active_namespace and namespace == active_namespace:
        return True
    if url_name in item.get("active_names", ()):
        return True
    return any(
        url_name.startswith(prefix) for prefix in item.get("active_prefixes", ())
    )


def _resolve_item(item, request, pinned=False):
    return {
        "id": item["id"],
        "label": item["label"],
        "description": item["description"],
        "icon": item["icon"],
        "url": reverse(item["url_name"]),
        "group": item.get("group"),
        "pinned": pinned,
        "active": _is_active(item, request),
    }


def get_sidebar_navigation(request):
    """Return permission-filtered core, pinned, and catalog navigation."""
    user = request.user
    if not user.is_authenticated:
        return None

    allowed_optional = [item for item in OPTIONAL_NAVIGATION if _is_allowed(item, user)]
    allowed_ids = get_allowed_optional_ids(user)
    preferences = normalize_sidebar_preferences(
        getattr(user, "sidebar_preferences", {}),
        allowed_ids,
    )
    pinned_ids = set(preferences["pinned"])
    allowed_by_id = {item["id"]: item for item in allowed_optional}

    core = [_resolve_item(item, request) for item in CORE_NAVIGATION]
    ordered_optional = [
        allowed_by_id[item_id]
        for item_id in preferences["order"]
        if item_id in allowed_by_id
    ]
    pinned = [
        _resolve_item(item, request, pinned=True)
        for item in ordered_optional
        if item["id"] in pinned_ids
    ]
    more = [
        _resolve_item(item, request)
        for item in ordered_optional
        if item["id"] not in pinned_ids
    ]

    grouped_more = OrderedDict()
    for item in more:
        grouped_more.setdefault(item["group"], []).append(item)

    customizable = []
    for item in ordered_optional:
        resolved_item = _resolve_item(item, request, item["id"] in pinned_ids)
        customizable.append(resolved_item)

    visible_panel_ids = set(preferences["visible_panels"])
    panels = [
        {
            **SIDEBAR_PANEL_BY_ID[panel_id],
            "visible": panel_id in visible_panel_ids,
        }
        for panel_id in preferences["panel_order"]
    ]

    return {
        "core": core,
        "panels": panels,
        "pinned": pinned,
        "more": more,
        "more_groups": [
            {"label": label, "items": items} for label, items in grouped_more.items()
        ],
        "customizable": customizable,
        "preferences": preferences,
        "order_value": ",".join(preferences["order"]),
        "panel_order_value": ",".join(preferences["panel_order"]),
        "has_active_more": any(item["active"] for item in more),
    }
