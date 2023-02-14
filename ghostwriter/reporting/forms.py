"""This contains all the forms used by the Reporting application."""

# Standard Libraries
import re

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from crispy_forms.bootstrap import Accordion, AccordionGroup, FieldWithButtons
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    ButtonHolder,
    Column,
    Div,
    Field,
    Layout,
    Row,
    Submit,
)

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import ReportConfiguration
from ghostwriter.modules.custom_layout_object import SwitchToggle
from ghostwriter.reporting.models import (
    Evidence,
    Finding,
    FindingNote,
    LocalFindingNote,
    Report,
    ReportFindingLink,
    ReportTemplate,
    Severity,
)
from ghostwriter.rolodex.models import Project


class FindingForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.Finding`.
    """

    class Meta:
        model = Finding
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["title"].widget.attrs["placeholder"] = "Finding Title"
        self.fields["description"].widget.attrs["placeholder"] = "What is this ..."
        self.fields["impact"].widget.attrs["placeholder"] = "What is the impact ..."
        self.fields["cvss_score"].widget.attrs["placeholder"] = "What is the CVSS score ..."
        self.fields["cvss_vector"].widget.attrs["placeholder"] = "What is the CVSS vector ..."

        self.fields["mitigation"].widget.attrs["placeholder"] = "What needs to be done ..."
        self.fields["replication_steps"].widget.attrs["placeholder"] = "What is the category ..."
        self.fields["host_detection_techniques"].widget.attrs["placeholder"] = "How difficult is exploitation ..."
        self.fields["network_detection_techniques"].widget.attrs["placeholder"] = "Is the finding OPEN, ACCEPTED, or CLOSED ..."
        self.fields["references"].widget.attrs["placeholder"] = "Some useful links and references ..."
        self.fields["finding_guidance"].widget.attrs[
            "placeholder"
        ] = "When using this finding in a report be sure to include ..."
        self.fields["tags"].widget.attrs["placeholder"] = "ATT&CK:T1555, privesc, ..."
        self.fields["finding_type"].label = "Finding Type"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon search-icon">Categorization</h4>
                <hr />
                """
            ),
            Row(
                Column("title", css_class="form-group col-md-6 mb-0"),
                Column(
                    "tags",
                    css_class="form-group col-md-6 mb-0",
                ),
                css_class="form-row",
            ),
            Row(
                Column("finding_type", css_class="form-group col-md-6 mb-0"),
                Column("severity", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("cvss_score", css_class="form-group col-md-6 mb-0"),
                Column("cvss_vector", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Accordion(
                AccordionGroup(
                    "CVSS Calculator",
                    HTML(
                        """
                        <!-- CVSS -->
                        <!--
                        Copyright (c) 2015, FIRST.ORG, INC.
                        All rights reserved.

                        Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
                        following conditions are met:
                        1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
                        disclaimer.
                        2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
                        following disclaimer in the documentation and/or other materials provided with the distribution.
                        3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
                        products derived from this software without specific prior written permission.

                        THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
                        INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
                        DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
                        SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
                        SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
                        WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
                        OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
                        -->

                        <div class="form-row" style="text-align:center;display:inline-block">
                        <fieldset id="baseMetricGroup">
                        <legend id="baseMetricGroup_Legend" title="The Base Metric group represents the intrinsic  characteristics of a vulnerability that are constant over time and across user environments. Determine the vulnerable component and score Attack Vector, Attack Complexity, Privileges Required and User Interaction relative to this.">Base Score</legend>

                        <div class="column column-left">

                        <div class="metric">
                        <h3 id="AV_Heading" title="This metric reflects the context by which vulnerability exploitation is possible. The Base Score increases the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable component.">Attack Vector (AV)</h3>
                        <input name="AV" value="N" id="AV_N" type="radio" onclick="CVSSAutoCalc()"><label for="AV_N" id="AV_N_Label" title="A vulnerability exploitable with network access means the vulnerable component is bound to the network stack and the attacker's path is through OSI layer 3 (the network layer). Such a vulnerability is often termed &quot;remotely exploitable” and can be thought of as an attack being exploitable one or more network hops away.">Network (N)</label>
                        <input name="AV" value="A" id="AV_A" type="radio" onclick="CVSSAutoCalc()"><label for="AV_A" id="AV_A_Label" title="A vulnerability exploitable with adjacent network access means the vulnerable component is bound to the network stack, however the attack is limited to the same shared physical (e.g. Bluetooth, IEEE 802.11), or logical (e.g. local IP subnet) network, and cannot be performed across an OSI layer 3 boundary (e.g. a router).">Adjacent (A)</label>
                        <input name="AV" value="L" id="AV_L" type="radio" onclick="CVSSAutoCalc()"><label for="AV_L" id="AV_L_Label" title="A vulnerability exploitable with local access means that the vulnerable component is not bound to the network stack, and the attacker’s path is via read/write/execute capabilities. In some cases, the attacker may be logged in locally in order to exploit the vulnerability, otherwise, she may rely on User Interaction to execute a malicious file.">Local (L)</label>
                        <input name="AV" value="P" id="AV_P" type="radio" onclick="CVSSAutoCalc()"><label for="AV_P" id="AV_P_Label" title="A vulnerability exploitable with physical access requires the attacker to physically touch or manipulate the vulnerable component. Physical interaction may be brief or persistent.">Physical (P)</label>
                        </div>

                        <div class="metric">
                        <h3 id="AC_Heading" title="This metric describes the conditions beyond the attacker’s control that must exist in order to exploit the vulnerability. Such conditions may require the collection of more information about the target, the presence of certain system configuration settings, or computational exceptions.">Attack Complexity (AC)</h3>
                        <input name="AC" value="L" id="AC_L" type="radio" onclick="CVSSAutoCalc()"><label for="AC_L" id="AC_L_Label" title="Specialized access conditions or extenuating circumstances do not exist. An attacker can expect repeatable success against the vulnerable component.">Low (L)</label>
                        <input name="AC" value="H" id="AC_H" type="radio" onclick="CVSSAutoCalc()"><label for="AC_H" id="AC_H_Label" title="A successful attack depends on conditions beyond the attacker's control. That is, a successful attack cannot be accomplished at will, but requires the attacker to invest in some measurable amount of effort in preparation or execution against the vulnerable component before a successful attack can be expected. For example, a successful attack may require the attacker: to perform target-specific reconnaissance; to prepare the target environment to improve exploit reliability; or to inject herself into the logical network path between the target and the resource requested by the victim in order to read and/or modify network communications (e.g. a man in the middle attack).">High (H)</label>
                        </div>

                        <div class="metric">
                        <h3 id="PR_Heading" title="This metric describes the level of privileges an attacker must possess before successfully exploiting the vulnerability. This Base Score increases as fewer privileges are required.">Privileges Required (PR)</h3>
                        <input name="PR" value="N" id="PR_N" type="radio" onclick="CVSSAutoCalc()"><label for="PR_N" id="PR_N_Label" title="The attacker is unauthorized prior to attack, and therefore does not require any access to settings or files to carry out an attack.">None (N)</label>
                        <input name="PR" value="L" id="PR_L" type="radio" onclick="CVSSAutoCalc()"><label for="PR_L" id="PR_L_Label" title="The attacker is authorized with (i.e. requires) privileges that provide basic user capabilities that could normally affect only settings and files owned by a user. Alternatively, an attacker with Low privileges may have the ability to cause an impact only to non-sensitive resources.">Low (L)</label>
                        <input name="PR" value="H" id="PR_H" type="radio" onclick="CVSSAutoCalc()"><label for="PR_H" id="PR_H_Label" title="The attacker is authorized with (i.e. requires) privileges that provide significant (e.g. administrative) control over the vulnerable component that could affect component-wide settings and files.">High (H)</label>
                        </div>

                        <div class="metric">
                        <h3 id="UI_Heading" title="This metric captures the requirement for a user, other than the attacker, to participate in the successful compromise the vulnerable component. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner. The Base Score is highest when no user interaction is required.">User Interaction (UI)</h3>
                        <input name="UI" value="N" id="UI_N" type="radio" onclick="CVSSAutoCalc()"><label for="UI_N" id="UI_N_Label" title="The vulnerable system can be exploited without any interaction from any user.">None (N)</label>
                        <input name="UI" value="R" id="UI_R" type="radio" onclick="CVSSAutoCalc()"><label for="UI_R" id="UI_R_Label" title="Successful exploitation of this vulnerability requires a user to take some action before the vulnerability can be exploited.">Required (R)</label>
                        </div>

                        </div>


                        <div class="column column-right">

                        <div class="metric">
                        <h3 id="S_Heading" title="Does a successful attack impact a component other than the vulnerable component? If so, the Base Score increases and the Confidentiality, Integrity and Authentication metrics should be scored relative to the impacted component.">Scope (S)</h3>
                        <input name="S" value="U" id="S_U" type="radio" onclick="CVSSAutoCalc()"><label for="S_U" id="S_U_Label" title="An exploited vulnerability can only affect resources managed by the same authority. In this case the vulnerable component and the impacted component are the same.">Unchanged (U)</label>
                        <input name="S" value="C" id="S_C" type="radio" onclick="CVSSAutoCalc()"><label for="S_C" id="S_C_Label" title="An exploited vulnerability can affect resources beyond the authorization privileges intended by the vulnerable component. In this case the vulnerable component and the impacted component are different.">Changed (C)</label>
                        </div>

                        <div class="metric">
                        <h3 id="C_Heading" title="This metric measures the impact to the confidentiality of the information resources managed by a software component due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (C)</h3>
                        <input name="C" value="N" id="C_N" type="radio" onclick="CVSSAutoCalc()"><label for="C_N" id="C_N_Label" title="There is no loss of confidentiality within the impacted component.">None (N)</label>
                        <input name="C" value="L" id="C_L" type="radio" onclick="CVSSAutoCalc()"><label for="C_L" id="C_L_Label" title="There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is constrained. The information disclosure does not cause a direct, serious loss to the impacted component.">Low (L)</label>
                        <input name="C" value="H" id="C_H" type="radio" onclick="CVSSAutoCalc()"><label for="C_H" id="C_H_Label" title="There is total loss of confidentiality, resulting in all resources within the impacted component being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact.">High (H)</label>
                        </div>

                        <div class="metric">
                        <h3 id="I_Heading" title="This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information.">Integrity (I)</h3>
                        <input name="I" value="N" id="I_N" type="radio" onclick="CVSSAutoCalc()"><label for="I_N" id="I_N_Label" title="There is no loss of integrity within the impacted component.">None (N)</label>
                        <input name="I" value="L" id="I_L" type="radio" onclick="CVSSAutoCalc()"><label for="I_L" id="I_L_Label" title="Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is constrained. The data modification does not have a direct, serious impact on the impacted component.">Low (L)</label>
                        <input name="I" value="H" id="I_H" type="radio" onclick="CVSSAutoCalc()"><label for="I_H" id="I_H_Label" title="There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the impacted component. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the impacted component.">High (H)</label>
                        </div>

                        <div class="metric">
                        <h3 id="A_Heading" title="This metric measures the impact to the availability of the impacted component resulting from a successfully exploited vulnerability. It refers to the loss of availability of the impacted component itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of an impacted component.">Availability (A)</h3>
                        <input name="A" value="N" id="A_N" type="radio" onclick="CVSSAutoCalc()"><label for="A_N" id="A_N_Label" title="There is no impact to availability within the impacted component.">None (N)</label>
                        <input name="A" value="L" id="A_L" type="radio" onclick="CVSSAutoCalc()"><label for="A_L" id="A_L_Label" title="There is reduced performance or interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the impacted component are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the impacted component.">Low (L)</label>
                        <input name="A" value="H" id="A_H" type="radio" onclick="CVSSAutoCalc()"><label for="A_H" id="A_H_Label" title="There is total loss of availability, resulting in the attacker being able to fully deny access to resources in the impacted component; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the impacted component (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).">High (H)</label>
                        </div>

                        </div>


                        <div id="scoreRating" class="scoreRating">
                        <span id="baseMetricScore"></span>
                        <span id="baseSeverity">Select values for all base metrics</span>
                        </div>
                        </fieldset>
                        </div>
                        """
                    ),
                    active=False,
                    template="accordion_group.html",
                ),
            ),
            HTML(
                """
                <h4 class="icon pencil-icon">General Information</h4>
                <hr />
                """
            ),
            Field("description"),
            Field("impact"),
            HTML(
                """
                <h4 class="icon shield-icon">Defense</h4>
                <hr />
                """
            ),
            Field("mitigation"),
            Field("replication_steps"),
            Field("host_detection_techniques"),
            Field(
                "network_detection_techniques",
            ),
            HTML(
                """
                <h4 class="icon link-icon">Reference Links</h4>
                <hr />
                """
            ),
            "references",
            "finding_guidance",
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )


class ReportForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.Report` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = Report
        exclude = ("creation", "last_update", "created_by", "complete")

    def __init__(self, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_instance = project
        # Limit the list to just projects not marked as complete
        active_projects = Project.objects.filter(complete=False).order_by("-start_date", "client", "project_type")
        if active_projects:
            self.fields["project"].empty_label = "-- Select an Active Project --"
        else:
            self.fields["project"].empty_label = "-- No Active Projects --"
        self.fields["project"].queryset = active_projects
        self.fields[
            "project"
        ].label_from_instance = lambda obj: f"{obj.start_date} {obj.client.name} {obj.project_type} ({obj.codename})"
        self.fields["docx_template"].label = "DOCX Template"
        self.fields["pptx_template"].label = "PPTX Template"
        self.fields["docx_template"].required = False
        self.fields["pptx_template"].required = False
        self.fields["tags"].widget.attrs["placeholder"] = "draft, QA2, ..."
        self.fields["title"].widget.attrs["placeholder"] = "Red Team Report for Project Foo"

        report_config = ReportConfiguration.get_solo()
        self.fields["docx_template"].initial = report_config.default_docx_template
        self.fields["pptx_template"].initial = report_config.default_pptx_template
        self.fields["docx_template"].empty_label = "-- Pick a Word Template --"
        self.fields["pptx_template"].empty_label = "-- Pick a PowerPoint Template --"

        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("title", css_class="form-group col-md-6 mb-0"),
                Column("tags", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            "project",
            HTML(
                """
                <h4 class="icon file-icon">Assign Templates</h4>
                <hr />
                <p>Select a template to use for the Word and PowerPoint versions of the report.
                If you do not select a template, the global default template will be used.
                If a default is not configured, you will need to select one here or on the report page.</p>
                """
            ),
            Row(
                Column("docx_template", css_class="form-group col-md-6 mb-0"),
                Column("pptx_template", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )


class ReportFindingLinkUpdateForm(forms.ModelForm):
    """
    Update an individual :model:`reporting.ReportFindingLink` associated with an
    individual :model:`reporting.Report`.
    """

    class Meta:
        model = ReportFindingLink
        exclude = (
            "report",
            "position",
            "finding_guidance",
            "added_as_blank",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        evidence_upload_url = reverse(
            "reporting:upload_evidence_modal",
            kwargs={"pk": self.instance.id, "modal": "modal"},
        )
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["affected_entities"].widget.attrs["placeholder"] = "List of Hostnames or IP Addresses"
        self.fields["title"].widget.attrs["placeholder"] = "Finding Title"
        self.fields["description"].widget.attrs["placeholder"] = "What is this ..."
        self.fields["impact"].widget.attrs["placeholder"] = "What is the impact ..."

        self.fields["cvss_score"].widget.attrs["placeholder"] = "What is the CVSS score ..."
        self.fields["cvss_vector"].widget.attrs["placeholder"] = "What is the CVSS vector ..."
        self.fields["mitigation"].widget.attrs["placeholder"] = "What needs to be done ..."
        self.fields["replication_steps"].widget.attrs["placeholder"] = "What is the category ..."
        self.fields["host_detection_techniques"].widget.attrs["placeholder"] = "How difficult is exploitation ..."
        self.fields["network_detection_techniques"].widget.attrs["placeholder"] = "Is the finding OPEN, ACCEPTED, or CLOSED..."
        self.fields["references"].widget.attrs["placeholder"] = "Some useful links and references ..."
        self.fields["tags"].widget.attrs["placeholder"] = "ATT&CK:T1555, privesc, ..."
        self.fields["finding_type"].label = "Finding Type"
        self.fields["assigned_to"].label = "Assigned Editor"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_id = "report-finding-form"
        self.helper.attrs = {"evidence-upload-modal-url": evidence_upload_url}
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon search-icon">Categorization</h4>
                <hr />
                """
            ),
            Row(
                Column("title", css_class="form-group col-md-12 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("assigned_to", css_class="form-group col-md-6 mb-0"),
                Column("tags", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("finding_type", css_class="form-group col-md-6 mb-0"),
                Column("severity", css_class="form-group col-md-6 mb-0"),
            ),
            Row(
                Column("cvss_score", css_class="form-group col-md-6 mb-0"),
                Column("cvss_vector", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Accordion(
                AccordionGroup(
                    "CVSS Calculator",
                    HTML(
                        """
                        <!-- CVSS -->
                        <!--
                        Copyright (c) 2015, FIRST.ORG, INC.
                        All rights reserved.

                        Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
                        following conditions are met:
                        1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
                        disclaimer.
                        2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
                        following disclaimer in the documentation and/or other materials provided with the distribution.
                        3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
                        products derived from this software without specific prior written permission.

                        THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
                        INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
                        DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
                        SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
                        SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
                        WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
                        OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
                        -->

                        <div class="form-row" style="text-align:center;display:inline-block">
                        <fieldset id="baseMetricGroup">
                        <legend id="baseMetricGroup_Legend" title="The Base Metric group represents the intrinsic  characteristics of a vulnerability that are constant over time and across user environments. Determine the vulnerable component and score Attack Vector, Attack Complexity, Privileges Required and User Interaction relative to this.">Base Score</legend>

                        <div class="column column-left">

                        <div class="metric">
                        <h3 id="AV_Heading" title="This metric reflects the context by which vulnerability exploitation is possible. The Base Score increases the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable component.">Attack Vector (AV)</h3>
                        <input name="AV" value="N" id="AV_N" type="radio" onclick="CVSSAutoCalc()"><label for="AV_N" id="AV_N_Label" title="A vulnerability exploitable with network access means the vulnerable component is bound to the network stack and the attacker's path is through OSI layer 3 (the network layer). Such a vulnerability is often termed &quot;remotely exploitable” and can be thought of as an attack being exploitable one or more network hops away.">Network (N)</label>
                        <input name="AV" value="A" id="AV_A" type="radio" onclick="CVSSAutoCalc()"><label for="AV_A" id="AV_A_Label" title="A vulnerability exploitable with adjacent network access means the vulnerable component is bound to the network stack, however the attack is limited to the same shared physical (e.g. Bluetooth, IEEE 802.11), or logical (e.g. local IP subnet) network, and cannot be performed across an OSI layer 3 boundary (e.g. a router).">Adjacent (A)</label>
                        <input name="AV" value="L" id="AV_L" type="radio" onclick="CVSSAutoCalc()"><label for="AV_L" id="AV_L_Label" title="A vulnerability exploitable with local access means that the vulnerable component is not bound to the network stack, and the attacker’s path is via read/write/execute capabilities. In some cases, the attacker may be logged in locally in order to exploit the vulnerability, otherwise, she may rely on User Interaction to execute a malicious file.">Local (L)</label>
                        <input name="AV" value="P" id="AV_P" type="radio" onclick="CVSSAutoCalc()"><label for="AV_P" id="AV_P_Label" title="A vulnerability exploitable with physical access requires the attacker to physically touch or manipulate the vulnerable component. Physical interaction may be brief or persistent.">Physical (P)</label>
                        </div>

                        <div class="metric">
                        <h3 id="AC_Heading" title="This metric describes the conditions beyond the attacker’s control that must exist in order to exploit the vulnerability. Such conditions may require the collection of more information about the target, the presence of certain system configuration settings, or computational exceptions.">Attack Complexity (AC)</h3>
                        <input name="AC" value="L" id="AC_L" type="radio" onclick="CVSSAutoCalc()"><label for="AC_L" id="AC_L_Label" title="Specialized access conditions or extenuating circumstances do not exist. An attacker can expect repeatable success against the vulnerable component.">Low (L)</label>
                        <input name="AC" value="H" id="AC_H" type="radio" onclick="CVSSAutoCalc()"><label for="AC_H" id="AC_H_Label" title="A successful attack depends on conditions beyond the attacker's control. That is, a successful attack cannot be accomplished at will, but requires the attacker to invest in some measurable amount of effort in preparation or execution against the vulnerable component before a successful attack can be expected. For example, a successful attack may require the attacker: to perform target-specific reconnaissance; to prepare the target environment to improve exploit reliability; or to inject herself into the logical network path between the target and the resource requested by the victim in order to read and/or modify network communications (e.g. a man in the middle attack).">High (H)</label>
                        </div>

                        <div class="metric">
                        <h3 id="PR_Heading" title="This metric describes the level of privileges an attacker must possess before successfully exploiting the vulnerability. This Base Score increases as fewer privileges are required.">Privileges Required (PR)</h3>
                        <input name="PR" value="N" id="PR_N" type="radio" onclick="CVSSAutoCalc()"><label for="PR_N" id="PR_N_Label" title="The attacker is unauthorized prior to attack, and therefore does not require any access to settings or files to carry out an attack.">None (N)</label>
                        <input name="PR" value="L" id="PR_L" type="radio" onclick="CVSSAutoCalc()"><label for="PR_L" id="PR_L_Label" title="The attacker is authorized with (i.e. requires) privileges that provide basic user capabilities that could normally affect only settings and files owned by a user. Alternatively, an attacker with Low privileges may have the ability to cause an impact only to non-sensitive resources.">Low (L)</label>
                        <input name="PR" value="H" id="PR_H" type="radio" onclick="CVSSAutoCalc()"><label for="PR_H" id="PR_H_Label" title="The attacker is authorized with (i.e. requires) privileges that provide significant (e.g. administrative) control over the vulnerable component that could affect component-wide settings and files.">High (H)</label>
                        </div>

                        <div class="metric">
                        <h3 id="UI_Heading" title="This metric captures the requirement for a user, other than the attacker, to participate in the successful compromise the vulnerable component. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner. The Base Score is highest when no user interaction is required.">User Interaction (UI)</h3>
                        <input name="UI" value="N" id="UI_N" type="radio" onclick="CVSSAutoCalc()"><label for="UI_N" id="UI_N_Label" title="The vulnerable system can be exploited without any interaction from any user.">None (N)</label>
                        <input name="UI" value="R" id="UI_R" type="radio" onclick="CVSSAutoCalc()"><label for="UI_R" id="UI_R_Label" title="Successful exploitation of this vulnerability requires a user to take some action before the vulnerability can be exploited.">Required (R)</label>
                        </div>

                        </div>


                        <div class="column column-right">

                        <div class="metric">
                        <h3 id="S_Heading" title="Does a successful attack impact a component other than the vulnerable component? If so, the Base Score increases and the Confidentiality, Integrity and Authentication metrics should be scored relative to the impacted component.">Scope (S)</h3>
                        <input name="S" value="U" id="S_U" type="radio" onclick="CVSSAutoCalc()"><label for="S_U" id="S_U_Label" title="An exploited vulnerability can only affect resources managed by the same authority. In this case the vulnerable component and the impacted component are the same.">Unchanged (U)</label>
                        <input name="S" value="C" id="S_C" type="radio" onclick="CVSSAutoCalc()"><label for="S_C" id="S_C_Label" title="An exploited vulnerability can affect resources beyond the authorization privileges intended by the vulnerable component. In this case the vulnerable component and the impacted component are different.">Changed (C)</label>
                        </div>

                        <div class="metric">
                        <h3 id="C_Heading" title="This metric measures the impact to the confidentiality of the information resources managed by a software component due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (C)</h3>
                        <input name="C" value="N" id="C_N" type="radio" onclick="CVSSAutoCalc()"><label for="C_N" id="C_N_Label" title="There is no loss of confidentiality within the impacted component.">None (N)</label>
                        <input name="C" value="L" id="C_L" type="radio" onclick="CVSSAutoCalc()"><label for="C_L" id="C_L_Label" title="There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is constrained. The information disclosure does not cause a direct, serious loss to the impacted component.">Low (L)</label>
                        <input name="C" value="H" id="C_H" type="radio" onclick="CVSSAutoCalc()"><label for="C_H" id="C_H_Label" title="There is total loss of confidentiality, resulting in all resources within the impacted component being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact.">High (H)</label>
                        </div>

                        <div class="metric">
                        <h3 id="I_Heading" title="This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information.">Integrity (I)</h3>
                        <input name="I" value="N" id="I_N" type="radio" onclick="CVSSAutoCalc()"><label for="I_N" id="I_N_Label" title="There is no loss of integrity within the impacted component.">None (N)</label>
                        <input name="I" value="L" id="I_L" type="radio" onclick="CVSSAutoCalc()"><label for="I_L" id="I_L_Label" title="Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is constrained. The data modification does not have a direct, serious impact on the impacted component.">Low (L)</label>
                        <input name="I" value="H" id="I_H" type="radio" onclick="CVSSAutoCalc()"><label for="I_H" id="I_H_Label" title="There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the impacted component. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the impacted component.">High (H)</label>
                        </div>

                        <div class="metric">
                        <h3 id="A_Heading" title="This metric measures the impact to the availability of the impacted component resulting from a successfully exploited vulnerability. It refers to the loss of availability of the impacted component itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of an impacted component.">Availability (A)</h3>
                        <input name="A" value="N" id="A_N" type="radio" onclick="CVSSAutoCalc()"><label for="A_N" id="A_N_Label" title="There is no impact to availability within the impacted component.">None (N)</label>
                        <input name="A" value="L" id="A_L" type="radio" onclick="CVSSAutoCalc()"><label for="A_L" id="A_L_Label" title="There is reduced performance or interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the impacted component are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the impacted component.">Low (L)</label>
                        <input name="A" value="H" id="A_H" type="radio" onclick="CVSSAutoCalc()"><label for="A_H" id="A_H_Label" title="There is total loss of availability, resulting in the attacker being able to fully deny access to resources in the impacted component; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the impacted component (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).">High (H)</label>
                        </div>

                        </div>


                        <div id="scoreRating" class="scoreRating">
                        <span id="baseMetricScore"></span>
                        <span id="baseSeverity">Select values for all base metrics</span>
                        </div>
                        </fieldset>
                        </div>
                        """
                    ),
                    active=False,
                    template="accordion_group.html",
                ),
            ),
            HTML(
                """
                <h4 class="icon list-icon">Affected Entities</h4>
                <hr />
                """
            ),
            Field("affected_entities", css_class="enable-evidence-upload"),
            HTML(
                """
                <h4 class="icon pencil-icon">General Information</h4>
                <hr />
                """
            ),
            Field("description", css_class="enable-evidence-upload"),
            Field("impact", css_class="enable-evidence-upload"),
            HTML(
                """
                <h4 class="icon shield-icon">Defense</h4>
                <hr />
                """
            ),
            Field("mitigation", css_class="enable-evidence-upload"),
            Field("replication_steps", css_class="enable-evidence-upload"),
            Field("host_detection_techniques", css_class="enable-evidence-upload"),
            Field(
                "network_detection_techniques",
                css_class="enable-evidence-upload",
            ),
            HTML(
                """
                <h4 class="icon link-icon">Reference Links</h4>
                <hr />
                """
            ),
            Field("references", css_class="enable-evidence-upload"),
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel
                    </button>
                    """
                ),
            ),
        )


class EvidenceForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.Evidence` associated with an individual
    :model:`reporting.ReportFindingLink`.
    """

    class Meta:
        model = Evidence
        fields = (
            "friendly_name",
            "document",
            "description",
            "caption",
            "tags",
        )
        widgets = {
            "document": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.is_modal = kwargs.pop("is_modal", None)
        self.evidence_queryset = kwargs.pop("evidence_queryset", None)
        super().__init__(*args, **kwargs)
        self.fields["caption"].required = True
        self.fields["caption"].widget.attrs["autocomplete"] = "off"
        self.fields["caption"].widget.attrs["placeholder"] = "Report Caption"
        self.fields["tags"].widget.attrs["placeholder"] = "ATT&CK:T1555, privesc, ..."
        self.fields["friendly_name"].required = True
        self.fields["friendly_name"].widget.attrs["autocomplete"] = "off"
        self.fields["friendly_name"].widget.attrs["placeholder"] = "Friendly Name"
        self.fields["description"].widget.attrs["placeholder"] = "Brief Description or Note"
        self.fields["document"].label = ""
        # Don't set form buttons for a modal pop-up
        if self.is_modal:
            submit = None
            cancel_button = None
        else:
            submit = Submit("submit-button", "Submit", css_class="btn btn-primary col-md-4")
            cancel_button = HTML(
                """
                <button onclick="window.location.href='{{ cancel_link }}'"
                class="btn btn-outline-secondary col-md-4" type="button">Cancel
                </button>
                """
            )
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_errors = False
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.form_id = "evidence-upload-form"
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon signature-icon">Report Information</h4>
                <hr>
                <p>The friendly name is used to reference this evidence in the report and the caption appears below
                the figures in the generated reports.</p>
                """
            ),
            Row(
                Column("friendly_name", css_class="form-group col-md-6 mb-0"),
                Column("tags", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            "caption",
            "description",
            HTML(
                """
                <h4 class="icon upload-icon">Upload a File</h4>
                <hr>
                <p>Attach text evidence (*.txt, *.log, or *.md) or image evidence (*.png, *.jpg, or *.jpeg).
                Previews for images will appear below.</p>
                <p><span class="bold">Tip:</span> You copy and paste an image (file or screenshot) into this page!
                Make sure to <span class="italic">click outside of any form fields first</span>.</p>
                <div id="findingPreview" class="pb-3"></div>
                """
            ),
            Div(
                Field(
                    "document",
                    id="id_document",
                    css_class="custom-file-input",
                ),
                HTML(
                    """
                    <label id="filename" class="custom-file-label" for="customFile">
                    Click here to select or drag and drop your file...</label>
                    """
                ),
                css_class="custom-file",
            ),
            ButtonHolder(submit, cancel_button, css_class="mt-3"),
        )

    def clean_document(self):
        document = self.cleaned_data["document"]
        # Check if evidence file is missing
        if not document:
            raise ValidationError(
                _("You must provide an evidence file"),
                "incomplete",
            )
        return document

    def clean_friendly_name(self):
        friendly_name = self.cleaned_data["friendly_name"]
        if self.evidence_queryset:
            # Check if provided name has already been used for another file for this report
            report_queryset = self.evidence_queryset.values_list("id", "friendly_name")
            for evidence in report_queryset:
                if friendly_name == evidence[1] and not self.instance.id == evidence[0]:
                    raise ValidationError(
                        _("This friendly name has already been used for a file attached to this finding."),
                        "duplicate",
                    )
        return friendly_name


class FindingNoteForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.FindingNote` associated with an individual
    :model:`reporting.Finding`.
    """

    class Meta:
        model = FindingNote
        fields = ("note",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div("note"),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel
                    </button>
                    """
                ),
            ),
        )

    def clean_note(self):
        note = self.cleaned_data["note"]
        # Check if note is empty
        if not note:
            raise ValidationError(
                _("You must provide some content for the note"),
                code="required",
            )
        return note


class LocalFindingNoteForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.LocalFindingNote` associated with an individual
    :model:`ReportFindingLink.
    """

    class Meta:
        model = LocalFindingNote
        fields = ("note",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div("note"),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel
                    </button>
                    """
                ),
            ),
        )

    def clean_note(self):
        note = self.cleaned_data["note"]
        # Check if note is empty
        if not note:
            raise ValidationError(
                _("You must provide some content for the note"),
                code="required",
            )
        return note


class ReportTemplateForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.ReportTemplate`.
    """

    class Meta:
        model = ReportTemplate
        exclude = ("upload_date", "last_update", "lint_result", "uploaded_by")
        widgets = {
            "document": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["document"].label = ""
        self.fields["document"].widget.attrs["class"] = "custom-file-input"
        self.fields["name"].widget.attrs["placeholder"] = "Default Red Team Report"
        self.fields["description"].widget.attrs["placeholder"] = "Use this template for any red team work unless ..."
        self.fields["changelog"].widget.attrs["placeholder"] = "Track Template Modifications"
        self.fields["doc_type"].empty_label = "-- Select a Matching Filetype --"
        self.fields["client"].empty_label = "-- Attach to a Client (Optional) --"
        self.fields["tags"].widget.attrs["placeholder"] = "language:en_US, cvss, ..."
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon file-icon">Template Information</h4>
                <hr>
                <p>The name appears in the template dropdown menus in reports.</p>
                """
            ),
            Row(
                Column("name", css_class="form-group col-md-6 mb-0"),
                Column("tags", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("doc_type", css_class="form-group col-md-6 mb-0"),
                Column("client", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column(
                    SwitchToggle(
                        "protected",
                    ),
                    css_class="form-group col-md-6 mb-0",
                ),
                Column(
                    SwitchToggle(
                        "landscape",
                    ),
                    css_class="form-group col-md-6 mb-0",
                ),
                css_class="form-row pb-2",
            ),
            "description",
            HTML(
                """
                <h4 class="icon upload-icon">Upload a File</h4>
                <hr>
                <p>Attach a document that matches your selected filetype to use as a report template</p>
                """
            ),
            Div(
                "document",
                HTML(
                    """
                    <label id="filename" class="custom-file-label" for="customFile">Choose template file...</label>
                    """
                ),
                css_class="custom-file",
            ),
            "changelog",
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel
                    </button>
                    """
                ),
            ),
        )

    def clean_document(self):
        document = self.cleaned_data["document"]
        # Check if template file is missing
        if not document:
            raise ValidationError(
                _("You must provide a template file"),
                "incomplete",
            )
        return document


class SelectReportTemplateForm(forms.ModelForm):
    """
    Modify the ``docx_template`` and ``pptx_template`` values of an individual
    :model:`reporting.Report`.
    """

    class Meta:
        model = Report
        fields = ("docx_template", "pptx_template")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["docx_template"].help_text = None
        self.fields["pptx_template"].help_text = None
        self.fields["docx_template"].empty_label = "-- Select a DOCX Template --"
        self.fields["pptx_template"].empty_label = "-- Select a PPTX Template --"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_method = "post"
        self.helper.form_id = "report-template-swap-form"
        self.helper.form_tag = True
        self.helper.form_action = reverse("reporting:ajax_swap_report_template", kwargs={"pk": self.instance.id})
        self.helper.layout = Layout(
            Row(
                Column(
                    HTML(
                        """
                        <p class="text-left mt-1">Template for DOCX</p>
                        """
                    ),
                    css_class="col-md-2",
                ),
                Column(
                    FieldWithButtons(
                        "docx_template",
                        HTML(
                            """
                            <a
                                class="btn btn-default word-btn js-generate-report"
                                type="button"
                                href="{% url 'reporting:generate_docx' report.id %}"
                                data-toggle="tooltip"
                                data-placement="top"
                                title="Generate a DOCX report"
                            >
                            </a>
                            """
                        ),
                    ),
                    css_class="col-md-4",
                ),
                css_class="justify-content-md-center",
            ),
            Row(
                Column(
                    HTML(
                        """
                        <p class="text-left mt-1">Template for PPTX</p>
                        """
                    ),
                    css_class="col-md-2",
                ),
                Column(
                    FieldWithButtons(
                        "pptx_template",
                        HTML(
                            """
                            <a
                                class="btn btn-default pptx-btn"
                                type="button"
                                href="{% url 'reporting:generate_pptx' report.id %}"
                                data-toggle="tooltip"
                                data-placement="top"
                                title="Generate a PPTX report"
                            >
                            </a>
                            """
                        ),
                    ),
                    css_class="col-md-4",
                ),
                css_class="justify-content-md-center",
            ),
            HTML(
                """
                <p class="mb-2">Other report types do not use templates:</p>
                <div class="btn-group">
                    <a class="btn btn-default excel-btn-icon" href="{% url 'reporting:generate_xlsx' report.id %}"
                    data-toggle="tooltip" data-placement="top" title="Generate an XLSX report"></i></a>
                    <a class="btn btn-default json-btn-icon" href="{% url 'reporting:generate_json' report.id %}"
                    data-toggle="tooltip" data-placement="top" title="Generate exportable JSON"></a>
                    <a class="btn btn-default archive-btn-icon js-generate-report"
                    href="{% url 'reporting:generate_all' report.id %}" data-toggle="tooltip" data-placement="top"
                    title="Generate and package all report types and evidence in a Zip"></a>
                </div>
                """
            ),
        )


class SeverityForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.Severity`.
    """

    class Meta:
        model = Severity
        fields = "__all__"

    def clean_color(self, *args, **kwargs):
        color = self.cleaned_data["color"]
        regex = "^(?:[0-9a-fA-F]{1,2}){3}$"
        valid_hex_regex = re.compile(regex)
        if color:
            if "#" in color:
                raise ValidationError(
                    _("Do not include the # symbol in the color field."),
                    "invalid",
                )
            if len(color) < 6:
                raise ValidationError(
                    _("Your hex color code should be six characters in length."),
                    "invalid",
                )
            if not re.search(valid_hex_regex, color):
                raise ValidationError(
                    _("Please enter a valid hex color, three pairs of characters using A-F and 0-9 (e.g., 7A7A7A)."),
                    "invalid",
                )

        return color
