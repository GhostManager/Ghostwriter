"""Narrow Django Q task wrappers approved by server-side policy."""

# Standard Libraries
import subprocess

# Django Imports
from django.core.management import call_command

# Ghostwriter Libraries
from ghostwriter.home.django_q_policy import (
    TaskPolicyError,
    get_command_policy,
    validate_command_policy,
)


def clear_expired_sessions():
    """Run only Ghostwriter's expired-session cleanup management command."""
    call_command("clear_expired_sessions")


def run_configured_command(command_name):
    """Run one fixed server-approved command without a shell."""
    validate_command_policy()
    commands = get_command_policy()
    if command_name not in commands:
        raise TaskPolicyError("The requested command is not approved")
    command = commands[command_name]
    completed = subprocess.run(
        list(command["argv"]),
        cwd=command.get("cwd"),
        env=dict(command.get("env", {})),
        shell=False,
        check=True,
        timeout=command.get("timeout"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {"returncode": completed.returncode}
