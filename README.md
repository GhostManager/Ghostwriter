# Ghostwriter

[![Sponsored by SpecterOps](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fspecterops%2F.github%2Fmain%2Fconfig%2Fshield.json&style=flat)](https://github.com/specterops#ghostwriter)

[![Python Version](https://img.shields.io/badge/Python-3.10-brightgreen.svg)](.) [![Django Version](https://img.shields.io/badge/Django-3.2-006400)](.) [![License](https://img.shields.io/badge/License-BSD3-darkred.svg)](.) ![GitHub Release (Latest by Date)](https://img.shields.io/github/v/release/GhostManager/Ghostwriter?label=Latest%20Release) ![GitHub Release Date](https://img.shields.io/github/release-date/ghostmanager/ghostwriter?label=Release%20Date&color=blue)

[![CodeFactor](https://img.shields.io/codefactor/grade/github/GhostManager/Ghostwriter?label=Code%20Quality)](.)  [![Code Coverage](https://img.shields.io/codecov/c/github/GhostManager/Ghostwriter?label=Code%20Coverage)](.)  [![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5139/badge)](https://bestpractices.coreinfrastructure.org/projects/5139) [![Build and Run Unit Test Workflow](https://github.com/GhostManager/Ghostwriter/actions/workflows/workflow.yml/badge.svg)](https://github.com/GhostManager/Ghostwriter/actions/workflows/workflow.yml)

[![Black Hat USA Arsenal 2019 & 2022](https://img.shields.io/badge/2019%20&%202022-Black%20Hat%20USA%20Arsenal-lightgrey.svg)](https://www.blackhat.com/us-19/arsenal/schedule/index.html#ghostwriter-15475) [![Black Hat Asia Arsenal 2022](https://img.shields.io/badge/2022-Black%20Hat%20Asia%20Arsenal-lightgrey.svg)](https://www.blackhat.com/asia-22/arsenal/schedule/index.html#ghostwriter-26252)

![ghostwriter](DOCS/images/logo.png)

Ghostwriter is an open-source platform designed to enhance offensive security operations by simplifying report writing,
asset tracking, and assessment management. It offers tools for managing clients, creating a reusable findings library,
and organizing the infrastructure and domains utilized during assessments. With its powerful reporting engine, Ghostwriter
includes comprehensive collaborative writing features and customizable report templates, allowing teams to produce polished
deliverables with minimal manual effort.

Ghostwriter comes equipped with "enterprise-level" features, such as role-based access controls, single sign-on authentication,
and multi-factor authentication. Additionally, it integrates with tools like Mythic C2 and Cobalt Strike to enable automatic
activity logging. These capabilities make Ghostwriter an ideal centralized and collaborative environment for red teams and
consultants to efficiently plan, execute, and document their assessments.

The platform effectively tracks and manages client and project information, covert infrastructure assets (such as servers
and domain names), finding templates, report templates, evidence files, and more.

This data is accessible to Ghostwriter's reporting engine, which generates comprehensive Word (DOCX) reports using Jinja2
templating and your customized report templates. Ghostwriter can also produce reports in XLSX, PPTX, and JSON formats.

Furthermore, you can leverage Ghostwriter's GraphQL API to integrate custom project management, reporting workflows,
and external tools into the platform.

## Details

Check out the introductory blogpost: [Introducing Ghostwriter](https://posts.specterops.io/introducing-ghostwriter-part-1-61e7bd014aff)

This blogpost discusses the design and intent behind Ghostwriter: [Introducing Ghostwriter: Part 2](https://posts.specterops.io/introducing-ghostwriter-part-2-f2d8368a1ed6)

## Documentation

The [Ghostwriter Wiki](https://ghostwriter.wiki/) contains everything you need to know to use or customize Ghostwriter.

The wiki covers everything from installation and setup information for first time users to database schemas, the project's
code style guide, and how to expand or customize parts of the project to fit your needs.

## Getting Help

[![Slack Status](https://img.shields.io/badge/Slack-%23ghostwriter-blueviolet?logo=slack)](https://slack.specterops.io/)

The quickest way to get help is Slack. The BloodHound Slack Team has a *#ghostwriter* channel for discussing this project
and requesting assistance. There is also a *#reporting* channel for discussing various topics related to writing and managing
reports and findings.

You can submit an issue. If you do, please use the issue template and provide as much information as possible.

Before submitting an issue, review the [Ghostwriter Wiki](https://ghostwriter.wiki/). Many of the common issues new users encounter stem from
missing an installation step or an issue with Docker on their host system.

## Contributing to the Project

The project team welcomes feedback, new ideas, and external contributions. Please open issues or submit a pull requests!
Before submitting a PR, please check open and closed issues for any previous related discussion. Also, the proposed code
must follow the [Code Style Guide](https://ghostwriter.wiki/coding-style-guide/style-guide) to be accepted.

We only ask you to limit PR submissions to those that fix a bug, enhance an existing feature, or add something new.

## Contributions

The following people at SpecterOps have contributed much to this project:

* [@ColonelThirtyTwo](https://github.com/ColonelThirtyTwo)
* [@covertgeek](https://github.com/covertgeek)
* [@hotnops](https://github.com/hotnops)
* [@andrewchiles](https://github.com/andrewchiles)

These folks kindly submitted feedback and PRs to fix bugs and enhance existing features. Thank you! 

* [@fastlorenzo](https://github.com/fastlorenzo)
* [@mattreduce](https://github.com/mattreduce)
* [@dbuentello](https://github.com/dbuentello)
* [@therealtoastycat](https://github.com/therealtoastycat)
* [@brandonscholet](https://github.com/brandonscholet)
* [@er4z0r](https://github.com/er4z0r)
* [@domwhewell](https://github.com/domwhewell)
* [@KomodoGal](https://github.com/KomodoGal)
* [@federicodotta](https://github.com/federicodotta)
* [@smcgu](https://github.com/smcgu)

## Supporters

Ghostwriter's continuous development would not be possible without [SpecterOps's](https://www.specterops.io/) commitment to transparency and
support for open-source development.
