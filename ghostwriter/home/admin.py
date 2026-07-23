"""This contains customizations for displaying the Home application models in the admin panel."""

# Standard Libraries
import os

# Django Imports
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

# 3rd Party Libraries
from django_q import admin as django_q_admin
from django_q.models import Failure, Schedule, Success
from django_q.tasks import async_task

# Ghostwriter Libraries
from ghostwriter.home.django_q_policy import (
    TaskPolicyError,
    get_hook_policy,
    get_schedule_policy,
    validate_schedule,
)
from ghostwriter.home.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    list_filter = ("user",)
    readonly_fields = ("avatar_download_link",)
    search_fields = ("user__username", "user__email")

    class Media:
        js = ('js/admin/userprofile_admin.js',)

    def avatar_download_link(self, obj):
        """Display a download link in the detail view."""
        try:
            file_path = obj.avatar.path
        except ValueError:
            file_path = os.path.join(settings.STATICFILES_DIRS[0], "images/default_avatar.png")

        if os.path.exists(file_path) and obj.avatar and obj.id:
            filename = os.path.basename(obj.avatar.name)
            return format_html(
                '<a href="{url}" download="{filename}">{filename}</a>',
                url=reverse("users:avatar_download", args=[obj.user.username]),
                filename=filename
            )
        return "File missing or not available for download"
    avatar_download_link.short_description = "Download File"


class RestrictedScheduleForm(forms.ModelForm):
    """Expose only server-approved functions and hooks for scheduled tasks."""

    func = forms.ChoiceField(label="Function")
    hook = forms.ChoiceField(label="Hook", required=False)

    class Meta:
        model = Schedule
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        task_policy = get_schedule_policy()
        self.fields["func"].choices = [
            (path, specification.get("label", path))
            for path, specification in sorted(
                task_policy.items(),
                key=lambda item: item[1].get("label", item[0]),
            )
        ]
        hook_policy = get_hook_policy(schedule_only=True)
        self.fields["hook"].choices = [("", "---------")] + [
            (path, specification.get("label", path))
            for path, specification in sorted(
                hook_policy.items(),
                key=lambda item: item[1].get("label", item[0]),
            )
        ]

        if self.instance and self.instance.pk:
            if self.instance.func not in task_policy:
                self.fields["func"].choices.append(
                    (self.instance.func, f"Disallowed: {self.instance.func}")
                )
            if self.instance.hook and self.instance.hook not in hook_policy:
                self.fields["hook"].choices.append(
                    (self.instance.hook, f"Disallowed: {self.instance.hook}")
                )

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        self.instance.func = cleaned_data.get("func")
        self.instance.hook = cleaned_data.get("hook") or None
        self.instance.args = cleaned_data.get("args")
        self.instance.kwargs = cleaned_data.get("kwargs")
        self.instance.intended_date_kwarg = cleaned_data.get("intended_date_kwarg")
        try:
            validate_schedule(self.instance)
        except TaskPolicyError as error:
            raise forms.ValidationError(str(error)) from error
        return cleaned_data


@admin.action(description="Resubmit policy-approved tasks to queue")
def resubmit_allowed_tasks(model_admin, request, queryset):
    """Resubmit historical tasks only when current server policy permits them."""
    submitted = 0
    denied = 0
    for task in queryset:
        try:
            async_task(
                task.func,
                *task.args or (),
                hook=task.hook,
                group=task.group,
                cluster=task.cluster,
                **task.kwargs or {},
            )
        except TaskPolicyError:
            denied += 1
            continue
        submitted += 1
        if isinstance(model_admin, RestrictedFailAdmin):
            task.delete()
    if submitted:
        model_admin.message_user(
            request,
            f"Resubmitted {submitted} approved task(s).",
            level=messages.SUCCESS,
        )
    if denied:
        model_admin.message_user(
            request,
            f"Blocked {denied} task(s) that are not permitted by server policy.",
            level=messages.ERROR,
        )


class RestrictedTaskAdmin(django_q_admin.TaskAdmin):
    """Read-only successful task history with policy-aware resubmission."""

    actions = [resubmit_allowed_tasks]


class RestrictedFailAdmin(django_q_admin.FailAdmin):
    """Read-only failed task history with policy-aware resubmission."""

    actions = [resubmit_allowed_tasks]


class RestrictedScheduleAdmin(django_q_admin.ScheduleAdmin):
    """Django Q schedule admin constrained by server-side policy."""

    form = RestrictedScheduleForm
    readonly_fields = ("cluster", "intended_date_kwarg")


for django_q_model in (Schedule, Success, Failure):
    if admin.site.is_registered(django_q_model):
        admin.site.unregister(django_q_model)

admin.site.register(Schedule, RestrictedScheduleAdmin)
admin.site.register(Success, RestrictedTaskAdmin)
admin.site.register(Failure, RestrictedFailAdmin)
