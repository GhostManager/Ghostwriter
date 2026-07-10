# Copy this to `local.d` to enable django debug logging and logging
# of all SQL queries

LOGGING["root"]["level"] = "DEBUG"
LOGGING.setdefault("loggers", {})["django.db.backends"] = {
    "level": "DEBUG"
}
