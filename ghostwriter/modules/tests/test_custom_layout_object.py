# Standard Libraries
from unittest.mock import Mock, patch

# Django Imports
from django.test import SimpleTestCase

# Ghostwriter Libraries
from ghostwriter.modules.custom_layout_object import CustomTab


class CustomTabTests(SimpleTestCase):
    """Collection of tests for custom crispy layout objects."""

    def test_custom_tab_keeps_name_out_of_layout_fields(self):
        tab = CustomTab("Project Information", "client", "codename", css_id="project")

        self.assertEqual(tab.name, "Project Information")
        self.assertEqual(tab.fields, ["client", "codename"])
        self.assertNotIn("Project Information", tab.fields)

    def test_custom_tab_uses_separate_hash_and_pane_ids(self):
        tab = CustomTab("Project Information", "client", css_id="project")

        self.assertEqual(tab.tab_hash, "#project")
        self.assertEqual(tab.css_id, "tab-pane-project")

    def test_custom_tab_derives_ids_from_name_when_css_id_is_omitted(self):
        tab = CustomTab("Extra Fields", "extra_fields")

        self.assertEqual(tab.tab_hash, "#extra-fields")
        self.assertEqual(tab.css_id, "tab-pane-extra-fields")

    @patch("crispy_forms.bootstrap.Container.render", return_value="")
    def test_extra_fields_tab_renders_spec_count_badge(self, _render):
        tab = CustomTab("Extra Fields", "extra_fields")
        form = Mock()
        form.fields = {"extra_fields": Mock(specs=[Mock(), Mock(), Mock()])}

        tab.render(form, Mock())
        link = tab.render_link()

        self.assertIn('<span class="tab-count-badge">3</span>', link)
