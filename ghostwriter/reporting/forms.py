"""This contains all the forms used by the Reporting application."""

# Standard Libraries
import re

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from crispy_forms.bootstrap import Accordion, AccordionGroup, TabHolder, Tab, FieldWithButtons
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
from ghostwriter.api.utils import get_client_list, get_project_list
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
    """Save an individual :model:`reporting.Finding`."""

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
        self.fields["replication_steps"].widget.attrs["placeholder"] = "How to reproduce/find this issue ..."
        self.fields["host_detection_techniques"].widget.attrs["placeholder"] = "How to detect it on an endpoint ..."
        self.fields["network_detection_techniques"].widget.attrs["placeholder"] = "How to detect it on a network ..."
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
                    TabHolder(
                        Tab(
                            "CVSS v3.0",
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
                                <input name="AV" value="L" id="AV_L" type="radio" onclick="CVSSAutoCalc()"><label for="AV_L" id="AV_L_Label" title="A vulnerability exploitable with local access means that the vulnerable component is not bound to the network stack, and the attacker's path is via read/write/execute capabilities. In some cases, the attacker may be logged in locally in order to exploit the vulnerability, otherwise, she may rely on User Interaction to execute a malicious file.">Local (L)</label>
                                <input name="AV" value="P" id="AV_P" type="radio" onclick="CVSSAutoCalc()"><label for="AV_P" id="AV_P_Label" title="A vulnerability exploitable with physical access requires the attacker to physically touch or manipulate the vulnerable component. Physical interaction may be brief or persistent.">Physical (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="AC_Heading" title="This metric describes the conditions beyond the attacker's control that must exist in order to exploit the vulnerability. Such conditions may require the collection of more information about the target, the presence of certain system configuration settings, or computational exceptions.">Attack Complexity (AC)</h3>
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
                        ),
                        Tab(
                            "CVSS v4.0",
                            HTML(
                                """
                                <!--
                                Copyright (c) 2023 FIRST.ORG, Inc., Red Hat, and contributors

                                Redistribution and use in source and binary forms, with or without
                                modification, are permitted provided that the following conditions are met:

                                1. Redistributions of source code must retain the above copyright notice, this
                                   list of conditions and the following disclaimer.

                                2. Redistributions in binary form must reproduce the above copyright notice,
                                   this list of conditions and the following disclaimer in the documentation
                                   and/or other materials provided with the distribution.

                                THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
                                AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
                                IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
                                DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
                                FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
                                DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
                                SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
                                CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
                                OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
                                OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
                                -->
                                <div style="height: 500px; overflow: auto;">
                                <fieldset id="baseMetricGroup">
                                <legend id="baseMetricGroup_Legend" title="This category is usually filled by the supplier">Base Metrics</legend>

                                <h5 id="Exploitability_Metrics" title="">Exploitability Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_AV_Heading" title="This metric reflects the context by which vulnerability exploitation is possible. This metric value (and consequently the resulting severity) will be larger the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable system. The assumption is that the number of potential attackers for a vulnerability that could be exploited from across a network is larger than the number of potential attackers that could exploit a vulnerability requiring physical access to a device, and therefore warrants a greater severity.">Attack Vector (AV)</h3>
                                <input name="v4_AV" value="N" id="v4_AV_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AV_N" id="v4_AV_N_Label" title="The vulnerable system is bound to the network stack and the set of possible attackers extends beyond the other options listed below, up to and including the entire Internet. Such a vulnerability is often termed “remotely exploitable” and can be thought of as an attack being exploitable at the protocol level one or more network hops away (e.g., across one or more routers).">Network (N)</label>
                                <input name="v4_AV" value="A" id="v4_AV_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AV_A" id="v4_AV_A_Label" title="The vulnerable system is bound to a protocol stack, but the attack is limited at the protocol level to a logically adjacent topology. This can mean an attack must be launched from the same shared proximity (e.g., Bluetooth, NFC, or IEEE 802.11) or logical network (e.g., local IP subnet), or from within a secure or otherwise limited administrative domain (e.g., MPLS, secure VPN within an administrative network zone).">Adjacent (A)</label>
                                <input name="v4_AV" value="L" id="v4_AV_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AV_L" id="v4_AV_L_Label" title="The vulnerable system is not bound to the network stack and the attacker's path is via read/write/execute capabilities. Either the attacker exploits the vulnerability by accessing the target system locally (e.g., keyboard, console), or through terminal emulation (e.g., SSH); or the attacker relies on User Interaction by another person to perform actions required to exploit the vulnerability (e.g., using social engineering techniques to trick a legitimate user into opening a malicious document).">Local (L)</label>
                                <input name="v4_AV" value="P" id="v4_AV_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AV_P" id="v4_AV_P_Label" title="The attack requires the attacker to physically touch or manipulate the vulnerable system. Physical interaction may be brief (e.g., evil maid attack) or persistent.">Physical (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_AC_Heading" title="This metric captures measurable actions that must be taken by the attacker to actively evade or circumvent existing built-in security-enhancing conditions in order to obtain a working exploit. These are conditions whose primary purpose is to increase security and/or increase exploit engineering complexity. A vulnerability exploitable without a target-specific variable has a lower complexity than a vulnerability that would require non-trivial customization. This metric is meant to capture security mechanisms utilized by the vulnerable system.">Attack Complexity (AC)</h3>
                                <input name="v4_AC" value="L" id="v4_AC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AC_L" id="v4_AC_L_Label" title="The attacker must take no measurable action to exploit the vulnerability. The attack requires no target-specific circumvention to exploit the vulnerability. An attacker can expect repeatable success against the vulnerable system.">Low (L)</label>
                                <input name="v4_AC" value="H" id="v4_AC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AC_H" id="v4_AC_H_Label" title="The successful attack depends on the evasion or circumvention of security-enhancing techniques in place that would otherwise hinder the attack. These include: Evasion of exploit mitigation techniques, for example, circumvention of address space randomization (ASLR) or data execution prevention (DEP) must be performed for the attack to be successful; Obtaining target-specific secrets. The attacker must gather some target-specific secret before the attack can be successful. A secret is any piece of information that cannot be obtained through any amount of reconnaissance. To obtain the secret the attacker must perform additional attacks or break otherwise secure measures (e.g. knowledge of a secret key may be needed to break a crypto channel). This operation must be performed for each attacked target.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_AT_Heading" title="This metric captures the prerequisite deployment and execution conditions or variables of the vulnerable system that enable the attack. These differ from security-enhancing techniques/technologies (ref Attack Complexity) as the primary purpose of these conditions is not to explicitly mitigate attacks, but rather, emerge naturally as a consequence of the deployment and execution of the vulnerable system.">Attack Requirements (AT)</h3>
                                <input name="v4_AT" value="N" id="v4_AT_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AT_N" id="v4_AT_N_Label" title="The successful attack does not depend on the deployment and execution conditions of the vulnerable system. The attacker can expect to be able to reach the vulnerability and execute the exploit under all or most instances of the vulnerability.">None (N)</label>
                                <input name="v4_AT" value="L" id="v4_AT_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AT_P" id="v4_AT_P_Label" title="The successful attack depends on the presence of specific deployment and execution conditions of the vulnerable system that enable the attack. These include: a race condition must be won to successfully exploit the vulnerability (the successfulness of the attack is conditioned on execution conditions that are not under full control of the attacker, or the attack may need to be launched multiple times against a single target before being successful); the attacker must inject themselves into the logical network path between the target and the resource requested by the victim (e.g. vulnerabilities requiring an on-path attacker).">Present (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_PR_Heading" title="This metric describes the level of privileges an attacker must possess prior to successfully exploiting the vulnerability. The method by which the attacker obtains privileged credentials prior to the attack (e.g., free trial accounts), is outside the scope of this metric. Generally, self-service provisioned accounts do not constitute a privilege requirement if the attacker can grant themselves privileges as part of the attack.">Privileges Required (PR)</h3>
                                <input name="v4_PR" value="N" id="v4_PR_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_PR_N" id="v4_PR_N_Label" title="The attacker is unauthorized prior to attack, and therefore does not require any access to settings or files of the vulnerable system to carry out an attack.">None (N)</label>
                                <input name="v4_PR" value="L" id="v4_PR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_PR_L" id="v4_PR_L_Label" title="The attacker requires privileges that provide basic capabilities that are typically limited to settings and resources owned by a single low-privileged user. Alternatively, an attacker with Low privileges has the ability to access only non-sensitive resources.">Low (L)</label>
                                <input name="v4_PR" value="H" id="v4_PR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_PR_H" id="v4_PR_H_Label" title="The attacker requires privileges that provide significant (e.g., administrative) control over the vulnerable system allowing full access to the vulnerable system's settings and files.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_UI_Heading" title="This metric captures the requirement for a human user, other than the attacker, to participate in the successful compromise of the vulnerable system. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner.">User Interaction (UI)</h3>
                                <input name="v4_UI" value="N" id="v4_UI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_UI_N" id="v4_UI_N_Label" title="The vulnerable system can be exploited without interaction from any human user, other than the attacker.">None (N)</label>
                                <input name="v4_UI" value="R" id="v4_UI_R" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_UI_R" id="v4_UI_R_Label" title="Successful exploitation of this vulnerability requires limited interaction by the targeted user with the vulnerable system and the attacker’s payload. These interactions would be considered involuntary and do not require that the user actively subvert protections built into the vulnerable system.">Passive (P)</label>
                                <input name="v4_UI" value="R" id="v4_UI_R" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_UI_R" id="v4_UI_R_Label" title="Successful exploitation of this vulnerability requires a targeted user to perform specific, conscious interactions with the vulnerable system and the attacker’s payload, or the user’s interactions would actively subvert protection mechanisms which would lead to exploitation of the vulnerability.">Active (A)</label>
                                </div>

                                <h5 id="VulnerableSystem_Metrics" title="">Vulnerable System Impact Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_VC_Heading" title="This metric measures the impact to the confidentiality of the information managed by the VULNERABLE SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (VC)</h3>
                                <input name="v4_VC" value="H" id="v4_VC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VC_H" id="v4_VC_H_Label" title="There is a total loss of confidentiality, resulting in all information within the Vulnerable System being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact. For example, an attacker steals the administrator's password, or private encryption keys of a web server.">High (H)</label>
                                <input name="v4_VC" value="L" id="v4_VC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VC_L" id="v4_VC_L_Label" title="There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the Vulnerable System.">Low (L)</label>
                                <input name="v4_VC" value="N" id="v4_VC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VC_N" id="v4_VC_N_Label" title="There is no loss of confidentiality within the Vulnerable System.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_VI_Heading" title="This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the VULNERABLE SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging).">Integrity (VI)</h3>
                                <input name="v4_VI" value="H" id="v4_VI_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VI_H" id="v4_VI_H_Label" title="There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the vulnerable system. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the vulnerable system.">High (H)</label>
                                <input name="v4_VI" value="L" id="v4_VI_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VI_L" id="v4_VI_L_Label" title="Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is limited. The data modification does not have a direct, serious impact to the Vulnerable System.">Low (L)</label>
                                <input name="v4_VI" value="N" id="v4_VI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VI_N" id="v4_VI_N_Label" title="There is no loss of integrity within the Vulnerable System.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_VA_Heading" title="This metric measures the impact to the availability of the VULNERABLE SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system.">Availability (VA)</h3>
                                <input name="v4_VA" value="H" id="v4_VA_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VA_H" id="v4_VA_H_Label" title="There is a total loss of availability, resulting in the attacker being able to fully deny access to resources in the Vulnerable System; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the Vulnerable System (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).">High (H)</label>
                                <input name="v4_VA" value="L" id="v4_VA_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VA_L" id="v4_VA_L_Label" title="Performance is reduced or there are interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the Vulnerable System are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the Vulnerable System.">Low (L)</label>
                                <input name="v4_VA" value="N" id="v4_VA_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VA_N" id="v4_VA_N_Label" title="There is no impact to availability within the Vulnerable System.">None (N)</label>
                                </div>

                                <h5 id="SSystemImpact_Metrics" title="">Subsequent System Impact Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_SC_Heading" title="This metric measures the impact to the confidentiality of the information managed by the SUBSEQUENT SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (SC)</h3>
                                <input name="v4_SC" value="H" id="v4_SC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SC_H" id="v4_SC_H_Label" title="There is a total loss of confidentiality, resulting in all resources within the Subsequent System being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact. For example, an attacker steals the administrator's password, or private encryption keys of a web server.">High (H)</label>
                                <input name="v4_SC" value="L" id="v4_SC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SC_L" id="v4_SC_L_Label" title="There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the Subsequent System.">Low (L)</label>
                                <input name="v4_SC" value="N" id="v4_SC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SC_N" id="v4_SC_N_Label" title="There is no loss of confidentiality within the Subsequent System or all confidentiality impact is constrained to the Vulnerable System.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_SI_Heading" title="This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the SUBSEQUENT SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging).">Integrity (SI)</h3>
                                <input name="v4_SI" value="H" id="v4_SI_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SI_H" id="v4_SI_H_Label" title="There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the Subsequent System. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the Subsequent System.">High (H)</label>
                                <input name="v4_SI" value="L" id="v4_SI_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SI_L" id="v4_SI_L_Label" title="Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is limited. The data modification does not have a direct, serious impact to the Subsequent System.">Low (L)</label>
                                <input name="v4_SI" value="N" id="v4_SI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SI_N" id="v4_SI_N_Label" title="There is no loss of integrity within the Subsequent System or all integrity impact is constrained to the Vulnerable System.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_SA_Heading" title="This metric measures the impact to the availability of the SUBSEQUENT SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system.">Availability (SA)</h3>
                                <input name="v4_SA" value="H" id="v4_SA_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SA_H" id="v4_SA_H_Label" title="There is a total loss of availability, resulting in the attacker being able to fully deny access to resources in the Subsequent System; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the Subsequent System (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).">High (H)</label>
                                <input name="v4_SA" value="L" id="v4_SA_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SA_L" id="v4_SA_L_Label" title="Performance is reduced or there are interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the Subsequent System are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the Subsequent System.">Low (L)</label>
                                <input name="v4_SA" value="N" id="v4_SA_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SA_N" id="v4_SA_N_Label" title="There is no impact to availability within the Subsequent System or all availability impact is constrained to the Vulnerable System.">None (N)</label>
                                </div>
                                </fieldset>

                                <fieldset id="supplementalMetricGroup">
                                <legend id="supplementalMetricGroup_Legend" title="This category is usually filled by the supplier">Supplemental Metrics</legend>

                                <div class="metric">
                                <h3 id="v4_S_Heading" title="When a system does have an intended use or fitness of purpose aligned to safety, it is possible that exploiting a vulnerability within that system may have Safety impact which can be represented in the Supplemental Metrics group. Lack of a Safety metric value being supplied does NOT mean that there may not be any Safety-related impacts.">Safety (S)</h3>
                                <input name="v4_S" value="X" id="v4_S_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_S_X" id="v4_S_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_S" value="N" id="v4_S_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_S_N" id="v4_S_N_Label" title="Consequences of the vulnerability meet definition of IEC 61508 consequence category &quot;negligible.&quot;">Negligible (N)</label>
                                <input name="v4_S" value="P" id="v4_S_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_S_P" id="v4_S_P_Label" title="Consequences of the vulnerability meet definition of IEC 61508 consequence categories of &quot;marginal,&quot; &quot;critical,&quot; or &quot;catastrophic.&quot;">Present (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_AU_Heading" title="The “ The “Automatable” metric captures the answer to the question ”Can an attacker automate exploitation events for this vulnerability across multiple targets?” based on steps 1-4 of the kill chain [Hutchins et al., 2011]. These steps are reconnaissance, weaponization, delivery, and exploitation.">Automatable (AU)</h3>
                                <input name="v4_AU" value="X" id="v4_AU_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AU_X" id="v4_AU_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_AU" value="N" id="v4_AU_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AU_N" id="v4_AU_N_Label" title="Attackers cannot reliably automate all 4 steps of the kill chain for this vulnerability for some reason. These steps are reconnaissance, weaponization, delivery, and exploitation.">No (N)</label>
                                <input name="v4_AU" value="Y" id="v4_AU_Y" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AU_Y" id="v4_AU_Y_Label" title="Attackers can reliably automate all 4 steps of the kill chain. These steps are reconnaissance, weaponization, delivery, and exploitation (e.g., the vulnerability is “wormable”).">Yes (Y)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_R_Heading" title="Recovery describes the resilience of a system to recover services, in terms of performance and availability, after an attack has been performed.">Recovery (R)</h3>
                                <input name="v4_R" value="X" id="v4_R_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_R_X" id="A_N_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_R" value="A" id="v4_R_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_R_A" id="A_L_Label" title="The system recovers services automatically after an attack has been performed.">Automatic (A)</label>
                                <input name="v4_R" value="U" id="v4_R_U" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_R_U" id="A_H_Label" title="The system requires manual intervention by the user to recover services, after an attack has been performed.">User (U)</label>
                                <input name="v4_R" value="I" id="v4_R_I" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_R_I" id="A_H_Label" title="The system services are irrecoverable by the user, after an attack has been performed.">Irrecoverable (I)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_V_Heading" title="Value Density describes the resources that the attacker will gain control over with a single exploitation event.">Value Density (V)</h3>
                                <input name="v4_V" value="X" id="v4_V_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_V_X" id="v4_V_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_V" value="D" id="v4_V_D" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_V_D" id="v4_V_D_Label" title="The vulnerable system has limited resources. That is, the resources that the attacker will gain control over with a single exploitation event are relatively small. An example of Diffuse (think: limited) Value Density would be an attack on a single email client vulnerability.">Diffuse (D)</label>
                                <input name="v4_V" value="C" id="v4_V_C" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_V_C" id="v4_V_C_Label" title="The vulnerable system is rich in resources. Heuristically, such systems are often the direct responsibility of “system operators” rather than users. An example of Concentrated (think: broad) Value Density would be an attack on a central email server.">Concentrated (C)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_RE_Heading" title="The intention of the Vulnerability Response Effort metric is to provide supplemental information on how difficult it is for consumers to provide an initial response to the impact of vulnerabilities for deployed products and services in their infrastructure. The consumer can then take this additional information on effort required into consideration when applying mitigations and/or scheduling remediation.">Vulnerability Response Effort (RE)</h3>
                                <input name="v4_RE" value="N" id="v4_RE_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_RE_X" id="v4_RE_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_RE" value="L" id="v4_RE_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_RE_L" id="v4_RE_L_Label" title="The effort required to respond to a vulnerability is low/trivial. Examples include: communication on better documentation, configuration workarounds, or guidance from the vendor that does not require an immediate update, upgrade, or replacement by the consuming entity, such as firewall filter configuration.">Low (L)</label>
                                <input name="v4_RE" value="H" id="v4_RE_M" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_RE_M" id="v4_RE_M_Label" title="The actions required to respond to a vulnerability require some effort on behalf of the consumer and could cause minimal service impact to implement. Examples include: simple remote update, disabling of a subsystem, or a low-touch software upgrade such as a driver update.">Moderate (M)</label>
                                <input name="v4_RE" value="H" id="v4_RE_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_RE_H" id="v4_RE_H_Label" title="The actions required to respond to a vulnerability are significant and/or difficult, and may possibly lead to an extended, scheduled service impact.  This would need to be considered for scheduling purposes including honoring any embargo on deployment of the selected response. Alternatively, response to the vulnerability in the field is not possible remotely. The only resolution to the vulnerability involves physical replacement (e.g. units deployed would have to be recalled for a depot level repair or replacement). Examples include: a highly privileged driver update, microcode or UEFI BIOS updates, or software upgrades requiring careful analysis and understanding of any potential infrastructure impact before implementation. A UEFI BIOS update that impacts Trusted Platform Module (TPM) attestation without impacting disk encryption software such as Bit locker is a good recent example. Irreparable failures such as non-bootable flash subsystems, failed disks or solid-state drives (SSD), bad memory modules, network devices, or other non-recoverable under warranty hardware, should also be scored as having a High effort.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_U_Heading" title="To facilitate a standardized method to incorporate additional provider-supplied assessment, an optional “pass-through” Supplemental Metric called Provider Urgency is available. Note: While any assessment provider along the product supply chain may provide a Provider Urgency rating. The Penultimate Product Provider (PPP) is best positioned to provide a direct assessment of Provider Urgency.">Provider Urgency (U)</h3>
                                <input name="v4_U" value="X" id="v4_U_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_X" id="v4_U_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_U" value="C" id="v4_U_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_C" id="v4_U_C_Label" title="Provider has assessed the impact of this vulnerability as having no urgency (Informational).">Clear</label>
                                <input name="v4_U" value="G" id="v4_U_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_G" id="v4_U_G_Label" title="Provider has assessed the impact of this vulnerability as having a reduced urgency.">Green</label>
                                <input name="v4_U" value="A" id="v4_U_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_A" id="v4_U_A_Label" title="Provider has assessed the impact of this vulnerability as having a moderate urgency.">Amber</label>
                                <input name="v4_U" value="R" id="v4_U_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_R" id="v4_U_R_Label" title="Provider has assessed the impact of this vulnerability as having the highest urgency.">Red</label>
                                </div>

                                </fieldset>
                                <fieldset id="environmentalMetricGroup">
                                <legend id="environmentalMetricGroup_Legend" title="This category is usually filled by the consumer">Environmental (Modified Base Metrics)</legend>

                                <h5 id="Exploitability_Metrics" title="">Exploitability Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_MAV_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric reflects the context by which vulnerability exploitation is possible. This metric value (and consequently the resulting severity) will be larger the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable system. The assumption is that the number of potential attackers for a vulnerability that could be exploited from across a network is larger than the number of potential attackers that could exploit a vulnerability requiring physical access to a device, and therefore warrants a greater severity.">Attack Vector (MAV)</h3>
                                <input name="v4_MAV" value="X" id="v4_MAV_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_X" id="v4_MAV_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MAV" value="N" id="v4_MAV_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_N" id="v4_MAV_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">Network (N)</label>
                                <input name="v4_MAV" value="A" id="v4_MAV_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_A" id="v4_MAV_A_Label" title="This metric values has the same definition as the Base Metric value defined above.">Adjacent (A)</label>
                                <input name="v4_MAV" value="L" id="v4_MAV_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_L" id="v4_MAV_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Local (L)</label>
                                <input name="v4_MAV" value="P" id="v4_MAV_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_P" id="v4_MAV_P_Label" title="This metric values has the same definition as the Base Metric value defined above.">Physical (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MAC_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric captures measurable actions that must be taken by the attacker to actively evade or circumvent existing built-in security-enhancing conditions in order to obtain a working exploit. These are conditions whose primary purpose is to increase security and/or increase exploit engineering complexity. A vulnerability exploitable without a target-specific variable has a lower complexity than a vulnerability that would require non-trivial customization. This metric is meant to capture security mechanisms utilized by the vulnerable system.">Attack Complexity (MAC)</h3>
                                <input name="v4_MAC" value="X" id="v4_MAC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAC_X" id="v4_MAC_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MAC" value="L" id="v4_MAC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAC_L" id="v4_MAC_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MAC" value="H" id="v4_MAC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAC_H" id="v4_MAC_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MAT_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric captures the prerequisite deployment and execution conditions or variables of the vulnerable system that enable the attack. These differ from security-enhancing techniques/technologies (ref Attack Complexity) as the primary purpose of these conditions is not to explicitly mitigate attacks, but rather, emerge naturally as a consequence of the deployment and execution of the vulnerable system.">Attack Requirements (MAT)</h3>
                                <input name="v4_MAT" value="X" id="v4_MAT_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAT_X" id="v4_MAT_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MAT" value="N" id="v4_MAT_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAT_N" id="v4_MAT_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                <input name="v4_MAT" value="P" id="v4_MAT_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAT_P" id="v4_MAT_P_Label" title="This metric values has the same definition as the Base Metric value defined above.">Present (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MPR_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric describes the level of privileges an attacker must possess prior to successfully exploiting the vulnerability. The method by which the attacker obtains privileged credentials prior to the attack (e.g., free trial accounts), is outside the scope of this metric. Generally, self-service provisioned accounts do not constitute a privilege requirement if the attacker can grant themselves privileges as part of the attack.">Privileges Required (MPR)</h3>
                                <input name="v4_MPR" value="X" id="v4_MPR_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MPR_X" id="v4_MPR_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MPR" value="N" id="v4_MPR_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MPR_N" id="v4_MPR_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                <input name="v4_MPR" value="L" id="v4_MPR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MPR_L" id="v4_MPR_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MPR" value="H" id="v4_MPR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MPR_H" id="v4_MPR_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MUI_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric captures the requirement for a human user, other than the attacker, to participate in the successful compromise of the vulnerable system. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner.">User Interaction (MUI)</h3>
                                <input name="v4_MUI" value="X" id="v4_MUI_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MUI_X" id="v4_MUI_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MUI" value="N" id="v4_MUI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MUI_N" id="v4_MUI_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                <input name="v4_MUI" value="P" id="v4_MUI_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MUI_P" id="v4_MUI_P_Label" title="This metric values has the same definition as the Base Metric value defined above.">Passive (P)</label>
                                <input name="v4_MUI" value="R" id="v4_MUI_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MUI_A" id="v4_MUI_A_Label" title="This metric values has the same definition as the Base Metric value defined above.">Active (A)</label>
                                </div>

                                <h5 id="VulnerableSystem_Metrics" title="">Vulnerable System Impact Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_MVC_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the confidentiality of the information managed by the VULNERABLE SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (MVC)</h3>
                                <input name="v4_MVC" value="X" id="v4_MVC_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVC_X" id="v4_MVC_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MVC" value="H" id="v4_MVC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVC_H" id="v4_MVC_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MVC" value="L" id="v4_MVC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVC_L" id="v4_MVC_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MVC" value="N" id="v4_MVC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVC_N" id="v4_MVC_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MVI_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the VULNERABLE SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging).">Integrity (MVI)</h3>
                                <input name="v4_MVI" value="X" id="v4_MVI_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVI_X" id="v4_MVI_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MVI" value="H" id="v4_MVI_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVI_H" id="v4_MVI_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MVI" value="L" id="v4_MVI_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVI_L" id="v4_MVI_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MVI" value="N" id="v4_MVI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVI_N" id="v4_MVI_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MVA_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the availability of the VULNERABLE SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system.">Availability (MVA)</h3>
                                <input name="v4_MVA" value="X" id="v4_MVA_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVA_X" id="v4_MVA_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MVA" value="H" id="v4_MVA_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVA_H" id="v4_MVA_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MVA" value="L" id="v4_MVA_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVA_L" id="v4_MVA_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MVA" value="N" id="v4_MVA_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVA_N" id="v4_MVA_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                </div>

                                <h5 id="SSystem_Metrics" title="">Subsequent System Impact Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_MSC_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the confidentiality of the information managed by the SUBSEQUENT SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (MSC)</h3>
                                <input name="v4_MSC" value="X" id="v4_MSC_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSC_X" id="v4_MSC_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MSC" value="H" id="v4_MSC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSC_H" id="v4_MSC_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MSC" value="L" id="v4_MSC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSC_L" id="v4_MSC_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MSC" value="N" id="v4_MSC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSC_N" id="v4_MSC_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">Negligible (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MSI_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the SUBSEQUENT SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging). In addition to the logical systems defined for System of Interest, Subsequent Systems can also include impacts to humans.">Integrity (MSI)</h3>
                                <input name="v4_MSI" value="X" id="v4_MSI_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_X" id="v4_MSI_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MSI" value="S" id="v4_MSI_S" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_S" id="v4_MSI_S_Label" title="The exploited vulnerability will result in integrity impacts that could cause serious injury or worse (categories of &quot;Marginal&quot; or worse as described in IEC 61508) to a human actor or participant.">Safety (S)</label>
                                <input name="v4_MSI" value="H" id="v4_MSI_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_H" id="v4_MSI_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MSI" value="L" id="v4_MSI_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_L" id="v4_MSI_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MSI" value="N" id="v4_MSI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_N" id="v4_MSI_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">Negligible (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MSA_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the availability of the SUBSEQUENT SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system. In addition to the logical systems defined for System of Interest, Subsequent Systems can also include impacts to humans.">Availability (MSA)</h3>
                                <input name="v4_MSA" value="X" id="v4_MSA_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_X" id="v4_MSA_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MSA" value="S" id="v4_MSA_S" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_S" id="v4_MSA_S_Label" title="The exploited vulnerability will result in availability impacts that could cause serious injury or worse (categories of &quot;Marginal&quot; or worse as described in IEC 61508) to a human actor or participant.">Safety (S)</label>
                                <input name="v4_MSA" value="H" id="v4_MSA_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_H" id="v4_MSA_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MSA" value="L" id="v4_MSA_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_L" id="v4_MSA_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MSA" value="N" id="v4_MSA_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_N" id="v4_MSA_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">Negligible (N)</label>
                                </div>
                                </fieldset>
                                <fieldset id="environmentalMetricGroup">
                                <legend id="environmentalMetricGroup_Legend" title="This category is usually filled by the consumer">Environmental (Security Requirements)</legend>

                                <div class="metric">
                                <h3 id="v4_CR_Heading" title="This metric enables the consumer to customize the assessment depending on the importance of the affected IT asset to the analyst’s organization, measured in terms of Confidentiality. That is, if an IT asset supports a business function for which Confidentiality is most important, the analyst can assign a greater value to Confidentiality metrics relative to Integrity and Availability.">Confidentiality Requirements (CR)</h3>
                                <input name="v4_CR" value="N" id="v4_CR_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_CR_X" id="v4_CR_X_Label" title="Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score">Not Defined (X)</label>
                                <input name="v4_CR" value="H" id="v4_CR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_CR_H" id="v4_CR_H_Label" title="Loss of Confidentiality is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization.">High (H)</label>
                                <input name="v4_CR" value="L" id="v4_CR_M" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_CR_M" id="v4_CR_M_Label" title="Loss of Confidentiality is likely to have a serious adverse effect on the organization or individuals associated with the organization.">Medium (M)</label>
                                <input name="v4_CR" value="N" id="v4_CR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_CR_L" id="v4_CR_L_Label" title="Loss of Confidentiality is likely to have only a limited adverse effect on the organization or individuals associated with the organization.">Low (L)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_IR_Heading" title="This metric enables the consumer to customize the assessment depending on the importance of the affected IT asset to the analyst’s organization, measured in terms of Integrity. That is, if an IT asset supports a business function for which Integrity is most important, the analyst can assign a greater value to Integrity metrics relative to Confidentiality and Availability.">Integrity Requirements (IR)</h3>
                                <input name="v4_IR" value="X" id="v4_IR_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_IR_X" id="v4_IR_X_Label" title="Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score">Not Defined (X)</label>
                                <input name="v4_IR" value="H" id="v4_IR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_IR_H" id="v4_IR_H_Label" title="Loss of Integrity is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization.">High (H)</label>
                                <input name="v4_IR" value="M" id="v4_IR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_IR_M" id="v4_IR_M_Label" title="Loss of Integrity is likely to have a serious adverse effect on the organization or individuals associated with the organization.">Medium (M)</label>
                                <input name="v4_IR" value="L" id="v4_IR_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_IR_L" id="v4_IR_L_Label" title="Loss of Integrity is likely to have only a limited adverse effect on the organization or individuals associated with the organization.">Low (L)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_AR_Heading" title="This metric enables the consumer to customize the assessment depending on the importance of the affected IT asset to the analyst’s organization, measured in terms of Availability. That is, if an IT asset supports a business function for which Availability is most important, the analyst can assign a greater value to Availability metrics relative to Confidentiality and Integrity.">Availability Requirements (AR)</h3>
                                <input name="v4_AR" value="X" id="v4_AR_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AR_X" id="v4_AR_X_Label" title="Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score">Not Defined (X)</label>
                                <input name="v4_AR" value="H" id="v4_AR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AR_H" id="v4_AR_H_Label" title="Loss of Availability is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization.">High (H)</label>
                                <input name="v4_AR" value="M" id="v4_AR_M" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AR_M" id="v4_AR_M_Label" title="Loss of Availability is likely to have a serious adverse effect on the organization or individuals associated with the organization.">Medium (M)</label>
                                <input name="v4_AR" value="L" id="v4_AR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AR_L" id="v4_AR_L_Label" title="Loss of Availability is likely to have only a limited adverse effect on the organization or individuals associated with the organization.">Low (L)</label>
                                </div>
                                </fieldset>
                                <fieldset id="threatMetricGroup">
                                <legend id="threatMetricGroup_Legend" title="This category is usually filled by the consumer">Threat Metrics</legend>

                                <div class="metric">
                                <h3 id="v4_E_Heading" title="This metric measures the likelihood of the vulnerability being attacked, and is typically based on the current state of exploit techniques, exploit code availability, or active, &quot;in-the-wild&quot; exploitation. It is the responsibility of the CVSS consumer to populate the values of Exploit Maturity (E) based on information regarding the availability of exploitation code/processes and the state of exploitation techniques. This information will be referred to as &quot;threat intelligence&quot;.">Exploit Maturity (E)</h3>
                                <input name="v4_E" value="X" id="v4_E_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_E_X" id="v4_E_X_Label" title="The Exploit Maturity metric is not being used.  Reliable threat intelligence is not available to determine Exploit Maturity characteristics.">Not Defined (X)</label>
                                <input name="v4_E" value="A" id="v4_E_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_E_A" id="v4_E_A_Label" title="Based on threat intelligence sources either of the following must apply:
· Attacks targeting this vulnerability (attempted or successful) have been reported
· Solutions to simplify attempts to exploit the vulnerability are publicly or privately available (such as exploit toolkits)">Attacked (A)</label>
                                <input name="v4_E" value="P" id="v4_E_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_E_P" id="v4_E_P_Label" title="Based on threat intelligence sources each of the following must apply:
· Proof-of-concept is publicly available
· No knowledge of reported attempts to exploit this vulnerability
· No knowledge of publicly available solutions used to simplify attempts to exploit the vulnerability">POC (P)</label>
                                <input name="v4_E" value="U" id="v4_E_U" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_E_U" id="v4_E_U_Label" title="Based on threat intelligence sources each of the following must apply:
· No knowledge of publicly available proof-of-concept
· No knowledge of reported attempts to exploit this vulnerability
· No knowledge of publicly available solutions used to simplify attempts to exploit the vulnerability">Unreported (U)</label>
                                </div>
                                </fieldset>
                                </div>
                                """
                            ),
                        ),
                    )
                    ,
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

    def __init__(self, user=None, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this is an update, mark the project field as read-only
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields["project"].disabled = True

        # Limit the list to the pre-selected project and disable the field
        if project:
            self.fields["project"].queryset = Project.objects.filter(pk=project.pk)
            self.fields["project"].disabled = True

        if not project:
            projects = get_project_list(user)
            active_projects = projects.filter(complete=False).order_by("-start_date", "client", "project_type")
            if active_projects:
                self.fields["project"].empty_label = "-- Select an Active Project --"
            else:
                self.fields["project"].empty_label = "-- No Active Projects --"
            self.fields["project"].queryset = active_projects
            self.fields[
                "project"
            ].label_from_instance = (
                lambda obj: f"{obj.start_date} {obj.client.name} {obj.project_type} ({obj.codename})"
            )

        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
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
            "complete",
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
        self.fields["replication_steps"].widget.attrs["placeholder"] = "How to reproduce/find this issue ..."
        self.fields["host_detection_techniques"].widget.attrs["placeholder"] = "How to detect it on an endpoint ..."
        self.fields["network_detection_techniques"].widget.attrs["placeholder"] = "How to detect it on a network ..."
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
                    TabHolder(
                        Tab(
                            "CVSS v3.0",
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
                                <input name="AV" value="L" id="AV_L" type="radio" onclick="CVSSAutoCalc()"><label for="AV_L" id="AV_L_Label" title="A vulnerability exploitable with local access means that the vulnerable component is not bound to the network stack, and the attacker's path is via read/write/execute capabilities. In some cases, the attacker may be logged in locally in order to exploit the vulnerability, otherwise, she may rely on User Interaction to execute a malicious file.">Local (L)</label>
                                <input name="AV" value="P" id="AV_P" type="radio" onclick="CVSSAutoCalc()"><label for="AV_P" id="AV_P_Label" title="A vulnerability exploitable with physical access requires the attacker to physically touch or manipulate the vulnerable component. Physical interaction may be brief or persistent.">Physical (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="AC_Heading" title="This metric describes the conditions beyond the attacker's control that must exist in order to exploit the vulnerability. Such conditions may require the collection of more information about the target, the presence of certain system configuration settings, or computational exceptions.">Attack Complexity (AC)</h3>
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
                        ),
                        Tab(
                            "CVSS v4.0",
                            HTML(
                                """
                                <!--
                                Copyright (c) 2023 FIRST.ORG, Inc., Red Hat, and contributors

                                Redistribution and use in source and binary forms, with or without
                                modification, are permitted provided that the following conditions are met:

                                1. Redistributions of source code must retain the above copyright notice, this
                                   list of conditions and the following disclaimer.

                                2. Redistributions in binary form must reproduce the above copyright notice,
                                   this list of conditions and the following disclaimer in the documentation
                                   and/or other materials provided with the distribution.

                                THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
                                AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
                                IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
                                DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
                                FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
                                DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
                                SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
                                CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
                                OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
                                OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
                                -->
                                <div style="height: 500px; overflow: auto;">
                                <fieldset id="baseMetricGroup">
                                <legend id="baseMetricGroup_Legend" title="This category is usually filled by the supplier">Base Metrics</legend>

                                <h5 id="Exploitability_Metrics" title="">Exploitability Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_AV_Heading" title="This metric reflects the context by which vulnerability exploitation is possible. This metric value (and consequently the resulting severity) will be larger the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable system. The assumption is that the number of potential attackers for a vulnerability that could be exploited from across a network is larger than the number of potential attackers that could exploit a vulnerability requiring physical access to a device, and therefore warrants a greater severity.">Attack Vector (AV)</h3>
                                <input name="v4_AV" value="N" id="v4_AV_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AV_N" id="v4_AV_N_Label" title="The vulnerable system is bound to the network stack and the set of possible attackers extends beyond the other options listed below, up to and including the entire Internet. Such a vulnerability is often termed “remotely exploitable” and can be thought of as an attack being exploitable at the protocol level one or more network hops away (e.g., across one or more routers).">Network (N)</label>
                                <input name="v4_AV" value="A" id="v4_AV_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AV_A" id="v4_AV_A_Label" title="The vulnerable system is bound to a protocol stack, but the attack is limited at the protocol level to a logically adjacent topology. This can mean an attack must be launched from the same shared proximity (e.g., Bluetooth, NFC, or IEEE 802.11) or logical network (e.g., local IP subnet), or from within a secure or otherwise limited administrative domain (e.g., MPLS, secure VPN within an administrative network zone).">Adjacent (A)</label>
                                <input name="v4_AV" value="L" id="v4_AV_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AV_L" id="v4_AV_L_Label" title="The vulnerable system is not bound to the network stack and the attacker's path is via read/write/execute capabilities. Either the attacker exploits the vulnerability by accessing the target system locally (e.g., keyboard, console), or through terminal emulation (e.g., SSH); or the attacker relies on User Interaction by another person to perform actions required to exploit the vulnerability (e.g., using social engineering techniques to trick a legitimate user into opening a malicious document).">Local (L)</label>
                                <input name="v4_AV" value="P" id="v4_AV_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AV_P" id="v4_AV_P_Label" title="The attack requires the attacker to physically touch or manipulate the vulnerable system. Physical interaction may be brief (e.g., evil maid attack) or persistent.">Physical (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_AC_Heading" title="This metric captures measurable actions that must be taken by the attacker to actively evade or circumvent existing built-in security-enhancing conditions in order to obtain a working exploit. These are conditions whose primary purpose is to increase security and/or increase exploit engineering complexity. A vulnerability exploitable without a target-specific variable has a lower complexity than a vulnerability that would require non-trivial customization. This metric is meant to capture security mechanisms utilized by the vulnerable system.">Attack Complexity (AC)</h3>
                                <input name="v4_AC" value="L" id="v4_AC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AC_L" id="v4_AC_L_Label" title="The attacker must take no measurable action to exploit the vulnerability. The attack requires no target-specific circumvention to exploit the vulnerability. An attacker can expect repeatable success against the vulnerable system.">Low (L)</label>
                                <input name="v4_AC" value="H" id="v4_AC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AC_H" id="v4_AC_H_Label" title="The successful attack depends on the evasion or circumvention of security-enhancing techniques in place that would otherwise hinder the attack. These include: Evasion of exploit mitigation techniques, for example, circumvention of address space randomization (ASLR) or data execution prevention (DEP) must be performed for the attack to be successful; Obtaining target-specific secrets. The attacker must gather some target-specific secret before the attack can be successful. A secret is any piece of information that cannot be obtained through any amount of reconnaissance. To obtain the secret the attacker must perform additional attacks or break otherwise secure measures (e.g. knowledge of a secret key may be needed to break a crypto channel). This operation must be performed for each attacked target.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_AT_Heading" title="This metric captures the prerequisite deployment and execution conditions or variables of the vulnerable system that enable the attack. These differ from security-enhancing techniques/technologies (ref Attack Complexity) as the primary purpose of these conditions is not to explicitly mitigate attacks, but rather, emerge naturally as a consequence of the deployment and execution of the vulnerable system.">Attack Requirements (AT)</h3>
                                <input name="v4_AT" value="N" id="v4_AT_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AT_N" id="v4_AT_N_Label" title="The successful attack does not depend on the deployment and execution conditions of the vulnerable system. The attacker can expect to be able to reach the vulnerability and execute the exploit under all or most instances of the vulnerability.">None (N)</label>
                                <input name="v4_AT" value="L" id="v4_AT_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AT_P" id="v4_AT_P_Label" title="The successful attack depends on the presence of specific deployment and execution conditions of the vulnerable system that enable the attack. These include: a race condition must be won to successfully exploit the vulnerability (the successfulness of the attack is conditioned on execution conditions that are not under full control of the attacker, or the attack may need to be launched multiple times against a single target before being successful); the attacker must inject themselves into the logical network path between the target and the resource requested by the victim (e.g. vulnerabilities requiring an on-path attacker).">Present (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_PR_Heading" title="This metric describes the level of privileges an attacker must possess prior to successfully exploiting the vulnerability. The method by which the attacker obtains privileged credentials prior to the attack (e.g., free trial accounts), is outside the scope of this metric. Generally, self-service provisioned accounts do not constitute a privilege requirement if the attacker can grant themselves privileges as part of the attack.">Privileges Required (PR)</h3>
                                <input name="v4_PR" value="N" id="v4_PR_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_PR_N" id="v4_PR_N_Label" title="The attacker is unauthorized prior to attack, and therefore does not require any access to settings or files of the vulnerable system to carry out an attack.">None (N)</label>
                                <input name="v4_PR" value="L" id="v4_PR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_PR_L" id="v4_PR_L_Label" title="The attacker requires privileges that provide basic capabilities that are typically limited to settings and resources owned by a single low-privileged user. Alternatively, an attacker with Low privileges has the ability to access only non-sensitive resources.">Low (L)</label>
                                <input name="v4_PR" value="H" id="v4_PR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_PR_H" id="v4_PR_H_Label" title="The attacker requires privileges that provide significant (e.g., administrative) control over the vulnerable system allowing full access to the vulnerable system's settings and files.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_UI_Heading" title="This metric captures the requirement for a human user, other than the attacker, to participate in the successful compromise of the vulnerable system. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner.">User Interaction (UI)</h3>
                                <input name="v4_UI" value="N" id="v4_UI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_UI_N" id="v4_UI_N_Label" title="The vulnerable system can be exploited without interaction from any human user, other than the attacker.">None (N)</label>
                                <input name="v4_UI" value="R" id="v4_UI_R" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_UI_R" id="v4_UI_R_Label" title="Successful exploitation of this vulnerability requires limited interaction by the targeted user with the vulnerable system and the attacker’s payload. These interactions would be considered involuntary and do not require that the user actively subvert protections built into the vulnerable system.">Passive (P)</label>
                                <input name="v4_UI" value="R" id="v4_UI_R" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_UI_R" id="v4_UI_R_Label" title="Successful exploitation of this vulnerability requires a targeted user to perform specific, conscious interactions with the vulnerable system and the attacker’s payload, or the user’s interactions would actively subvert protection mechanisms which would lead to exploitation of the vulnerability.">Active (A)</label>
                                </div>

                                <h5 id="VulnerableSystem_Metrics" title="">Vulnerable System Impact Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_VC_Heading" title="This metric measures the impact to the confidentiality of the information managed by the VULNERABLE SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (VC)</h3>
                                <input name="v4_VC" value="H" id="v4_VC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VC_H" id="v4_VC_H_Label" title="There is a total loss of confidentiality, resulting in all information within the Vulnerable System being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact. For example, an attacker steals the administrator's password, or private encryption keys of a web server.">High (H)</label>
                                <input name="v4_VC" value="L" id="v4_VC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VC_L" id="v4_VC_L_Label" title="There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the Vulnerable System.">Low (L)</label>
                                <input name="v4_VC" value="N" id="v4_VC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VC_N" id="v4_VC_N_Label" title="There is no loss of confidentiality within the Vulnerable System.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_VI_Heading" title="This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the VULNERABLE SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging).">Integrity (VI)</h3>
                                <input name="v4_VI" value="H" id="v4_VI_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VI_H" id="v4_VI_H_Label" title="There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the vulnerable system. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the vulnerable system.">High (H)</label>
                                <input name="v4_VI" value="L" id="v4_VI_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VI_L" id="v4_VI_L_Label" title="Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is limited. The data modification does not have a direct, serious impact to the Vulnerable System.">Low (L)</label>
                                <input name="v4_VI" value="N" id="v4_VI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VI_N" id="v4_VI_N_Label" title="There is no loss of integrity within the Vulnerable System.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_VA_Heading" title="This metric measures the impact to the availability of the VULNERABLE SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system.">Availability (VA)</h3>
                                <input name="v4_VA" value="H" id="v4_VA_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VA_H" id="v4_VA_H_Label" title="There is a total loss of availability, resulting in the attacker being able to fully deny access to resources in the Vulnerable System; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the Vulnerable System (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).">High (H)</label>
                                <input name="v4_VA" value="L" id="v4_VA_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VA_L" id="v4_VA_L_Label" title="Performance is reduced or there are interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the Vulnerable System are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the Vulnerable System.">Low (L)</label>
                                <input name="v4_VA" value="N" id="v4_VA_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_VA_N" id="v4_VA_N_Label" title="There is no impact to availability within the Vulnerable System.">None (N)</label>
                                </div>

                                <h5 id="SSystemImpact_Metrics" title="">Subsequent System Impact Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_SC_Heading" title="This metric measures the impact to the confidentiality of the information managed by the SUBSEQUENT SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (SC)</h3>
                                <input name="v4_SC" value="H" id="v4_SC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SC_H" id="v4_SC_H_Label" title="There is a total loss of confidentiality, resulting in all resources within the Subsequent System being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact. For example, an attacker steals the administrator's password, or private encryption keys of a web server.">High (H)</label>
                                <input name="v4_SC" value="L" id="v4_SC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SC_L" id="v4_SC_L_Label" title="There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the Subsequent System.">Low (L)</label>
                                <input name="v4_SC" value="N" id="v4_SC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SC_N" id="v4_SC_N_Label" title="There is no loss of confidentiality within the Subsequent System or all confidentiality impact is constrained to the Vulnerable System.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_SI_Heading" title="This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the SUBSEQUENT SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging).">Integrity (SI)</h3>
                                <input name="v4_SI" value="H" id="v4_SI_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SI_H" id="v4_SI_H_Label" title="There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the Subsequent System. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the Subsequent System.">High (H)</label>
                                <input name="v4_SI" value="L" id="v4_SI_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SI_L" id="v4_SI_L_Label" title="Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is limited. The data modification does not have a direct, serious impact to the Subsequent System.">Low (L)</label>
                                <input name="v4_SI" value="N" id="v4_SI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SI_N" id="v4_SI_N_Label" title="There is no loss of integrity within the Subsequent System or all integrity impact is constrained to the Vulnerable System.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_SA_Heading" title="This metric measures the impact to the availability of the SUBSEQUENT SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system.">Availability (SA)</h3>
                                <input name="v4_SA" value="H" id="v4_SA_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SA_H" id="v4_SA_H_Label" title="There is a total loss of availability, resulting in the attacker being able to fully deny access to resources in the Subsequent System; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the Subsequent System (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).">High (H)</label>
                                <input name="v4_SA" value="L" id="v4_SA_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SA_L" id="v4_SA_L_Label" title="Performance is reduced or there are interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the Subsequent System are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the Subsequent System.">Low (L)</label>
                                <input name="v4_SA" value="N" id="v4_SA_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_SA_N" id="v4_SA_N_Label" title="There is no impact to availability within the Subsequent System or all availability impact is constrained to the Vulnerable System.">None (N)</label>
                                </div>
                                </fieldset>

                                <fieldset id="supplementalMetricGroup">
                                <legend id="supplementalMetricGroup_Legend" title="This category is usually filled by the supplier">Supplemental Metrics</legend>

                                <div class="metric">
                                <h3 id="v4_S_Heading" title="When a system does have an intended use or fitness of purpose aligned to safety, it is possible that exploiting a vulnerability within that system may have Safety impact which can be represented in the Supplemental Metrics group. Lack of a Safety metric value being supplied does NOT mean that there may not be any Safety-related impacts.">Safety (S)</h3>
                                <input name="v4_S" value="X" id="v4_S_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_S_X" id="v4_S_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_S" value="N" id="v4_S_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_S_N" id="v4_S_N_Label" title="Consequences of the vulnerability meet definition of IEC 61508 consequence category &quot;negligible.&quot;">Negligible (N)</label>
                                <input name="v4_S" value="P" id="v4_S_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_S_P" id="v4_S_P_Label" title="Consequences of the vulnerability meet definition of IEC 61508 consequence categories of &quot;marginal,&quot; &quot;critical,&quot; or &quot;catastrophic.&quot;">Present (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_AU_Heading" title="The “ The “Automatable” metric captures the answer to the question ”Can an attacker automate exploitation events for this vulnerability across multiple targets?” based on steps 1-4 of the kill chain [Hutchins et al., 2011]. These steps are reconnaissance, weaponization, delivery, and exploitation.">Automatable (AU)</h3>
                                <input name="v4_AU" value="X" id="v4_AU_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AU_X" id="v4_AU_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_AU" value="N" id="v4_AU_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AU_N" id="v4_AU_N_Label" title="Attackers cannot reliably automate all 4 steps of the kill chain for this vulnerability for some reason. These steps are reconnaissance, weaponization, delivery, and exploitation.">No (N)</label>
                                <input name="v4_AU" value="Y" id="v4_AU_Y" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AU_Y" id="v4_AU_Y_Label" title="Attackers can reliably automate all 4 steps of the kill chain. These steps are reconnaissance, weaponization, delivery, and exploitation (e.g., the vulnerability is “wormable”).">Yes (Y)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_R_Heading" title="Recovery describes the resilience of a system to recover services, in terms of performance and availability, after an attack has been performed.">Recovery (R)</h3>
                                <input name="v4_R" value="X" id="v4_R_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_R_X" id="A_N_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_R" value="A" id="v4_R_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_R_A" id="A_L_Label" title="The system recovers services automatically after an attack has been performed.">Automatic (A)</label>
                                <input name="v4_R" value="U" id="v4_R_U" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_R_U" id="A_H_Label" title="The system requires manual intervention by the user to recover services, after an attack has been performed.">User (U)</label>
                                <input name="v4_R" value="I" id="v4_R_I" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_R_I" id="A_H_Label" title="The system services are irrecoverable by the user, after an attack has been performed.">Irrecoverable (I)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_V_Heading" title="Value Density describes the resources that the attacker will gain control over with a single exploitation event.">Value Density (V)</h3>
                                <input name="v4_V" value="X" id="v4_V_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_V_X" id="v4_V_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_V" value="D" id="v4_V_D" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_V_D" id="v4_V_D_Label" title="The vulnerable system has limited resources. That is, the resources that the attacker will gain control over with a single exploitation event are relatively small. An example of Diffuse (think: limited) Value Density would be an attack on a single email client vulnerability.">Diffuse (D)</label>
                                <input name="v4_V" value="C" id="v4_V_C" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_V_C" id="v4_V_C_Label" title="The vulnerable system is rich in resources. Heuristically, such systems are often the direct responsibility of “system operators” rather than users. An example of Concentrated (think: broad) Value Density would be an attack on a central email server.">Concentrated (C)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_RE_Heading" title="The intention of the Vulnerability Response Effort metric is to provide supplemental information on how difficult it is for consumers to provide an initial response to the impact of vulnerabilities for deployed products and services in their infrastructure. The consumer can then take this additional information on effort required into consideration when applying mitigations and/or scheduling remediation.">Vulnerability Response Effort (RE)</h3>
                                <input name="v4_RE" value="N" id="v4_RE_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_RE_X" id="v4_RE_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_RE" value="L" id="v4_RE_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_RE_L" id="v4_RE_L_Label" title="The effort required to respond to a vulnerability is low/trivial. Examples include: communication on better documentation, configuration workarounds, or guidance from the vendor that does not require an immediate update, upgrade, or replacement by the consuming entity, such as firewall filter configuration.">Low (L)</label>
                                <input name="v4_RE" value="H" id="v4_RE_M" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_RE_M" id="v4_RE_M_Label" title="The actions required to respond to a vulnerability require some effort on behalf of the consumer and could cause minimal service impact to implement. Examples include: simple remote update, disabling of a subsystem, or a low-touch software upgrade such as a driver update.">Moderate (M)</label>
                                <input name="v4_RE" value="H" id="v4_RE_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_RE_H" id="v4_RE_H_Label" title="The actions required to respond to a vulnerability are significant and/or difficult, and may possibly lead to an extended, scheduled service impact.  This would need to be considered for scheduling purposes including honoring any embargo on deployment of the selected response. Alternatively, response to the vulnerability in the field is not possible remotely. The only resolution to the vulnerability involves physical replacement (e.g. units deployed would have to be recalled for a depot level repair or replacement). Examples include: a highly privileged driver update, microcode or UEFI BIOS updates, or software upgrades requiring careful analysis and understanding of any potential infrastructure impact before implementation. A UEFI BIOS update that impacts Trusted Platform Module (TPM) attestation without impacting disk encryption software such as Bit locker is a good recent example. Irreparable failures such as non-bootable flash subsystems, failed disks or solid-state drives (SSD), bad memory modules, network devices, or other non-recoverable under warranty hardware, should also be scored as having a High effort.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_U_Heading" title="To facilitate a standardized method to incorporate additional provider-supplied assessment, an optional “pass-through” Supplemental Metric called Provider Urgency is available. Note: While any assessment provider along the product supply chain may provide a Provider Urgency rating. The Penultimate Product Provider (PPP) is best positioned to provide a direct assessment of Provider Urgency.">Provider Urgency (U)</h3>
                                <input name="v4_U" value="X" id="v4_U_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_X" id="v4_U_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_U" value="C" id="v4_U_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_C" id="v4_U_C_Label" title="Provider has assessed the impact of this vulnerability as having no urgency (Informational).">Clear</label>
                                <input name="v4_U" value="G" id="v4_U_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_G" id="v4_U_G_Label" title="Provider has assessed the impact of this vulnerability as having a reduced urgency.">Green</label>
                                <input name="v4_U" value="A" id="v4_U_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_A" id="v4_U_A_Label" title="Provider has assessed the impact of this vulnerability as having a moderate urgency.">Amber</label>
                                <input name="v4_U" value="R" id="v4_U_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_U_R" id="v4_U_R_Label" title="Provider has assessed the impact of this vulnerability as having the highest urgency.">Red</label>
                                </div>

                                </fieldset>
                                <fieldset id="environmentalMetricGroup">
                                <legend id="environmentalMetricGroup_Legend" title="This category is usually filled by the consumer">Environmental (Modified Base Metrics)</legend>

                                <h5 id="Exploitability_Metrics" title="">Exploitability Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_MAV_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric reflects the context by which vulnerability exploitation is possible. This metric value (and consequently the resulting severity) will be larger the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable system. The assumption is that the number of potential attackers for a vulnerability that could be exploited from across a network is larger than the number of potential attackers that could exploit a vulnerability requiring physical access to a device, and therefore warrants a greater severity.">Attack Vector (MAV)</h3>
                                <input name="v4_MAV" value="X" id="v4_MAV_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_X" id="v4_MAV_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MAV" value="N" id="v4_MAV_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_N" id="v4_MAV_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">Network (N)</label>
                                <input name="v4_MAV" value="A" id="v4_MAV_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_A" id="v4_MAV_A_Label" title="This metric values has the same definition as the Base Metric value defined above.">Adjacent (A)</label>
                                <input name="v4_MAV" value="L" id="v4_MAV_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_L" id="v4_MAV_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Local (L)</label>
                                <input name="v4_MAV" value="P" id="v4_MAV_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAV_P" id="v4_MAV_P_Label" title="This metric values has the same definition as the Base Metric value defined above.">Physical (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MAC_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric captures measurable actions that must be taken by the attacker to actively evade or circumvent existing built-in security-enhancing conditions in order to obtain a working exploit. These are conditions whose primary purpose is to increase security and/or increase exploit engineering complexity. A vulnerability exploitable without a target-specific variable has a lower complexity than a vulnerability that would require non-trivial customization. This metric is meant to capture security mechanisms utilized by the vulnerable system.">Attack Complexity (MAC)</h3>
                                <input name="v4_MAC" value="X" id="v4_MAC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAC_X" id="v4_MAC_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MAC" value="L" id="v4_MAC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAC_L" id="v4_MAC_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MAC" value="H" id="v4_MAC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAC_H" id="v4_MAC_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MAT_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric captures the prerequisite deployment and execution conditions or variables of the vulnerable system that enable the attack. These differ from security-enhancing techniques/technologies (ref Attack Complexity) as the primary purpose of these conditions is not to explicitly mitigate attacks, but rather, emerge naturally as a consequence of the deployment and execution of the vulnerable system.">Attack Requirements (MAT)</h3>
                                <input name="v4_MAT" value="X" id="v4_MAT_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAT_X" id="v4_MAT_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MAT" value="N" id="v4_MAT_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAT_N" id="v4_MAT_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                <input name="v4_MAT" value="P" id="v4_MAT_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MAT_P" id="v4_MAT_P_Label" title="This metric values has the same definition as the Base Metric value defined above.">Present (P)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MPR_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric describes the level of privileges an attacker must possess prior to successfully exploiting the vulnerability. The method by which the attacker obtains privileged credentials prior to the attack (e.g., free trial accounts), is outside the scope of this metric. Generally, self-service provisioned accounts do not constitute a privilege requirement if the attacker can grant themselves privileges as part of the attack.">Privileges Required (MPR)</h3>
                                <input name="v4_MPR" value="X" id="v4_MPR_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MPR_X" id="v4_MPR_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MPR" value="N" id="v4_MPR_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MPR_N" id="v4_MPR_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                <input name="v4_MPR" value="L" id="v4_MPR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MPR_L" id="v4_MPR_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MPR" value="H" id="v4_MPR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MPR_H" id="v4_MPR_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MUI_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric captures the requirement for a human user, other than the attacker, to participate in the successful compromise of the vulnerable system. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner.">User Interaction (MUI)</h3>
                                <input name="v4_MUI" value="X" id="v4_MUI_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MUI_X" id="v4_MUI_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MUI" value="N" id="v4_MUI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MUI_N" id="v4_MUI_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                <input name="v4_MUI" value="P" id="v4_MUI_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MUI_P" id="v4_MUI_P_Label" title="This metric values has the same definition as the Base Metric value defined above.">Passive (P)</label>
                                <input name="v4_MUI" value="R" id="v4_MUI_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MUI_A" id="v4_MUI_A_Label" title="This metric values has the same definition as the Base Metric value defined above.">Active (A)</label>
                                </div>

                                <h5 id="VulnerableSystem_Metrics" title="">Vulnerable System Impact Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_MVC_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the confidentiality of the information managed by the VULNERABLE SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (MVC)</h3>
                                <input name="v4_MVC" value="X" id="v4_MVC_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVC_X" id="v4_MVC_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MVC" value="H" id="v4_MVC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVC_H" id="v4_MVC_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MVC" value="L" id="v4_MVC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVC_L" id="v4_MVC_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MVC" value="N" id="v4_MVC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVC_N" id="v4_MVC_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MVI_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the VULNERABLE SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging).">Integrity (MVI)</h3>
                                <input name="v4_MVI" value="X" id="v4_MVI_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVI_X" id="v4_MVI_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MVI" value="H" id="v4_MVI_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVI_H" id="v4_MVI_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MVI" value="L" id="v4_MVI_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVI_L" id="v4_MVI_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MVI" value="N" id="v4_MVI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVI_N" id="v4_MVI_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MVA_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the availability of the VULNERABLE SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system.">Availability (MVA)</h3>
                                <input name="v4_MVA" value="X" id="v4_MVA_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVA_X" id="v4_MVA_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MVA" value="H" id="v4_MVA_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVA_H" id="v4_MVA_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MVA" value="L" id="v4_MVA_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVA_L" id="v4_MVA_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MVA" value="N" id="v4_MVA_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MVA_N" id="v4_MVA_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">None (N)</label>
                                </div>

                                <h5 id="SSystem_Metrics" title="">Subsequent System Impact Metrics</h5>

                                <div class="metric">
                                <h3 id="v4_MSC_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the confidentiality of the information managed by the SUBSEQUENT SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.">Confidentiality (MSC)</h3>
                                <input name="v4_MSC" value="X" id="v4_MSC_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSC_X" id="v4_MSC_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MSC" value="H" id="v4_MSC_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSC_H" id="v4_MSC_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MSC" value="L" id="v4_MSC_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSC_L" id="v4_MSC_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MSC" value="N" id="v4_MSC_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSC_N" id="v4_MSC_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">Negligible (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MSI_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the SUBSEQUENT SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging). In addition to the logical systems defined for System of Interest, Subsequent Systems can also include impacts to humans.">Integrity (MSI)</h3>
                                <input name="v4_MSI" value="X" id="v4_MSI_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_X" id="v4_MSI_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MSI" value="S" id="v4_MSI_S" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_S" id="v4_MSI_S_Label" title="The exploited vulnerability will result in integrity impacts that could cause serious injury or worse (categories of &quot;Marginal&quot; or worse as described in IEC 61508) to a human actor or participant.">Safety (S)</label>
                                <input name="v4_MSI" value="H" id="v4_MSI_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_H" id="v4_MSI_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MSI" value="L" id="v4_MSI_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_L" id="v4_MSI_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MSI" value="N" id="v4_MSI_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSI_N" id="v4_MSI_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">Negligible (N)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_MSA_Heading" title="These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the availability of the SUBSEQUENT SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system. In addition to the logical systems defined for System of Interest, Subsequent Systems can also include impacts to humans.">Availability (MSA)</h3>
                                <input name="v4_MSA" value="X" id="v4_MSA_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_X" id="v4_MSA_X_Label" title="The metric has not been evaluated.">Not Defined (X)</label>
                                <input name="v4_MSA" value="S" id="v4_MSA_S" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_S" id="v4_MSA_S_Label" title="The exploited vulnerability will result in availability impacts that could cause serious injury or worse (categories of &quot;Marginal&quot; or worse as described in IEC 61508) to a human actor or participant.">Safety (S)</label>
                                <input name="v4_MSA" value="H" id="v4_MSA_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_H" id="v4_MSA_H_Label" title="This metric values has the same definition as the Base Metric value defined above.">High (H)</label>
                                <input name="v4_MSA" value="L" id="v4_MSA_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_L" id="v4_MSA_L_Label" title="This metric values has the same definition as the Base Metric value defined above.">Low (L)</label>
                                <input name="v4_MSA" value="N" id="v4_MSA_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_MSA_N" id="v4_MSA_N_Label" title="This metric values has the same definition as the Base Metric value defined above.">Negligible (N)</label>
                                </div>
                                </fieldset>
                                <fieldset id="environmentalMetricGroup">
                                <legend id="environmentalMetricGroup_Legend" title="This category is usually filled by the consumer">Environmental (Security Requirements)</legend>

                                <div class="metric">
                                <h3 id="v4_CR_Heading" title="This metric enables the consumer to customize the assessment depending on the importance of the affected IT asset to the analyst’s organization, measured in terms of Confidentiality. That is, if an IT asset supports a business function for which Confidentiality is most important, the analyst can assign a greater value to Confidentiality metrics relative to Integrity and Availability.">Confidentiality Requirements (CR)</h3>
                                <input name="v4_CR" value="N" id="v4_CR_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_CR_X" id="v4_CR_X_Label" title="Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score">Not Defined (X)</label>
                                <input name="v4_CR" value="H" id="v4_CR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_CR_H" id="v4_CR_H_Label" title="Loss of Confidentiality is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization.">High (H)</label>
                                <input name="v4_CR" value="L" id="v4_CR_M" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_CR_M" id="v4_CR_M_Label" title="Loss of Confidentiality is likely to have a serious adverse effect on the organization or individuals associated with the organization.">Medium (M)</label>
                                <input name="v4_CR" value="N" id="v4_CR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_CR_L" id="v4_CR_L_Label" title="Loss of Confidentiality is likely to have only a limited adverse effect on the organization or individuals associated with the organization.">Low (L)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_IR_Heading" title="This metric enables the consumer to customize the assessment depending on the importance of the affected IT asset to the analyst’s organization, measured in terms of Integrity. That is, if an IT asset supports a business function for which Integrity is most important, the analyst can assign a greater value to Integrity metrics relative to Confidentiality and Availability.">Integrity Requirements (IR)</h3>
                                <input name="v4_IR" value="X" id="v4_IR_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_IR_X" id="v4_IR_X_Label" title="Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score">Not Defined (X)</label>
                                <input name="v4_IR" value="H" id="v4_IR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_IR_H" id="v4_IR_H_Label" title="Loss of Integrity is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization.">High (H)</label>
                                <input name="v4_IR" value="M" id="v4_IR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_IR_M" id="v4_IR_M_Label" title="Loss of Integrity is likely to have a serious adverse effect on the organization or individuals associated with the organization.">Medium (M)</label>
                                <input name="v4_IR" value="L" id="v4_IR_N" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_IR_L" id="v4_IR_L_Label" title="Loss of Integrity is likely to have only a limited adverse effect on the organization or individuals associated with the organization.">Low (L)</label>
                                </div>

                                <div class="metric">
                                <h3 id="v4_AR_Heading" title="This metric enables the consumer to customize the assessment depending on the importance of the affected IT asset to the analyst’s organization, measured in terms of Availability. That is, if an IT asset supports a business function for which Availability is most important, the analyst can assign a greater value to Availability metrics relative to Confidentiality and Integrity.">Availability Requirements (AR)</h3>
                                <input name="v4_AR" value="X" id="v4_AR_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AR_X" id="v4_AR_X_Label" title="Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score">Not Defined (X)</label>
                                <input name="v4_AR" value="H" id="v4_AR_H" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AR_H" id="v4_AR_H_Label" title="Loss of Availability is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization.">High (H)</label>
                                <input name="v4_AR" value="M" id="v4_AR_M" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AR_M" id="v4_AR_M_Label" title="Loss of Availability is likely to have a serious adverse effect on the organization or individuals associated with the organization.">Medium (M)</label>
                                <input name="v4_AR" value="L" id="v4_AR_L" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_AR_L" id="v4_AR_L_Label" title="Loss of Availability is likely to have only a limited adverse effect on the organization or individuals associated with the organization.">Low (L)</label>
                                </div>
                                </fieldset>
                                <fieldset id="threatMetricGroup">
                                <legend id="threatMetricGroup_Legend" title="This category is usually filled by the consumer">Threat Metrics</legend>

                                <div class="metric">
                                <h3 id="v4_E_Heading" title="This metric measures the likelihood of the vulnerability being attacked, and is typically based on the current state of exploit techniques, exploit code availability, or active, &quot;in-the-wild&quot; exploitation. It is the responsibility of the CVSS consumer to populate the values of Exploit Maturity (E) based on information regarding the availability of exploitation code/processes and the state of exploitation techniques. This information will be referred to as &quot;threat intelligence&quot;.">Exploit Maturity (E)</h3>
                                <input name="v4_E" value="X" id="v4_E_X" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_E_X" id="v4_E_X_Label" title="The Exploit Maturity metric is not being used.  Reliable threat intelligence is not available to determine Exploit Maturity characteristics.">Not Defined (X)</label>
                                <input name="v4_E" value="A" id="v4_E_A" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_E_A" id="v4_E_A_Label" title="Based on threat intelligence sources either of the following must apply:
· Attacks targeting this vulnerability (attempted or successful) have been reported
· Solutions to simplify attempts to exploit the vulnerability are publicly or privately available (such as exploit toolkits)">Attacked (A)</label>
                                <input name="v4_E" value="P" id="v4_E_P" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_E_P" id="v4_E_P_Label" title="Based on threat intelligence sources each of the following must apply:
· Proof-of-concept is publicly available
· No knowledge of reported attempts to exploit this vulnerability
· No knowledge of publicly available solutions used to simplify attempts to exploit the vulnerability">POC (P)</label>
                                <input name="v4_E" value="U" id="v4_E_U" type="radio" onclick="CVSS4AutoCalc()"><label for="v4_E_U" id="v4_E_U_Label" title="Based on threat intelligence sources each of the following must apply:
· No knowledge of publicly available proof-of-concept
· No knowledge of reported attempts to exploit this vulnerability
· No knowledge of publicly available solutions used to simplify attempts to exploit the vulnerability">Unreported (U)</label>
                                </div>
                                </fieldset>
                                </div>
                                """
                            ),
                        ),
                    )
                    ,
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
    """Save an individual :model:`reporting.ReportTemplate`."""

    class Meta:
        model = ReportTemplate
        exclude = ("upload_date", "last_update", "lint_result", "uploaded_by")
        widgets = {
            "document": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, user=None, *args, **kwargs):
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
        self.fields["p_style"].widget.attrs["placeholder"] = "Normal"
        self.fields["p_style"].initial = "Normal"

        clients = get_client_list(user)
        self.fields["client"].queryset = clients

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
                Column("client", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("doc_type", css_class="form-group col-md-6 mb-0"),
                Column("p_style", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("tags", css_class="form-group col-md-12 mb-0"),
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
    """Save an individual :model:`reporting.Severity`."""

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
