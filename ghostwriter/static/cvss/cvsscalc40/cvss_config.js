// Copyright FIRST, Red Hat, and contributors
// SPDX-License-Identifier: BSD-2-Clause

cvssConfig = {
  "Base Metrics": {
    "fill": "supplier",
    "metric_groups": {
      "Exploitability Metrics": {
        "Attack Vector (AV)": {
          "tooltip": "This metric reflects the context by which vulnerability exploitation is possible. This metric value (and consequently the resulting severity) will be larger the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable system. The assumption is that the number of potential attackers for a vulnerability that could be exploited from across a network is larger than the number of potential attackers that could exploit a vulnerability requiring physical access to a device, and therefore warrants a greater severity.",
          "short": "AV",
          "options": {
            "Network (N)": {
              "tooltip": "The vulnerable system is bound to the network stack and the set of possible attackers extends beyond the other options listed below, up to and including the entire Internet. Such a vulnerability is often termed “remotely exploitable” and can be thought of as an attack being exploitable at the protocol level one or more network hops away (e.g., across one or more routers).",
              "value": "N"
            },
            "Adjacent (A)": {
              "tooltip": "The vulnerable system is bound to a protocol stack, but the attack is limited at the protocol level to a logically adjacent topology. This can mean an attack must be launched from the same shared proximity (e.g., Bluetooth, NFC, or IEEE 802.11) or logical network (e.g., local IP subnet), or from within a secure or otherwise limited administrative domain (e.g., MPLS, secure VPN within an administrative network zone).",
              "value": "A"
            },
            "Local (L)": {
              "tooltip": "The vulnerable system is not bound to the network stack and the attacker’s path is via read/write/execute capabilities. Either the attacker exploits the vulnerability by accessing the target system locally (e.g., keyboard, console), or through terminal emulation (e.g., SSH); or the attacker relies on User Interaction by another person to perform actions required to exploit the vulnerability (e.g., using social engineering techniques to trick a legitimate user into opening a malicious document).",
              "value": "L"
            },
            "Physical (P)": {
              "tooltip": "The attack requires the attacker to physically touch or manipulate the vulnerable system. Physical interaction may be brief (e.g., evil maid attack) or persistent.",
              "value": "P"
            }
          },
          "selected": "N"
        },
        "Attack Complexity (AC)": {
          "tooltip": "This metric captures measurable actions that must be taken by the attacker to actively evade or circumvent existing built-in security-enhancing conditions in order to obtain a working exploit. These are conditions whose primary purpose is to increase security and/or increase exploit engineering complexity. A vulnerability exploitable without a target-specific variable has a lower complexity than a vulnerability that would require non-trivial customization. This metric is meant to capture security mechanisms utilized by the vulnerable system.",
          "short": "AC",
          "options": {
            "Low (L)": {
              "tooltip": "The attacker must take no measurable action to exploit the vulnerability. The attack requires no target-specific circumvention to exploit the vulnerability. An attacker can expect repeatable success against the vulnerable system.",
              "value": "L"
            },
            "High (H)": {
              "tooltip": "The successful attack depends on the evasion or circumvention of security-enhancing techniques in place that would otherwise hinder the attack. These include: Evasion of exploit mitigation techniques, for example, circumvention of address space randomization (ASLR) or data execution prevention (DEP) must be performed for the attack to be successful; Obtaining target-specific secrets. The attacker must gather some target-specific secret before the attack can be successful. A secret is any piece of information that cannot be obtained through any amount of reconnaissance. To obtain the secret the attacker must perform additional attacks or break otherwise secure measures (e.g. knowledge of a secret key may be needed to break a crypto channel). This operation must be performed for each attacked target.",
              "value": "H"
            }
          },
          "selected": "L"
        },
        "Attack Requirements (AT)": {
          "tooltip": "This metric captures the prerequisite deployment and execution conditions or variables of the vulnerable system that enable the attack. These differ from security-enhancing techniques/technologies (ref Attack Complexity) as the primary purpose of these conditions is not to explicitly mitigate attacks, but rather, emerge naturally as a consequence of the deployment and execution of the vulnerable system.",
          "short": "AT",
          "options": {
            "None (N)": {
              "tooltip": "The successful attack does not depend on the deployment and execution conditions of the vulnerable system. The attacker can expect to be able to reach the vulnerability and execute the exploit under all or most instances of the vulnerability.",
              "value": "N"
            },
            "Present (P)": {
              "tooltip": "The successful attack depends on the presence of specific deployment and execution conditions of the vulnerable system that enable the attack. These include: a race condition must be won to successfully exploit the vulnerability (the successfulness of the attack is conditioned on execution conditions that are not under full control of the attacker, or the attack may need to be launched multiple times against a single target before being successful); the attacker must inject themselves into the logical network path between the target and the resource requested by the victim (e.g. vulnerabilities requiring an on-path attacker).",
              "value": "P"
            }
          },
          "selected": "N"
        },
        "Privileges Required (PR)": {
          "tooltip": "This metric describes the level of privileges an attacker must possess prior to successfully exploiting the vulnerability. The method by which the attacker obtains privileged credentials prior to the attack (e.g., free trial accounts), is outside the scope of this metric. Generally, self-service provisioned accounts do not constitute a privilege requirement if the attacker can grant themselves privileges as part of the attack.",
          "short": "PR",
          "options": {
            "None (N)": {
              "tooltip": "The attacker is unauthorized prior to attack, and therefore does not require any access to settings or files of the vulnerable system to carry out an attack.",
              "value": "N"
            },
            "Low (L)": {
              "tooltip": "The attacker requires privileges that provide basic capabilities that are typically limited to settings and resources owned by a single low-privileged user. Alternatively, an attacker with Low privileges has the ability to access only non-sensitive resources.",
              "value": "L"
            },
            "High (H)": {
              "tooltip": "The attacker requires privileges that provide significant (e.g., administrative) control over the vulnerable system allowing full access to the vulnerable system’s settings and files.",
              "value": "H"
            }
          },
          "selected": "N"
        },
        "User Interaction (UI)": {
          "tooltip": "This metric captures the requirement for a human user, other than the attacker, to participate in the successful compromise of the vulnerable system. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner.",
          "short": "UI",
          "options": {
            "None (N)": {
              "tooltip": "The vulnerable system can be exploited without interaction from any human user, other than the attacker.",
              "value": "N"
            },
            "Passive (P)": {
              "tooltip": "Successful exploitation of this vulnerability requires limited interaction by the targeted user with the vulnerable system and the attacker’s payload. These interactions would be considered involuntary and do not require that the user actively subvert protections built into the vulnerable system.",
              "value": "P"
            },
            "Active (A)": {
              "tooltip": "Successful exploitation of this vulnerability requires a targeted user to perform specific, conscious interactions with the vulnerable system and the attacker’s payload, or the user’s interactions would actively subvert protection mechanisms which would lead to exploitation of the vulnerability.",
              "value": "A"
            }
          },
          "selected": "N"
        }
      },
      "Vulnerable System Impact Metrics": {
        "Confidentiality (VC)": {
          "tooltip": "This metric measures the impact to the confidentiality of the information managed by the VULNERABLE SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.",
          "short": "VC",
          "options": {
            "High (H)": {
              "tooltip": "There is a total loss of confidentiality, resulting in all information within the Vulnerable System being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact. For example, an attacker steals the administrator's password, or private encryption keys of a web server.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the Vulnerable System.",
              "value": "L"
            },
            "None (N)": {
              "tooltip": "There is no loss of confidentiality within the Vulnerable System.",
              "value": "N"
            }
          },
          "selected": "N"
        },
        "Integrity (VI)": {
          "tooltip": "This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the VULNERABLE SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging).",
          "short": "VI",
          "options": {
            "High (H)": {
              "tooltip": "There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the vulnerable system. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the vulnerable system.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is limited. The data modification does not have a direct, serious impact to the Vulnerable System.",
              "value": "L"
            },
            "None (N)": {
              "tooltip": "There is no loss of integrity within the Vulnerable System.",
              "value": "N"
            }
          },
          "selected": "N"
        },
        "Availability (VA)": {
          "tooltip": "This metric measures the impact to the availability of the VULNERABLE SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system.",
          "short": "VA",
          "options": {
            "High (H)": {
              "tooltip": "There is a total loss of availability, resulting in the attacker being able to fully deny access to resources in the Vulnerable System; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the Vulnerable System (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "Performance is reduced or there are interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the Vulnerable System are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the Vulnerable System.",
              "value": "L"
            },
            "None (N)": {
              "tooltip": "There is no impact to availability within the Vulnerable System.",
              "value": "N"
            }
          },
          "selected": "N"
        }
      },
      "Subsequent System Impact Metrics": {
        "Confidentiality (SC)": {
          "tooltip": "This metric measures the impact to the confidentiality of the information managed by the SUBSEQUENT SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.",
          "short": "SC",
          "options": {
            "High (H)": {
              "tooltip": "There is a total loss of confidentiality, resulting in all resources within the Subsequent System being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact. For example, an attacker steals the administrator's password, or private encryption keys of a web server.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the Subsequent System.",
              "value": "L"
            },
            "None (N)": {
              "tooltip": "There is no loss of confidentiality within the Subsequent System or all confidentiality impact is constrained to the Vulnerable System.",
              "value": "N"
            }
          },
          "selected": "N"
        },
        "Integrity (SI)": {
          "tooltip": "This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the SUBSEQUENT SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging).",
          "short": "SI",
          "options": {
            "High (H)": {
              "tooltip": "There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the Subsequent System. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the Subsequent System.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is limited. The data modification does not have a direct, serious impact to the Subsequent System.",
              "value": "L"
            },
            "None (N)": {
              "tooltip": "There is no loss of integrity within the Subsequent System or all integrity impact is constrained to the Vulnerable System.",
              "value": "N"
            }
          },
          "selected": "N"
        },
        "Availability (SA)": {
          "tooltip": "This metric measures the impact to the availability of the SUBSEQUENT SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system.",
          "short": "SA",
          "options": {
            "High (H)": {
              "tooltip": "There is a total loss of availability, resulting in the attacker being able to fully deny access to resources in the Subsequent System; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the Subsequent System (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "Performance is reduced or there are interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the Subsequent System are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the Subsequent System.",
              "value": "L"
            },
            "None (N)": {
              "tooltip": "There is no impact to availability within the Subsequent System or all availability impact is constrained to the Vulnerable System.",
              "value": "N"
            }
          },
          "selected": "N"
        }
      }
    }
  },
  "Supplemental Metrics": {
    "fill": "supplier",
    "metric_groups": {
      "": {
        "Safety (S)": {
          "tooltip": "When a system does have an intended use or fitness of purpose aligned to safety, it is possible that exploiting a vulnerability within that system may have Safety impact which can be represented in the Supplemental Metrics group. Lack of a Safety metric value being supplied does NOT mean that there may not be any Safety-related impacts.",
          "short": "S",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "Negligible (N)": {
              "tooltip": "Consequences of the vulnerability meet definition of IEC 61508 consequence category \"negligible.\"",
              "value": "N"
            },
            "Present (P)": {
              "tooltip": "Consequences of the vulnerability meet definition of IEC 61508 consequence categories of \"marginal,\" \"critical,\" or \"catastrophic.\"",
              "value": "P"
            }
          },
          "selected": "X"
        },
        "Automatable (AU)": {
          "tooltip": "The “ The “Automatable” metric captures the answer to the question ”Can an attacker automate exploitation events for this vulnerability across multiple targets?” based on steps 1-4 of the kill chain [Hutchins et al., 2011]. These steps are reconnaissance, weaponization, delivery, and exploitation.",
          "short": "AU",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "No (N)": {
              "tooltip": "Attackers cannot reliably automate all 4 steps of the kill chain for this vulnerability for some reason. These steps are reconnaissance, weaponization, delivery, and exploitation.",
              "value": "N"
            },
            "Yes (Y)": {
              "tooltip": "Attackers can reliably automate all 4 steps of the kill chain. These steps are reconnaissance, weaponization, delivery, and exploitation (e.g., the vulnerability is “wormable”).",
              "value": "Y"
            }
          },
          "selected": "X"
        },
        "Recovery (R)": {
          "tooltip": "Recovery describes the resilience of a system to recover services, in terms of performance and availability, after an attack has been performed.",
          "short": "R",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "Automatic (A)": {
              "tooltip": "The system recovers services automatically after an attack has been performed.",
              "value": "A"
            },
            "User (U)": {
              "tooltip": "The system requires manual intervention by the user to recover services, after an attack has been performed.",
              "value": "U"
            },
            "Irrecoverable (I)": {
              "tooltip": "The system services are irrecoverable by the user, after an attack has been performed.",
              "value": "I"
            }
          },
          "selected": "X"
        },
        "Value Density (V)": {
          "tooltip": "Value Density describes the resources that the attacker will gain control over with a single exploitation event.",
          "short": "V",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "Diffuse (D)": {
              "tooltip": "The vulnerable system has limited resources. That is, the resources that the attacker will gain control over with a single exploitation event are relatively small. An example of Diffuse (think: limited) Value Density would be an attack on a single email client vulnerability.",
              "value": "D"
            },
            "Concentrated (C)": {
              "tooltip": "The vulnerable system is rich in resources. Heuristically, such systems are often the direct responsibility of \“system operators\” rather than users. An example of Concentrated (think: broad) Value Density would be an attack on a central email server.",
              "value": "C"
            }
          },
          "selected": "X"
        },
        "Vulnerability Response Effort (RE)": {
          "tooltip": "The intention of the Vulnerability Response Effort metric is to provide supplemental information on how difficult it is for consumers to provide an initial response to the impact of vulnerabilities for deployed products and services in their infrastructure. The consumer can then take this additional information on effort required into consideration when applying mitigations and/or scheduling remediation.",
          "short": "RE",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "Low (L)": {
              "tooltip": "The effort required to respond to a vulnerability is low/trivial. Examples include: communication on better documentation, configuration workarounds, or guidance from the vendor that does not require an immediate update, upgrade, or replacement by the consuming entity, such as firewall filter configuration.",
              "value": "L"
            },
            "Moderate (M)": {
              "tooltip": "The actions required to respond to a vulnerability require some effort on behalf of the consumer and could cause minimal service impact to implement. Examples include: simple remote update, disabling of a subsystem, or a low-touch software upgrade such as a driver update.",
              "value": "M"
            },
            "High (H)": {
              "tooltip": "The actions required to respond to a vulnerability are significant and/or difficult, and may possibly lead to an extended, scheduled service impact.  This would need to be considered for scheduling purposes including honoring any embargo on deployment of the selected response. Alternatively, response to the vulnerability in the field is not possible remotely. The only resolution to the vulnerability involves physical replacement (e.g. units deployed would have to be recalled for a depot level repair or replacement). Examples include: a highly privileged driver update, microcode or UEFI BIOS updates, or software upgrades requiring careful analysis and understanding of any potential infrastructure impact before implementation. A UEFI BIOS update that impacts Trusted Platform Module (TPM) attestation without impacting disk encryption software such as Bit locker is a good recent example. Irreparable failures such as non-bootable flash subsystems, failed disks or solid-state drives (SSD), bad memory modules, network devices, or other non-recoverable under warranty hardware, should also be scored as having a High effort.",
              "value": "H"
            }
          },
          "selected": "X"
        },
        "Provider Urgency (U)": {
          "tooltip": "To facilitate a standardized method to incorporate additional provider-supplied assessment, an optional “pass-through” Supplemental Metric called Provider Urgency is available. Note: While any assessment provider along the product supply chain may provide a Provider Urgency rating. The Penultimate Product Provider (PPP) is best positioned to provide a direct assessment of Provider Urgency.",
          "short": "U",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "Clear": {
              "tooltip": "Provider has assessed the impact of this vulnerability as having no urgency (Informational).",
              "value": "Clear"
            },
            "Green": {
              "tooltip": "Provider has assessed the impact of this vulnerability as having a reduced urgency.",
              "value": "Green"
            },
            "Amber": {
              "tooltip": "Provider has assessed the impact of this vulnerability as having a moderate urgency.",
              "value": "Amber"
            },
            "Red": {
              "tooltip": "Provider has assessed the impact of this vulnerability as having the highest urgency.",
              "value": "Red"
            }
          },
          "selected": "X"
        }
      }
    }
  },
  "Environmental (Modified Base Metrics)": {
    "fill": "consumer",
    "metric_groups": {
      "Exploitability Metrics": {
        "Attack Vector (MAV)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric reflects the context by which vulnerability exploitation is possible. This metric value (and consequently the resulting severity) will be larger the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable system. The assumption is that the number of potential attackers for a vulnerability that could be exploited from across a network is larger than the number of potential attackers that could exploit a vulnerability requiring physical access to a device, and therefore warrants a greater severity.",
          "short": "MAV",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "Network (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            },
            "Adjacent (A)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "A"
            },
            "Local (L)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "L"
            },
            "Physical (P)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "P"
            }
          },
          "selected": "X"
        },
        "Attack Complexity (MAC)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric captures measurable actions that must be taken by the attacker to actively evade or circumvent existing built-in security-enhancing conditions in order to obtain a working exploit. These are conditions whose primary purpose is to increase security and/or increase exploit engineering complexity. A vulnerability exploitable without a target-specific variable has a lower complexity than a vulnerability that would require non-trivial customization. This metric is meant to capture security mechanisms utilized by the vulnerable system.",
          "short": "MAC",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "Low (L)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "L"
            },
            "High (H)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "H"
            }
          },
          "selected": "X"
        },
        "Attack Requirements (MAT)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric captures the prerequisite deployment and execution conditions or variables of the vulnerable system that enable the attack. These differ from security-enhancing techniques/technologies (ref Attack Complexity) as the primary purpose of these conditions is not to explicitly mitigate attacks, but rather, emerge naturally as a consequence of the deployment and execution of the vulnerable system.",
          "short": "MAT",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "None (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            },
            "Present (P)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "P"
            }
          },
          "selected": "X"
        },
        "Privileges Required (MPR)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric describes the level of privileges an attacker must possess prior to successfully exploiting the vulnerability. The method by which the attacker obtains privileged credentials prior to the attack (e.g., free trial accounts), is outside the scope of this metric. Generally, self-service provisioned accounts do not constitute a privilege requirement if the attacker can grant themselves privileges as part of the attack.",
          "short": "MPR",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "None (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            },
            "Low (L)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "L"
            },
            "High (H)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "H"
            }
          },
          "selected": "X"
        },
        "User Interaction (MUI)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric captures the requirement for a human user, other than the attacker, to participate in the successful compromise of the vulnerable system. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner.",
          "short": "MUI",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "None (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            },
            "Passive (P)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "P"
            },
            "Active (A)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "A"
            }
          },
          "selected": "X"
        }
      },
      "Vulnerable System Impact Metrics": {
        "Confidentiality (MVC)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the confidentiality of the information managed by the VULNERABLE SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.",
          "short": "MVC",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "High (H)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "L"
            },
            "None (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            }
          },
          "selected": "X"
        },
        "Integrity (MVI)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the VULNERABLE SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging).",
          "short": "MVI",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "High (H)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "L"
            },
            "None (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            }
          },
          "selected": "X"
        },
        "Availability (MVA)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the availability of the VULNERABLE SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system.",
          "short": "MVA",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "High (H)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "L"
            },
            "None (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            }
          },
          "selected": "X"
        }
      },
      "Subsequent System Impact Metrics": {
        "Confidentiality (MSC)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the confidentiality of the information managed by the SUBSEQUENT SYSTEM due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.",
          "short": "MSC",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "": {
            },
            "High (H)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "L"
            },
            "Negligible (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            },
          },
          "selected": "X"
        },
        "Integrity (MSI)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information. Integrity of the SUBSEQUENT SYSTEM is impacted when an attacker makes unauthorized modification of system data. Integrity is also impacted when a system user can repudiate critical actions taken in the context of the system (e.g. due to insufficient logging). In addition to the logical systems defined for System of Interest, Subsequent Systems can also include impacts to humans.",
          "short": "MSI",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "Safety (S)": {
              "tooltip": "The exploited vulnerability will result in integrity impacts that could cause serious injury or worse (categories of \"Marginal\" or worse as described in IEC 61508) to a human actor or participant.",
              "value": "S"
            },
            "High (H)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "L"
            },
            "Negligible (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            }
          },
          "selected": "X"
        },
        "Availability (MSA)": {
          "tooltip": "These metrics enable the consumer analyst to override individual Base metric values based on specific characteristics of a user’s environment. This metric measures the impact to the availability of the SUBSEQUENT SYSTEM resulting from a successfully exploited vulnerability. While the Confidentiality and Integrity impact metrics apply to the loss of confidentiality or integrity of data (e.g., information, files) used by the system, this metric refers to the loss of availability of the impacted system itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of a system. In addition to the logical systems defined for System of Interest, Subsequent Systems can also include impacts to humans.",
          "short": "MSA",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The metric has not been evaluated.",
              "value": "X"
            },
            "Safety (S)": {
              "tooltip": "The exploited vulnerability will result in availability impacts that could cause serious injury or worse (categories of \"Marginal\" or worse as described in IEC 61508) to a human actor or participant.",
              "value": "S"
            },
            "High (H)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "H"
            },
            "Low (L)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "L"
            },
            "Negligible (N)": {
              "tooltip": "This metric values has the same definition as the Base Metric value defined above.",
              "value": "N"
            }
          },
          "selected": "X"
        }
      }
    }
  },
  "Environmental (Security Requirements)": {
    "fill": "consumer",
    "metric_groups": {
      "": {
        "Confidentiality Requirements (CR)": {
          "tooltip": "This metric enables the consumer to customize the assessment depending on the importance of the affected IT asset to the analyst’s organization, measured in terms of Confidentiality. That is, if an IT asset supports a business function for which Confidentiality is most important, the analyst can assign a greater value to Confidentiality metrics relative to Integrity and Availability.",
          "short": "CR",
          "options": {
            "Not Defined (X)": {
              "tooltip": "Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score",
              "value": "X"
            },
            "High (H)": {
              "tooltip": "Loss of Confidentiality is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization.",
              "value": "H"
            },
            "Medium (M)": {
              "tooltip": "Loss of Confidentiality is likely to have a serious adverse effect on the organization or individuals associated with the organization.",
              "value": "M"
            },
            "Low (L)": {
              "tooltip": "Loss of Confidentiality is likely to have only a limited adverse effect on the organization or individuals associated with the organization.",
              "value": "L"
            }
          },
          "selected": "X"
        },
        "Integrity Requirements (IR)": {
          "tooltip": "This metric enables the consumer to customize the assessment depending on the importance of the affected IT asset to the analyst’s organization, measured in terms of Integrity. That is, if an IT asset supports a business function for which Integrity is most important, the analyst can assign a greater value to Integrity metrics relative to Confidentiality and Availability.",
          "short": "IR",
          "options": {
            "Not Defined (X)": {
              "tooltip": "Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score",
              "value": "X"
            },
            "High (H)": {
              "tooltip": "Loss of Integrity is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization.",
              "value": "H"
            },
            "Medium (M)": {
              "tooltip": "Loss of Integrity is likely to have a serious adverse effect on the organization or individuals associated with the organization.",
              "value": "M"
            },
            "Low (L)": {
              "tooltip": "Loss of Integrity is likely to have only a limited adverse effect on the organization or individuals associated with the organization.",
              "value": "L"
            }
          },
          "selected": "X"
        },
        "Availability Requirements (AR)": {
          "tooltip": "This metric enables the consumer to customize the assessment depending on the importance of the affected IT asset to the analyst’s organization, measured in terms of Availability. That is, if an IT asset supports a business function for which Availability is most important, the analyst can assign a greater value to Availability metrics relative to Confidentiality and Integrity.",
          "short": "AR",
          "options": {
            "Not Defined (X)": {
              "tooltip": "Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score",
              "value": "X"
            },
            "High (H)": {
              "tooltip": "Loss of Availability is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization.",
              "value": "H"
            },
            "Medium (M)": {
              "tooltip": "Loss of Availability is likely to have a serious adverse effect on the organization or individuals associated with the organization.",
              "value": "M"
            },
            "Low (L)": {
              "tooltip": "Loss of Availability is likely to have only a limited adverse effect on the organization or individuals associated with the organization.",
              "value": "L"
            }
          },
          "selected": "X"
        }
      }
    }
  },
  "Threat Metrics": {
    "fill": "consumer",
    "metric_groups": {
      "": {
        "Exploit Maturity (E)": {
          "tooltip": "This metric measures the likelihood of the vulnerability being attacked, and is typically based on the current state of exploit techniques, exploit code availability, or active, \"in-the-wild\" exploitation. It is the responsibility of the CVSS consumer to populate the values of Exploit Maturity (E) based on information regarding the availability of exploitation code/processes and the state of exploitation techniques. This information will be referred to as \"threat intelligence\".",
          "short": "E",
          "options": {
            "Not Defined (X)": {
              "tooltip": "The Exploit Maturity metric is not being used.  Reliable threat intelligence is not available to determine Exploit Maturity characteristics.",
              "value": "X"
            },
            "Attacked (A)": {
              "tooltip": "Based on threat intelligence sources either of the following must apply:\n· Attacks targeting this vulnerability (attempted or successful) have been reported\n· Solutions to simplify attempts to exploit the vulnerability are publicly or privately available (such as exploit toolkits)",
              "value": "A"
            },
            "POC (P)": {
              "tooltip": "Based on threat intelligence sources each of the following must apply:\n· Proof-of-concept is publicly available\n· No knowledge of reported attempts to exploit this vulnerability\n· No knowledge of publicly available solutions used to simplify attempts to exploit the vulnerability",
              "value": "P"
            },
            "Unreported (U)": {
              "tooltip": "Based on threat intelligence sources each of the following must apply:\n· No knowledge of publicly available proof-of-concept\n· No knowledge of reported attempts to exploit this vulnerability\n· No knowledge of publicly available solutions used to simplify attempts to exploit the vulnerability",
              "value": "U"
            }
          },
          "selected": "X"
        }
      }
    }
  }
}
