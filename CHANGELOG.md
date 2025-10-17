# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [6.0.5] - 16 October 2025

### Added

* Added the option to color the background of table cells (PR #717)
  * This applies to cells in rows not flagged as header rows

### Changed

* Changed the finding form in the admin panel to include the CVSS vector field (PR #715; Fixes #704)

### Fixed

* Fixed certain invalid characters that could break report generation if copied and pasted into the editor (PR #711; Fixes #709)
* Fixed some HTML `span` elements being styled with a red font color (PR #714; Fixes #703)
* Fixed invalid CVSS vector strings from causing the finding form to not render properly (PR #710; Fixes #705)
* Fixed the configuration values for health checks on disk usage and minimum memory not being imported in the production YAML (PR #699; thanks to @smcgu for flagging)
* Fixed templates with references to white cards failing linting
* Fixed the Tiptap editor automatically converting strings into hyperlinks when it thinks they are URLs (PR #720)
  * PR #673 attempted to disable this behavior, but it was not fully effective due to Tiptap having two paths for how it handles pasted text
  * Based on feedback, this is the preferred behavior for most users, but we understand some users may want to re-enable it
  * We will explore making this configurable in a future release

## [6.0.4] - 12 September 2025

### Added

* Added GraphQL endpoints, `*_by_tag`, for several models that get all objects that include the tag passed in as the query's parameter (PR #693)
  * Results are restricted to objects to which the user has access
  * Included models are limited to OplogEntry, Finding, Observation, ReportedFinding, and ReportedObservation for now

### Fixed

* Fixed an error that occurred when saving the contents of a custom field in the collaborative editor when more than one person had to editor open (PR #694)
* Fixed an issue with saving a newly added JSON field (PR #694)
* Fixed code blocks not rendering inside Word documents if they were a part of a list item (PR #694)

## [6.0.3] - 10 September 2025

### Added

* Added font color options back to the collaborative editor (PR #662)
  * You can now change the font color using the color picker
  * The color picker supports selecting from a palette of colors or entering custom hex or RGB values

### Changed

* Increased session timeout for evidence uploads to 24 hours (up from 15 minutes) (PR #686)
  * This addresses uploads expiring when users fill out the form but then do not submit the form until later
  * This change affects evidence uploads for the collaborative editor
* Removed some redundant buttons from the observations list view (PR #685)
* Improved the collaborative editor's modals (PR #683)
  * The fields now auto-focus
  * Pressing _Enter_ will now submit the modal form

### Fixed

* Fixed handling of the JSON content in JSON extra fields with the collaborative editor (PR #679)
* Fixed the temporal and environmental scores not working properly with the CVSS v3 calculator in the collaborative editor (PR #680; Fixes #670)
* Fixed an issue with bookmark/cross-references for headers in Word documents (PR #691)

## [6.0.2] - 8 August 2025

### Changed

* Changed the Tiptap editor to disable itself when users lose their connection to the collaborative editing server
  * This change prevents users from making changes to the document when they are not connected to the server

### Fixed

* Fixed the missing evidence button in the Tiptap editor when editing extra fields on reports
* Fixed some extra fields on findings not saving correctly with collaborative editing
* Fixed the "sanitize" action on activity logs not working well with large logs

## [6.0.1] - 31 July 2025

### Added

* Added a _postgres.conf_ file for the PostgresSQL container and database
  * This file allows you to customize the PostgreSQL configuration for your Ghostwriter instance
  * The file is located in the _compose/production/postgres_ directory and can be modified as needed
* Added the option to display a global banner at the top of any page for announcements
  * The banner has a configurable title and message content
  * You can optionally include a link that will appear as "Learn more" below the message
  * There is an expiration date to make the banner stop displaying after a specified date and time
  * There is a "public" flag to allow the banner to be displayed to unauthenticated users on the login page
  * If a user dismisses the banner, the banner will stay hidden until the banner's content changes
    * Ghostwrtier tracks the dismissal in the browser's local storage, so the dismissal will not persist across browsers or devices
  * Added a documentation page for the banner configuration

### Changed

* Changed the default `MAX_CONN_AGE` value to `0` per Django's recommendations for ASGI applications
* The `MAX_CONN_AGE` value is now controlled by a `POSTGRES_CONN_MAX_AGE` environment variable
* Increased PostgreSQL's `max_connections` to `150` (up from `100`) to help accommodate increased concurrent connections
  * This may help with the increased connections that came with the new collaborative editing feature in Ghostwriter v6.0.0
* Updated the pre-built Ghostwriter CLI binaries to v0.2.27
    * This update adds a `POSTGRES_CONN_MAX_AGE` value to the _.env_ file to control the maximum age of PostgreSQL connections
* Updated the Ghostwriter CLI binaries to v0.2.28
  * This update adds the collaborative editing and development frontend servers to the `running` and `logs` commands

### Fixed

* Fixed a permissions issue with the `uploadEvidence` GraphQL mutation that prevented users from uploading evidence files unless they were a `manager` or `admin`
* Fixed collaborative editing not working for boolean custom fields
* Fixed permission errors that could occur when trying to add an observation from a search result without permission

## [6.0.0] - 23 July 2025

### Added

* Introduced collaborative editing server and client-side components for real-time form collaboration
  * This feature allows multiple users to edit the same form or field simultaneously
  * The collaborative editing experience applies to report fields, findings, and observations for now
  * We will expand this feature to other areas of Ghostwriter in future releases
* Added new JavaScript/TypeScript frontend infrastructure with React components and GraphQL integration
* Updated software dependencies to the latest versions, including Django and PostgreSQL
  * **Important**: Upgrading an existing Ghostwriter v5 installation will require upgrading the database to v16
    * Make a backup of your database before upgrading (`./ghostwriter-cli backup` or a server snapshot)
    * Run `./ghostwriter-cli down`
    * Update your release (e.g., `git pull`)
    * Run`./ghostwriter-cli pg-upgrade`
    * Run `./ghostwriter-cli containers build`

### Changed

* Replaced the TinyMCE WYSIWYG editor with the new Tiptap editor for collaborative writing
  * TinyMCE is still used in some parts of Ghostwriter that are outside the collaborative editing experience
  * This new editor looks different, but it offers all the same formatting features
  * The new editor supports collaborative editing, allowing multiple users to edit the same document simultaneously
  * You will no longer see a "Save" or "Submit" button as your work is saved automatically as part of the collaborative editing experience
  * You can now insert image evidence and see a preview of it inline with your text as you work
* Updated the Ghostwriter CLI binaries to v0.2.26
  * These binaries include a new `tagcleanup` command to help you clean up unused or duplicated tags in your Ghostwriter instance

## [5.0.12] - 18 July 2025

### Added

* Added a `createUser` mutation to the GraphQL API to allow creating new users
  * This mutation is useful for creating new users without needing to use the web interface
  * The mutation requires the `email`, `username`, `password`, `name`, and `role` fields
  * Only admins can create new users via this mutation
  * If you choose to allow managers to create users, the mutation will not allow them to create users with the manager or admin roles

## [5.0.11] - 3 July 2025

### Fixed

* Fixed an issue that prevented a new user from configuring a TOTP device on login when `Require 2FA` was checked for their account

## [5.0.10] - 18 June 2025

### Changed

* Changed the findings library filter for findings on reports to clear up confusion (Fixes #622)
  * The "Return only findings on reports that started as blank findings" used to attempt to filter findings based on the `title` field
  * That filtering was incorrect and led to results that did not align with the filters intent and tooltip
  * The filter will now further filter the results to show only findings that started as blank templates

### Fixed

* Fixed disallowing signups not working for the general signup form (i.e., not the SSO signup)

## [5.0.9] - 3 June 2025

### Added

* Added an option to exclude archived reports in the report library when viewing completed reports
* Added observation and report evidence relationships for reports in the GraphQL schema 

### Changed

* The archive task will now use the selected default templates when generating archived reports
* The archive report action will now display a confirmation prompt to confirm the action

### Fixed

* Fix archive task selecting reports to archive incorrectly
  * It should now properly archive reports of completed projects that are 90 days (default) past the project end date
  * It will now catch and log errors in the archive task and continue with other reports (Fixes #617)
* The archiving task now stops on the first exception
* Fixed the archive task not deleting evidence files (Fixes #618)


## [5.0.8] - 30 May 2025

### Added

* Added options to show and hide columns in the findings and domains libraries
  * This change allows you to customize the columns displayed in the libraries to suit your needs
  * Selections are preserved in your browser's local storage, so they will not persist across browsers or devices

### Changed

* Table sorting will now be preserved between page loads and visits
  * This change allows you to sort a table and have the sorting remain when you navigate away from the page and return
  * The sorting is stored in your browser's local storage, so it will not persist across browsers or devices

## [5.0.7] - 23 April 2025

### Changed

* Added auto-complete for tags in filter forms (e.g., domain and finding libraries)
* Added the Tags column back to the tables for the domain and finding libraries
* Made changes to optimize Word document generation
  * This is part of an ongoing effort to optimize these workflows to reduce the time it takes to generate reports, especially those with large tables (Issue #585) 

### Fixed

* Fixed default values not populating for extra fields on observations (PR #604 by @rteatea)

## [5.0.6] - 04 April 2025

### Added

* Added a new "Quickstart" card to the homepage dashboard to help guide new users
  * The card includes general information tog et started, links to the wiki, and a link to the Ghostwriter community
  * Users can hide the card with the button on the card

### Changed

* Numerous user interface and user experience (UI/UX) enhancements
* Reduced table sizes to improve readability
  * Some table columns (e.g., notes and additional information unneeded for sorting) have moved into informational modals
  * You can open the modals by clicking the "i" icon in the table row
* Library filters are now inside collapsible sections to reduce clutter
  * If you prefer the filters always be accessible, their collapsed status is now tracked in your browser's local storage
  * If you open a filter, all filters will be open by default until you close them
* Selecting a report to edit from the sidebar will no longer redirect you to the report
  * We added the redirect to remove a click long ago, but this made it difficult to manage multiple reports
  * Now, selecting a report will swap reports and allow you to continue selecting findings in the library without a redirect
* Modified the homepage dashboard to show more relevant information and provide user guidance
  * We will continue to improve the homepage dashboard in future releases based on feedback

### Fixed

* Fixed report template "Upload Date" changing whenever the template was updated without changing the template file

## [5.0.5] - 14 March 2025

### Added

* Added a setting on report templates to control the width of evidence files for Microsoft Word reports (PR #597)
  * The default is still Word's standard 6.5" width
  * The setting allows you to adjust the width to fit your needs

## [5.0.4] - 13 March 2025

### Added

* Added a filter to the findings library to show only findings on reports that have not been created in or cloned to the library
  * While filtering with "Search findings on reports" you can select "Return only findings on reports & not in the library"

### Fixed

* Fixed table sorting on activity logs

## [5.0.3] - 28 February 2025

### Added

* Added objective result fields to the GraphQL schema and reporting engine
  * Objectives now have `result` and `result_rt` fields that can be used in report templates
  * The `result` field can now be updated via the GraphQL API

## [5.0.2] - 24 February 2025

### Fixed

* Fixed an issue with creating clients and projects when providing optional form data (e.g., invites, contacts, assignments)

## [5.0.1] - 13 February 2025

### Added

* Added a finding type label below the finding's title on the finding details page
* Added links to profile pages for users from the project library
* Added a table of active project assignments to the user profile page
  * This table is viewable by the user and managers

### Fixed

* Fixed an error that could occur when trying to edit an observation without permissions

## [5.0.0] - 7 February 2025

### Added

* Managers now have the ability to invite users to view a client or project from the client and project dashboards
* Added the `DATABASE_URL` variable to the Django container's environment (Fixes #578)

### Changed

* This release changes role-based access controls in the web UI to match the GraphQL API's stricter controls
  * Users with the standard `user` role will no longer be able to see or access projects to which they are not assigned
  * These users will be able to see a client has other past or current projects, but will be unable to see the details of those projects
  * Admins and managers can grant a user access to a client or project by inviting them from the client or project dashboards
* Fixed the WYSIWYG editor not working for custom Rich Text fields added to the log entry model
* Added tags to the autocomplete results when searching for findings and observations (Closes #582)
* Added autocomplete to client and project filters

## [4.3.11] - 8 January 2025

### Changed

* Updated the pre-built Ghostwriter CLI binaries to v0.2.22

## [4.3.10] - 3 January 2025

### Added

* Added a `HASURA_GRAPHQL_SERVER_HOSTNAME` for the DotEnv file to allow for setting the Hasura server hostname (Fixes #566)
  * This is available for Kubernetes deployments (see issue #566)
  * For all other deployments, the Hasura server hostname should be left set to `graphql_engine` by default

### Changed

* The linter now checks if the list styles are of type `PARAGRAPH` in the Word template
* The archived reports page now displays the project name for each report to help with identification
* Updated the pre-built Ghostwriter CLI binaries to v0.2.21

## [4.3.9] - 10 December 2024

### Changed

* Evidence previews for custom fields and evidence detail pages now display evidence at 6.5" wide to mimic the standard full-width seen in a Word document

### Fixed

* Fixed an issue that could cause improper casing for the first word in a caption

## [4.3.8] - 6 December 2024

### Added

* Added buttons to jump to a selected template from the report dashboard

### Changed

* Enabled pasting with formatting in the WYSIWYG editor
  * This change allows you to paste formatted text from other sources (e.g., Word documents) into the editor
  * This caused issues in the past when pasting from Word, some terminals, and some websites, but the reporting engine seems to handle the formatting well now
  * **Note:** Pasting with formatting may not work as expected in all cases, so please check your pasted content in the editor before generating a report
* Increased the auto-complete list's maximum items from 10 to 20 to show more evidence files
* Using the "Upload Evidence" button in the editor now pushes a `ref` version of the auto-complete entry to the auto-complete list upon successful upload

### Fixed

* Fixed activity log filtering not working correctly when very large log entries were present (PR #558)

## [4.3.7] - 25 November 2024

### Fixed

* Fixed forms not accepting decimal values for extra fields (PR #554)
* Fixed cross-references not working when the reference name contained spaces (PR #556)

## [4.3.6] - 14 November 2024

### Added

* Added support for table captions in the WYSIWYG editor (PR #547)
  * Caption text can be customized by right-clicking on the table > Table Properties > General > Show caption
* Added report configuration options for figure and table caption placement (above or below) for Word

### Changed

* Production deployments now default to only exposing PostgreSQL and Hasura ports to internal services (PR #551)
  * This change is to improve security by limiting the number of exposed ports on the server
  * If you need direct access to PostgreSQL or Hasura, you can adjust the Docker Compose file to expose the ports on the host system or run a utility like `psql` inside the container

### Fixed

* Fixed observations not being cloned when cloning a report (PR #548)
* Fixed lists being styled as _List Paragraph_ in Word instead of with user-defined _Bullet List_ or _Number List_ styles (PR #550)

## [4.3.5] - 30 October 2024

### Changed

* The `added_as_blank` attribute for findings is now included in the template linter

### Fixed

* Fixed `false` values appearing as `""` in the report template context after release v4.3.4

## [4.3.4] - 24 October 2024

### Changed

* Adjusted the duplicate IP address checks for cloud servers on a project to make them more robust to catch more edge cases

### Fixed

* Fixed an issue with creating a new cloud server on a project

## [4.3.3] - 21 October 2024

### Added

* Added display for the temporal and environmental scores on the CVSS v3.1 calculator (Closes #536)
* Added a `cvss_data` key to the report context that includes the CVSS data for each finding
  * The key is a list that includes four items: the CVSS version, score(s), severity, and your configured color for the severity
  * The score and severity data includes the temporal and environmental scores for CVSS v3.1, so those scores, severities, and colors are lists (base, temporal, environmental)
  * The data is available for use in the report template

### Fixed

* Fixed values of zero (e.g., `0` or `0.0`) displaying as "No Value Set" for extra fields (Closes #541)
* Fixed a minor style issue with the sidebar

## [4.3.2] - 30 Sep 2024

### Added

* Add a `severities` key to the report context that includes a list of all severity categories in the database (Closes #427)
  * Each severity category includes the category's name, color as a hex value, color as an RGB value, color as a hex tuple, and the category's weight
  * Each entry also has a `severity_rt` RichText object  for Word that places the severity in a font color that matches the severity's color
    * This object is identical to the `severity_rt` object on findings

### Changed

* Reworked the CVSS calculators on findings to allow switching between CVSS v3/3.1 and v4 (Closes #232, #356, #387, and #509)
  * Changes include the addition of the "modified" metrics like temporal, environmental, threat, and supplemental sections
* Changed autocomplete suggestions in the WYSIWYG editor to no longer be case-sensitive (Fixes #440)

### Fixed

* Fixed archive report generation failing due to the Word template used for the PowerPoint report (PR #528)

## [4.3.1] – 25 Sep 2024

### Added

* Added a `replace_blanks` filter to the report template engine to replace blank values in a dictionary with a specified string
  * This filter is useful when sorting a list of dictionaries with an attribute that may have a blank value
* Added an option in the change search in the findings library to search findings attached to reports (Closes #400)
  * Instead of matches from the library, the search will return results for findings attached to reports to which the user has access

### Changed

* Changed the serializer for report context to replace null values with a blank string (`""`) to help prevent errors when generating reports
  * **Note:** This change may affect templates that rely on null values to trigger conditional logic, but most conditional statements should not be affected
  * **Example:** The condition `{% if not X %}` will evaluate to `True` if `X` is `None` or `""`
* Changed the report form to allow users with the `admin` or `manager` roles to change the report's project (Closes #368)
  * This change allows a report to be moved from one project to another (e.g., you make a copy for a follow-up assessment)
  * This feature is only available to users with the `admin` or `manager` roles to prevent accidental data leaks

### Fixed

* Fixed an edge case with the Namecheap sync task that could lead to a domain remaining marked as expired after re-purchasing it or renewing it during the grace period

## [4.3.0] – 23 Sep 2024

### Added

* Added two mutations to the GraphQL API to support uploading new evidence files and report template files (Closes #230)
* Added a new adapter for handling authentication for Single Sign-On (SSO) providers
  * The adapter fills-in a nearly full profile for any new accounts (full name, email address, username)
  * Usernames for new accounts will default to the first half of the email address
  * If an existing account has the same email address, the accounts will be linked
  * Review the wiki for more information: [https://www.ghostwriter.wiki/features/access-authentication-and-session-controls/single-sign-on](https://www.ghostwriter.wiki/features/access-authentication-and-session-controls/single-sign-on)
* Added support for loading customized config files
  * These are files you can use to modify settings normally found in _/config/settings/base.py_ and _production.py_
  * Admins can make changes to the custom config files without worrying about the changes needing to be stashed prior to pulling an update
  * Review this section of the wiki for information: [https://www.ghostwriter.wiki/features/access-authentication-and-session-controls/single-sign-on#configuring-an-sso-provider](https://www.ghostwriter.wiki/features/access-authentication-and-session-controls/single-sign-on#configuring-an-sso-provider)
* Added support for a JSON field type for custom fields
* Added a "Tags" column to the domain and server library tables

### Changed

* Updated the `django-allauth` module used for authentication and SSO
  * **Important:** This change impacts anyone currently using SSO with Azure
  * The `azure` provider is now `microsoft` and SSO configurations will need to be updated
* Changed the cloud infrastructure monitoring task to also check auxiliary IP addresses when determining if a cloud host is tracked in a project
* Cloud hosts tracked on a project no longer require a unique IP address
  * A warning is displayed if a cloud host is tracked on a project with multiple hosts sharing the same IP address
* Changed filtering on tags to be case-insensitive
* On the report dashboard, clicking an autocomplete suggestion for a finding or observation will now add the item to the report

### Fixed

* Fixed spaces disappearing after Microsoft Word cross-references placed at the beginning of a new line or paragraph

### [4.2.5] - 7 August 2024

### Changed

* Changed filtered activity logs to sort by the start date instead of relevancy rank 

### Fixed

* Fixed activity logs not loading additional entries when scrolling to the bottom of the page
* Fixed an issue that could cause an error when importing an activity log csv file with one or more individual cells with content exceeding 128KB

### [4.2.4] - 29 July 2024

### Changed

* Changed the "Inline Code" formatting to work for blocks of text in the WYSIWYG editor (Closes #337)
  * You can now use the "Inline Code" formatting to apply a monospace font to a block of text in the WYSIWYG editor
  * This change allows you to apply the monospace font to multiple lines of text without needing to use the TinyMCE "Code Sample" blocks
  * When Ghostwriter detects an entire line or multiple lines of text are formatted as "Inline Code," it will format them as a code block in the report template
  * This change allows for additional formatting options, like highlighting or bolding text within the code block
  * The "Code Sample" button is still present in the WYSIWYG editor if you prefer to use that for code blocks

### Fixed

* Fixed an error with template linting when the template did not have a `CodeInline` or `CodeBlock` style (Fixes #486)

## [4.2.3] - 24 July 2024

### Added

* Added support for internal hyperlinks in the WYSIWYG editor (Closes #465; thanks to @domwhewell-sage)
  * You can now create internal links to headings when you insert a hyperlink, enter `#` to start your hyperlink URL, and select a heading
  * Internal links will be converted to cross-references in the report template

### Changed

* Applied `ListParagraph` to the lists in Word reports to ensure proper paragraph styling (PR #482; thanks to @smcgu)
* The autocomplete list for keywords in reports now includes entries for `{{.ref <Evidence File Name>}}` for evidence references alongside the evidence file (e.g., `{{.<Evidence File name>}}`) (Closes #479)
* Custom fields for observations and findings now support autocomplete and have the "Upload Evidence" button (Closes #485) 

### Fixed

* Fixed an issue that could prevent reports from being generated if a related cloud server was missing a hostname (PR #481)

## [v4.2.2] - 3 July 2024

### Added

* Added a check to the template linter to ensure the `CodeInline` and `CodeBlock` styles have the correct style type (PR #474)

### Changed

* Gave every optional field in the database a default value (a blank string) to help prevent errors when creating new entries via the GraphQL API (PR #469)

### Fixed

* Fixed extra fields on findings not being processed for report generation (PR #467)
* Fixed project fields being processed twice when generating a report (PR #468)
* Fixed syntax errors that weren't being caught properly and returning generic failure messages (PR #470)
* Fixed observation tags missing from the linting data (PR #471)
* Fixed uploading evidence and autocomplete on observations (PR #472)
* Fixed a server error that could occur when using the `checkoutServer` and `checkoutDomain` mutations in the GraphQL API and providing a null value for the `note` field (PR #475)
* Fixed the "My Active Projects" sidebar dropdown not showing the correct message if all projects are marked as complete (PR #475)

## [v4.2.1] - 18 June 2024

### Changed

* Increased the filename character limit to 255 characters for evidence filenames
  * This aligns with the maximum filename length for most filesystems
  * Filenames displayed in the interface are now truncated if they are longer than 50 characters
  * The full filenames can be viewed by hovering over the filename when viewing the evidence file's details
* Changed report export errors to help further narrow down the cause of Jinja2 syntax errors
* Activity log imports now make naive timestamps timezone-aware (Closes #433 & #434)
  * If the import does not specify a timezone (e.g., _+00:00_ for UTC), the server's timezone will be used
* When coming from an activity log to import entries, the log you came from will now be selected by default
* A domain's current availability status is no longer only visible under the _Health_ tab

### Fixed

* Fixed whitespace before hyperlinks being removed in generated Word documents (Closes #461)
* Fixed an issue with how evidence displayed inside XLSX reports (Closes #462)
* Fixed extra fields on projects not being processed for project document generation

## [v4.2.0] - 10 June 2024

### Added

* Added a third template document type, Project DOCX, for project document templates
  * These templates are separate from other DOCX templates because they will have access to different context data
  * Project templates will have access to project data
  * Report templates will have access to project and report data
* Added the ability to generate project documents to the project dashboard
  * This new feature uses the new project docx templates and existing pptx templates
* Added support for templating document properties with Jinja2 in the report templates
  * You can now use Jinja2 expressions to template document properties like the title, author, and company name
  * Edit these properties inside the Word application under _File_ » _Properties_, save the document, and re-upload your template
  * Thank you, @domwhewell, for the original submission (Closes #397)
* Added template linting checks for the Heading 1-7 styles
  * These styles should always be present in a Word document but may be unidentifiable if _styles.xml_ is corrupted
* Added support for using Jinja2 in the report filename template configured under the _Global Report Configuration_ inside the admin panel
  * You can now use Jinja2 expressions to template the report filename (e.g., `{{client.name}}` or `{{now|format_datetime("Y-m-d")}}`)
  * The filename template is used when downloading a generated report
* Added options for importing and exporting observations
* Added support for Jinja2-style loops inside the WYSIWYG editor
  * You can now use Jinja2 loops to create lists, table rows, and new paragraphs
  * Use `li`, `tr`, and `p` tags with the loops–e.g., `{%li for item in items %}...{%li endfor %}`
* Added Jinja2 validation checks to the WYSIWYG editor to check if user-submitted content is valid Jinja2 code
* Added filename overrides for report templates
  * You can now set a custom filename for a report template that will override the global default filename
  * The filename supports Jinja2 templating, like the global report filename
* Added support for referencing custom fields inside other custom fields in the WYSIWYG editor
  * e.g., You can now reference another custom field or a pre-formated value like `finding.severity_rt` inside a custom field
* Added `croniter` to the Docker builds to support scheduling background tasks with Cron syntax


### Changed

* The _Reports_ tab on the project dashboard has been renamed to _Reporting_ to better reflect the new project document templates
* Exports now include an `extra_fields` column for any user-defined extra fields associated with the exported data
* Slack messages for cloud assets now include the asset's current state (e.g., Running, Stopped, etc.) (Closes #417)
* The activity log filter now searches all log entries for the log, not just the entries on the current page
  * Log entries will continue to update in real time as new entries are added
  * Only the entries that match the filter will appear until the filter is changed or cleared
* Set a default value of `{}` for extra fields to avoid errors when creating new entries via the GraphQL API with empty extra fields
* Modified error handling for report generation to provide more detailed error messages when a report fails to generate (e.g., which finding or field caused the error)
* Changed nullable database fields to no longer be nullable to prevent errors when creating new entries via the GraphQL API
* Removed the spaces before and after the figure and table prefixes to allow for flexibility (Closes #446)
  * If spaces before or after the prefix are desired, they can be added when setting the value in the report configuration
  * Current values should be updated to add spaces (if desired) – e.g., change "–" to " – "
  * Thanks to [@smcgu](https://github.com/smcgu) for the original pull request!

### Fixed

* Fixed an error that could occur when editing a finding with no editor assigned
* Fixed blank findings added to a report not having user-defined fields
* Removed the "Upload Evidence" button from report custom fields as it was not functional
  * It will be functional in a future release
* Fixed an issue with generating reports when an attached finding had a null field
* Fixed an issue with cross-references not working when special characters were present in the reference name (Fixes #444)
* Fixed issue with report generation when adjusting font sizes in the WYSIWYG editor

## [4.1] - 3 April 2024

### Added

* Added support for creating custom fields for findings, domains, servers, projects, clients, and activity log entries
  * Custom field types include text, integer, float, boolean, and formatted text
  * Custom fields can be added, edited, and deleted via the admin panel
  * Formatted text fields use the WYSIWYG editor for formatting
  * Formatting carries over to report templates like formatted text in findings
  * Custom fields are available in the report template context
  * Learn more: [https://ghostwriter.wiki/](https://ghostwriter.wiki/)
* Added support for using Jinja2 and report context data inside formatted text fields
  * You can reference `{{ client.name }}` to insert the client's name into a formatted text field
  * You can also use Jinja2 filters and functions to manipulate the data (e.g., `{{ client.name|upper }}` to make the client's name uppercase)
* Added the ability to preview formatted text fields in the interface
  * Formatted text fields can be previewed with the new "Preview" button that appears next to them in the interface
  * Any evidence referenced in the formatted text field will also be displayed in the preview (rather than just the reference text)
  * Jinja2 statements and expressions will appear as text in the preview as these must be evaluated in the report template 
* Added support for tables in the WYSIWYG editor (Closes #355)
  * Tables use the _Table Grid_ style in the Microsoft Word templates 
  * Thank you for the contribution, [@domwhewell](https://github.com/domwhewell)!
* Added support for inserting page breaks in the WYSIWYG editor
  * Page breaks carry over to the Microsoft Word templates
* Added an option to "sanitize" activity logs as an alternative to deleting them to remove sensitive information
  * Sanitizing an activity log will remove selected data from all log entries in the log
* Added a new library for "observations"
  * These observations are similar to findings but much simpler
  * The base model includes a title, description, and tags and can be used to track positive observations for a project
  * The model is also highly customizable with support for custom fields (see the first item)
* Added user permissions to control who can create, edit, and delete observations in the library
* Added support for footer information (e.g., date, footer text, and slide numbers) in the PowerPoint report templates
  * The footer information is set in your slide deck templates
* Added a configuration option for the target report delivery date
  * The target date is configured as a number of business days from the project's end date
* Added a report configuration option to enforce title case for captions
  * If enabled, this option will enforce title case for all evidence captions in a report
  * An accompanying exclusion list allows you to specify words (e.g., articles) that should not be title cased
* Added a `getExtraFieldSpec` query to the GraphQL API that returns the extra field specification for a model
  * This query is useful for extensions that need to know the extra fields available for a model
* Added a note to the WYSIWYG editor to call-out it is possible to access a browser's context menu by using CTRL+right-click
* Added a new `hostname` configuration option to the General Settings in the admin panel
  * This option allows you to set the hostname for the Ghostwriter server
  * The hostname is used to generate links in Slack notifications and other places where a link to the server is needed

### Changed

* The WYSIWYG editor's toolbar and context menu have been updated to support the new table and page break features and make it easier to apply styles
* Project and report dashboards were redesigned to improve the layout and support the new custom fields
* Report dashboards now display the global report configuration for easier reference
* Added tags to the lists of findings, domains, and servers
* Uploaded evidence files can now be linked to a report rather than a finding
  * This change allows evidence files to be used in multiple findings, and the new custom formatted text fields
* When viewing an evidence file, the file contents are now displayed in the interface as they will appear in the report
  * This change allows you to preview the evidence file's contents with your border and caption before adding it to a report
  * Border width + color and figure label come from the global report configuration in the admin panel
* PowerPoint slide decks now include "Assessment Timeline" and "Observations" slides
  * The "Assessment Timeline" slide includes a table pre-populated with the project's start date, end date, and target report delivery date
  * The "Observations" slide(s) are similar to the findings slides but for the new observations 
* Reworked the reporting engine to reduce complexity and pave the way for future enhancements
  * This is mentioned here primarily for developers and integrators who may be working with the reporting engine
* Clicking the toast notification after adding a finding to a report will now take you to the report's findings tab
* Default values for extra fields are now set when creating a new entry with empty extra fields 
  * Default values now appear in the edit forms for the entries
  * The default value must be set before creating the entry for it to appear in the form or be set as the default value
* Updated the pre-built Ghostwriter CLI binaries to v0.2.19

### Deprecated

* The old "dot" variables used in findings (e.g., `{{.project_start}}` or `{{.client}}`) are no longer necessary and will be removed in a future release
  * The "dot" variables inserted some data previously unavailable while writing a finding inside Ghostwriter
  * The new support for Jinja2 composition inside the WYSIWYG editor makes these old "dot" variables redundant
  * The "dot" variables will still work in this release but are no longer referenced in the documentation
  * This deprecation does not include `{{.ref }}` or `{{.caption }}` which will continue to be used for captioning and creating cross-references references

## [4.0.8] - 13 February 2024

### Added

* Added GraphQL events to update `deadline` and `markedComplete` fields for project objectives and tasks when these objects are updated via the GraphQL API
* Added a `filter_tags` filter to the reporting engine to allow for filtering findings and other models by their tags

### Fixed

* Fixed an issue with the template linter that could cause an error when retrieving undeclared variables under certain conditions

### Changed

* Changed the `user` relationship for `objective` to `assignedTo` in the GraphQL schema to better reflect the relationship between objectives and users

## [4.0.7] - 31 January 2024

### Fixed

* Fixed an issue with usernames with periods causing an error after login (Fixes #385)
* Fixed error that prevented using the "Clear" checkbox for the user avatar field in the admin panel (Fixes #385)

## [4.0.6] - 25 January 2024

### Fixed

* Fixed an issue with timestamps in the activity log that could cause an error when importing a csv file

### Changed

* Activity log imports and exports now include the `entry_identifier` field
* Activity log imports now check for duplicate entries based on the `entry_identifier` field and update the existing entry instead of creating a new entry

### Security

* Removed the /media location from the Nginx configuration to remove the potential for unauthorized access to uploaded files
  * Please see security advisory for details: [https://github.com/GhostManager/Ghostwriter/security/advisories/GHSA-p796-9863-mwx8](https://github.com/GhostManager/Ghostwriter/security/advisories/GHSA-p796-9863-mwx8)
* Updated Jinja2 to v3.1.3 to address CVE-2024-22195 (Reference [CVE-2024-22195](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-22195))

## [4.0.5] - 12 January 2024

### Added

* Added project contacts to the GraphQL schema
* Added user accounts to the GraphQL schema to allow more automation options for project management
  * Authenticated accounts can query name, username, email, phone number, and timezone
* Added timezone validation into PostgreSQL to prevent invalid timezones from being saved via the GraphQL API
* Added a new `generateCodename` mutation to the GraphQL API that generates a unique codename for new projects (or whatever else you want to use it for)

### Fixed

* Fixed client contacts not loading properly in the drop-down on the project dashboard

### Changed

* The `contacts` table is now `clientContact` in the GraphQL API schema for better consistency with other table names
* Updated the GraphQL schema data in _DOCS_ to reflect the latest changes
* Updated the pre-built Ghostwriter CLI binaries to v0.2.18

## [4.0.4] - 8 January 2024

### Added

* Added a new `regex_search` filter for report templates that allows you to search for a regular expression in a string

### Fixed

* Fixed an edge case where a manually edited domain could remain marked as expired on the back end and prevent checkout

### Security

* Resolved a potential XSS vulnerability with autocomplete for finding titles (Closes #374)

## [4.0.3] - 15 December 2023

### Added

* Added tracking for which VirusTotal scanners have flagged a domain as malicious to the health check task
* Added a new `entry_identifier` field to activity log entries to make it easier to identify entries when using the GraphQL API
  * The field is an open-ended text field that you can use to track a job ID, UUID, or other identifier for the entry
  * The field has no unique constraints at this time, so you can use it to track multiple entries with the same identifier
  * Logging extensions like the `cobalt_sync` project use this field to avoid duplicate entries when re-syncing
  * The field is hidden by default in the Ghostwriter web UI when viewing log entries

### Fixed

* Fixed client contacts missing from the dropdown menu after assigning a contact (Fixes #175)

### Changed

* Adjusted the wording of the reminder message sent for upcoming domain releases in Slack to make it clear the domain would remain checked out until the end of the project
* Improved the Slack message sent when domain names go from "healthy" to "burned"
* Expanded PowerPoint report generation to include new content with information about team members and objectives
* Removed character limits on log entry fields to allow for longer entries
  * This change is most useful for fields that track IP addresses
  * This resolves an issue that could arise when using the `mythic_sync` extension to sync logs with Mythic from a server host with multiple NICs and IPv6 addresses
* Updated the pre-built Ghostwriter CLI binaries to v0.2.17

## [4.0.2] - 14 November 2023

### Fixed

* Fixed a report rendering error when a report had no findings
* Fixed an issue with search autocomplete and finding titles with single quotes
* Fixed links for editing scope lists and targets accessed from the project dashboard's dropdown menus

### Changed

* The WYSIWYG editor will now automatically expand the height of the editor to fit the content as you type (up to the height of the browser window) (Closes #344)

### Security

* Updated the TinyMCE WYSIWYG editor to v5.10.8 to incorporate security fixes into Ghostwriter's self-hosted files

## [4.0.1] - 27 September 2023

### Added

* Added `short_name` and `address` fields to the company information for use in report templates (Closes #339)

### Fixed

* Fixed the activity log export returning incorrect csv files (Fixes #341)

### Changed

* Removed the restriction on backup commands that prevented them from being run on if `postgres` was set as the username (Closes #340)

## [4.0.0] - 20 September 2023

### Added

* Added a "People" tab to the project dashboard that shows the project's assignments and client contacts
* Added configuration options for managing browser sessions
  * `SESSION_COOKIE_AGE` sets the number of seconds a session cookie will last before expiring
  * `SESSION_EXPIRE_AT_BROWSER_CLOSE` sets whether the session cookie will expire when the browser is closed
  * `SESSION_SAVE_EVERY_REQUEST` sets whether the session cookie will be saved on every request
* Added support for two-factor authentication using TOTP
* Added support for adding contacts to projects
  * Supports creating project-specific contacts and adding contacts from the client
  * Project contacts appear under the new `contacts` key in the report data
  * A project contact can be flagged as the primary contact and mark the contact as the report recipient
  * The primary contact appears under the new `recipient` key in the report data 
* Added autocomplete options to filter forms for the finding, domain, and server libraries
* Added an option to copy an activity log entry to your clipboard as JSON for easier sharing
* Added an option to the `review_cloud_infrastructure()` task to only report Digital Ocean droplets that are currently running

### Changed

* Separated the project form into two forms: one for the project details and assignments and one for project components (e.g., white cards, objectives)
  * This allows accounts with the `user` role to edit project components without permission to edit the project or its assignments
* Moved project assignments to the new "People" tab on the project dashboard
* Hid menus and buttons for features that are not available to the current user
* Access to the admin console is now routed through the main login form to require 2FA (if enabled for the user)
* The CVSS Vector and "added as blank" fields on report findings are now optional as they were meant to be

### Removed

* Removed the legacy REST API deprecated in Ghostwriter v3
* Removed the unused `restricted` account role
  * This is a clean-up for the release candidate; the `restricted` role was experimental and never implemented in the access controls
* Removed the `user` role's privileges to create, edit, and delete project assignments and client contacts to better adhere to the role's intended permissions
* Removed permissions for updating report templates via the GraphQL API
  * This option will return in a future release when it is possible to upload a template file via the API

## [3.2.12] - 18 September 2023

### Added

* Added the option to configure a default paragraph style for when you do not want to use the built-in default `Normal` style (PR #307)
  * Thanks to @federicodotta  for the submission!

### Changed

* The `restore` command will now revoke open database connections to prevent errors when restoring a database backup (PR #335)
  * Thanks to @marcioalm for the submission!

## [3.2.11] - 5 September 2023

### Added

* Added CVSS and tags to the finding rows in the Excel workbook report (xlsx)

### Fixed

* Fixed the `project_type` keyword not working in report generation

## [3.2.10] - 13 July 2023

### Fixed

* Adjusted logic for marking a domain as expired when syncing with Namecheap
  * A domain marked as auto-renewable can expire, so Ghostwriter will now also mark a domain as expired and disable auto-renew if the API response has `AutoRenew` and `IsExpired` both set to `true`

## [3.2.9] - 13 June 2023

### Added

* Added CVSS and tags to the finding rows in the Excel workbook report (xlsx)

### Changed

* Added a linter error message to offer suggestions for the often confusing `expected token 'end of print statement', got 'such'` Jinja2 syntax error

### Fixed

* The linter will now recognize the `id` value on findings as valid

### Security

* Added checks to escape potential formulas in Excel workbooks
  * Please see security advisory for details: [https://github.com/GhostManager/Ghostwriter/security/advisories/GHSA-6367-mm8f-96gr](https://github.com/GhostManager/Ghostwriter/security/advisories/GHSA-6367-mm8f-96gr)

## [3.2.8] - 24 May 2023

### Added

* Added a popover tooltip to the dashboard calendar's events to show the full title and additional details about the event
* Added a `get_item` filter for use in report templates that allows you to retrieve a single item from a list of items
* Added the Sugar parser to the JavaScript to improve international date parsing

### Changed

* Assignments displayed in the calendar and on the dashboard now show the project role for the assignment (Closes #311)
* The server will now allow domains with expiration dates in the past to be checked out if auto-renew is enabled
* Updated the pre-built Ghostwriter CLI binaries to v0.2.13

### Fixed

* Fixed an issue with the domain expiration dates sorting as integers
* Fixed an issue that could prevent releasing a domain if the domain's registrar was empty

## [v3.2.7] - 1 May 2023

### Added

* Added support for exporting and importing tags for the current import/export models (log entries, domains, servers, and findings)

### Changed

* The legacy REST API key notification for new activity logs now displays the log's ID to be used with the API and extensions like `mythic_sync` and `cobalt_sync`
* When creating a new activity log from the project dashboard, that project will now be automatically selected for the new log

### Fixed

* Fixed sidebar search boxes not working as intended following changes in v3.2.3 (Closes #294)

## [v3.2.6] - 10 April 2023

### Changed

* Changed the project assignments list on the home dashboard to show the assignment's start and end dates instead of the project's start and end dates (Closes #302)

### Fixed

* Fixed an issue that would cause a server error when uploading or editing an evidence file to a blank finding (Fixes #303)

## [v3.2.5] - 31 March 2023

### Added

* A report's title can now be added to the report download filename template as a new `title` variable

### Changed

* The global report configuration can now be reviewed on the management page (_/home/management/_)

### Fixed

* Fixed an issue that prevented saving an edited activity log entry when editing a timestamps seconds value

## [v3.2.4] - 28 March 2023

## Changed

* Updated the pre-built Ghostwriter CLI binaries to v0.2.11

### Fixed

* Fixed an issue that could result in an activity log's "latest activity" timestamp to be incorrect
* Fixed a bug that toggled a reported finding's editing status from "Ready" to "Needs Editing" after saving that finding

## [v3.2.3] - 22 March 2023

### Added

* Added the option to filter the project list by the assessment type
* Added `NO_PROXY` environment variables to production containers to prevent a proxy from being used for internal container connections
* Added a `tools` key to the report template context data that contains a list of unique tools that appeared in activity log entries

### Changed

* The server will now update references to an evidence file inside the associated finding when you change that file's name
* Changed the server search form under the project dashboard's Infrastructure tab to work like the adjacent domain search form
  * The form no longer requires an exact match for an IP address
  * It is now possible to search for partial matches against one of the server's IP addresses or its hostname
  * The form will now load a list of results for review rather than take you directly to the checkout page
* Combined some fields for the domain and server filter forms on their respective library pages
  * The domain filter has combined the "Name" and "Categorization" fields
  * The server filter has combined the "Hostname" and "IP Address" fields
* Simplified the client search to a single field that searches against the client's full name, short name, and codename (Closes #294)
  * Short names are now listed alongside the full name and codename on the client list page
* Filtering by client name on the project filter page also searches against the client's full name, short name, and codename
* Copied log entries now have their start and end dates set automatically to the current timestamp
* Updated WYSIWYG editor skin to better match the rest of the interface
* Merged PR #274 to allow the option for authenticating with social accounts

### Fixed

* Fixed severity category ordering appearing reversed for new installations of v3.2.0 to v3.0.2 (Fixes #292)
* Fixed hyperlinks not being distinguishable from the regular text in notes (Closes #295)

## [v3.2.2] - 13 February 2023

### Changed

* Upgraded Ghostwriter CLI binaries to v0.2.9

### Fixed

* Fixed situations where the webpage could fail to load after submitting a client and project form with a validation error (Fixes #290)
* Fixed tags on log entries not appearing immediately in the table after adding them
* Fixed issue that prevented updating a domain

## [v3.2.1] - 7 February 2023

### Added

* Added a warning to the report form about still needing to select a template if a global default is not configured
* Added report tags to the report data as a new `tags` variable accessible in report templates

### Fixed

* Fixed a server error that could occur when attempting to add a domain that already existed in the library
* Fixed the report update form still requiring a template selection after the v3.2 changes
* Fixed the report template linter not recognizing `tags` as a valid key for objects with tags

## [v3.2.0] - 2 February 2023

### Added

* Added support for applying tags to clients, projects, reports, findings, domains, servers, logs, and log entries
* Added whitecards and deconflictions nodes to the GraphQL schema for projects
* Added a notification to finding forms that warns you if another user has submitted changes to the same finding
* Added a button to project scope forms to automatically split comma-delimited scope lists into separate lines

### Fixed

* Fixed the wrong avatar appearing in the corner when viewing another user's profile
* Fixed unnecessary scrolling animation that could occur when clicking a tab in certain browsers

### Changed

* All new log view page with improved editing functionality
  * Selections for showing/hiding a column are now persistent between page visits and refreshes
  * Editing table rows now use a modal and allows all fields to be edited and saved at once 
* The web UI now supports customizing the severity category titles
* Changed project assignments to allow the same person to be assigned more than once as long as the date ranges do not overlap
* You can clear the docx or pptx template selected for a report
  * If you clear the template, the default template will be used instead
  * If you do not have a default template configured, the report will not be able to be generated
* A domain's "reset DNS" flag will now default to true when creating a new domain
* Moved all CSS and JavaScript files to local hosting for instances where Ghostwriter is running on a system without any internet access 
* The IP address field for project targets now accepts individual IP addresses and CIDR ranges (Closes [#211](https://github.com/GhostManager/Ghostwriter/issues/211))
* Report templates can now be flagged as landscape for tracking (Reference [#281](https://github.com/GhostManager/Ghostwriter/issues/281))
* Various web UI and scripting improvements for better performance, usability, and accessibility

### Security

* Proactively upgraded core dependencies and base OS images to their latest stable versions
* Applied additional sanitization to user-editable strings that may appear in HTML to address potential XSS vulnerabilities
* Updated TinyMCE to the latest v5 to address CVE-2022-23494 (Reference [CVE-2022-23494](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-23494))

## [3.1.4] - 11 November 2022

### Fixed

* Fixed an issue with lists that caused list items to be indented incorrectly in Word documents (Fixes [#264](https://github.com/GhostManager/Ghostwriter/issues/264))

### Security

* Switched to a sandbox environment for Jinja2 to restrict access to private object attributes inside report templates (Fixes [#266](https://github.com/GhostManager/Ghostwriter/issues/266))
  * Sandbox security will be monitored and improved upon, as needed, in future releases
  * Please see security advisory for details: [https://github.com/GhostManager/Ghostwriter/security/advisories/GHSA-rpqr-g6cp-f3h2](https://github.com/GhostManager/Ghostwriter/security/advisories/GHSA-rpqr-g6cp-f3h2)

## [3.1.3] - 3 November 2022

### Added

* Added a new configuration section with the ability to set a default timezone used for forms
* Added a new option to Global Report Configuration to enable configuring default download filenames for report files

## [3.1.2] - 31 October 2022

### Fixed

* Fixed error that could cause project updates to fail when no Slack channel is set (Fixes [#261](https://github.com/GhostManager/Ghostwriter/issues/261))

### Changed

* Extended list of bad categories for domain health checks (Related to [#236](https://github.com/GhostManager/Ghostwriter/issues/236))

## [3.1.1] - 18 October 2022

### Fixed

* Fixed "added as blank" flag being cleared from a finding following an update
* Fixed initial data for `DeconflictionStatus` model missing a status option

### Changed

* Increased size of the modal for previewing log entries related to deconfliction events
* Adjusted the design of the domain and server dashboards to match the new design of the client and project dashboards

## [3.1.0] - 14 October 2022

### Fixed

* Fixed a bug that could cause content or styling to be lost inside nested text formatting

### Added

* New deconfliction event tracking feature now available under the "Deconflictions" tab on project dashboards
* New whitecard tracking feature now available under the "White Cards" tab on project dashboards

### Changed

* Findings added to a report via a blank template (i.e., not added from the library) will now appear with a flag  icon for easy identification
* All fields that use the WYSIWYG editor now have a `RichText` counterpart available in report templates (Closes [#241](https://github.com/GhostManager/Ghostwriter/issues/241))
* Improved sample "tutorial" template to cover more advanced usage of filters, variables, and more

## [3.0.7] - 10 October 2022

### Fixed

* Fixed evidence files with uppercase extensions not being included in rendered reports (Closes #74)

### Added

* Logs now have an option to mute notifications (available to users with the `admin` and `manager` roles)

### Changed

* Log activity monitor will now only check logs for projects inside the execution window
* Tweaked report template permissions to allow users with the `admin` role that are not flagged as `staff` to edit or delete protected templates

## [v3.0.6] - 3 October 2022

### Added

* Added system health API endpoints and Docker health check commands (see wiki for details)
* Added `curl` to container images to aid in troubleshooting and enable health checks

### Changed

* Calendar view selection will now persist across sessions and page refreshes
* Upgraded Ghostwriter CLI binaries to v0.2.5
* Cloning a report will now clone any evidence files associated with the findings (Thanks to @ly4k! Closes PR #234)

## [v3.0.5] - 23 September 2022

### Fixed

* Fixed finding guidance display when viewing a finding attached to a report
* Fixed connection errors with an AWS region causing remaining regions to be skipped in the cloud monitoring task

### Added

* Added an `attachFinding` mutation to the GraphQL API for easily attaching a copy of a finding from the library to a report
* Added ability to copy/paste evidence into the upload form and view a preview (Thanks to @brandonscholet! Closes PR #228)

## [3.0.4] - 12 September 2022

### Fixed

* Fixed "No entries to display" reappearing during log syncs under some circumstances

### Added

* Added Slack notification to confirm Slack configuration for a new project
* Added Slack notification for project date changes and checkout adjustments
* Added new scheduled task that checks for activity logs for active projects that have not been synced in the last 24 hours and sends a Slack notification to the project channel
* Added a _.dockeringore_ file to reduce size and build time of Docker images
* Upgraded Ghostwriter CLI binaries to v0.2.4

### Changed

* Slack alert target can now be left blank if you do not want to target a person or channel
* Completed projects will no longer appear in the list of projects for a domain checkout
* Domain health checks will now flag a domain if VirusTotal has applied the `dga` tag to it
* Slack message formatting has been improved and will no longer include very large task outputs
* Updated Nginx image to 1.23.1 to enable building it on M1 macOS machines

## [3.0.3] - 5 August 2022

### Fixed

* Removed duplicate toast message displayed after the successful creation of a new oplog
* Fixed GraphQL configuration that could cause webhook authentication to fail
* Fixed server error when trying to view entries for an oplog that does not exist

### Changed

* Groups are now hidden on the user profile unless a user is part of a group
* Adjusted client and project dashboards for better display of information and controls
* Display of client's timezone has been changed to display the client's current date and time with the abbreviated timezone name
* API keys now start with an initial expiry date that is +1 days from the current date
* Project descriptions are now truncated after 35 words to make lengthy descriptions more readable in some sections of the UI
* Infrastructure notes under the project dashboard are now inside collapsible sections for easier reading
* Upgraded Ghostwriter CLI binaries to v0.2.3

## [3.0.2] - 2 August 2022

### Fixed

* Upgraded `Pillow` dependency to avoid issue between `Pillow` and `setuptools` v63.3.0

## [3.0.1] - 1 August 2022

### Added

* Added the `CSRF_TRUSTED_ORIGINS` to the base configuration to make it easier to add trusted origins for accessing Ghostwriter via a web proxy
* Oplog ID now appears at the top of the log entries view for easier identification
* Committed Ghostwriter CLI binaries (v0.2.2) for Windows, macOS, and Linux
* Added project notes to the serialized report data as a list under `project.notes` (Closes #210)

### Changed

* Set defaults on some fields to make it easier to insert new domains, objectives, and findings via GraphQL
  * New domains will now default to WHOIS enabled, healthy, and available
  * Objectives will now default to primary priority and position one (top of the list)
  * Reported findings will now insert into position one (top of the list for its severity category)
* Log entry fields can now be null to make it easier to insert new entries via GraphQL
* Improved log entry view to make it easier to view logs
* Users with the `manager` role can now update and delete protected report templates
* User accounts can now be filtered by role in the admin panel
* Removed GraphQL `operatorName` field preset to allow this value to be set by the user

### Fixed

* Fixed "Stand by" message appearing for all users viewing a report when one user generates a report
* Fixed domain expiration dates not sorting properly in the domain table when date format is changed
* Fixed operation log entries not loading if null values were present from GraphQL submissions
* Fixed `complete` field being required for reported findings but unavailable in the GraphQL schema (Fixes #226)
* Fixed oplog entries not being displayed if they contained null values from GraphQL submissions
* Fixed log entry tables not showing "No entries to display" row when no entries are available
* Fixed an issue that could cause an error when making a new activity log with a name longer than 50 characters
* Fixed minor issue that could prevent PowerPoint generation if multiple evidence images were stacked on top of each other inside a list

## [3.0.0] - 22 June 2022

### Changed

* Committed Ghostwriter CLI binaries (v0.2.1) for Windows, macOS, and Linux

## [3.0.0-rc1] - 8 June 2022

### Added

* Committed Ghostwriter CLI binaries (v0.1.1) for Windows, macOS, and Linux
* Added support for CVSS scoring with a calculator for findings (big thanks to @therealtoastycat and PR #189)

### Changed

* Docker will now use one _.env_ file with values for all environments
  * The file is generated by Ghostwriter CLI
* Ghostwriter CLI will now be used for installation, configuration, and management of the Ghostwriter server

### Deprecated

* The individual _.env_ files stored in `.envs/` are no longer used and will be ignored by v3.x.x and later

### Removed

* Removed old environment variable templates from the project because they are no longer used for setup or management

## [2.3.0-rc2] - 3 June 2022

### Added

* New options to generate and revoke API tokens with a set expiry date
* Added Hasura GraphQL engine to production environments
* Usernames are now clickable and open the user's profile page for viewing
* Added a `generateReport` mutation to the GraphQL API capable of returning the JSON report data as a base64 string
* Added user controls for generating and revoking API tokens from the user profile page
* Added `checkoutDomain` and `checkoutServer` actions to the GraphQL API that validate checkouts
* Added `deleteDomainCheckout`, `deleteServerCheckout`, `deleteTemplate`, and `deleteEvidence` actions to the GraphQL schema that clean-up the filesystem and database after deletions

### Changed

* Updated the Nginx configuration to incorporate the Hasura container
* Updated style of the finding preview pages for the finding library
* Updated style of notes to make them cleaner and easier to manage
* Project dashboard's "Objectives" tab will now show the current number of incomplete objectives and update when toggling objectives
* Updated keyword reference panel displayed when editing findings
* Subtask forms for objectives will now default to the objective's deadline date instead of "today"
* Objective deadlines will now be automatically adjusted when the parent objective's deadline changes
* Database migrations now set default values for timestamps (current time), timezones ("America/Los_Angeles"), and boolean values (False)
  * Enables easier creation of new entries via the GraphQL API

### Deprecated

* None

### Removed

* Removed unnecessary status badges on tabs in the project dashboard that were confusing and not very helpful
* Revoked direct insert permissions for `History` and `ServerHistory` tables used for tracking domain and server checkouts

### Fixed

* Upgraded `django-bleach` dependency to fix error with latest `python-bleach` (Fixes #208)
* Fixed error that blocked creation of default `BlockQuote` style in the report template
* Fixed domain age column not sorting correctly in domain library table
* Checkbox in server form will no longer appear way bigger than intended
* Fixed issue where `<em>` tags could cause report generation to fail

### Security

* Upgraded `pyjwt` to v2.4.0 to address CVE-2022-29217

## [2.3.0-rc1] - 2022-04-01

### Added

* User profiles now have a `role` field for managing permissions in the upcoming GraphQL API
* Added components for upcoming GraphQL API that are only available with _local.yml_ for testing in development environments
  * New Docker container for Hasura GraphQL engine
  * Work-in-progress Hasura metadata for the GraphQL API
  * New `HASURA_ACTION_SECRET` environment variable in env templates
  * New utilities for generating and managing JSON Web Tokens for the GraphQL API
* Added support for block quotes in report templates and WYSIWYG editor
* Added `ProjectInvite` and `ClientInvite` models to support upcoming role-based access controls
* Added a menu option to export a project scope to a text file from the project dashboard
  * Exports only the scope list for easy use with other tools–e.g., Nmap

### Changed

* Disabled `L10N` by default in favor of using `DATE_FORMAT` for managing the server's preferred date format (closes #193)
* Updated env templates with a `DATE_FORMAT` configuration for managing your preferred format
  * See updated installation documentation on ghostwriter.wiki
* User profiles now only show the user's role, groups, and Ghostwriter user status to the profile owner
* Updated nginx.conf to align it with Mozilla's recommendations for nginx v1.21.1 and OpenSSL 1.1.1l
  * See config: [https://ssl-config.mozilla.org/#server=nginx&version=1.21.1&config=intermediate&openssl=1.1.1l&ocsp=false&guideline=5.6](https://ssl-config.mozilla.org/#server=nginx&version=1.21.1&config=intermediate&openssl=1.1.1l&ocsp=false&guideline=5.6)
* Toast messages for errors are no longer sticky, so they do not have to be manually dismissed when covering UI elements
* Domain list table now shows an "Expiry" column and "Categories" column now parses the new ``categorization`` JSON field data
* Domain list filtering now includes a "Filter Expired" toggle that on by default
  * Filters out domains with expiration dates in the past and `auto_renew` set to `False` even if status is set to "Available"
* The table on the domain list page and the menu on the domain details page will no longer disable the check-out option if a domain's status is set to "Burned"
* Simplified usage of the `format_datetime` filter
  * Filter now accepts only two arguments: the date and the new format string
  * Format string should use Django values (e.g., `M d, Y`) instead of values translated to Python's standard (e.g., `%b %d, %Y`)
* Simplified usage of the `add_says` filter
  * Filter now accepts only two arguments: the date and an integer

### Deprecated

* v2.2.x usage of the `format_datetime` and `add_days` filters is deprecated in v2.3.0
  * Both filters will no longer accept Python-style `strftime` strings
  * Both filters no longer needs or accepts the `current_format` and `format_str` parameters
  * Templates using the old style will fail linting

### Removed

* Removed "WHOIS Privacy" column on domain list page to make room for more pertinent information

### Fixed

* Bumped `djangorestframework-api-key` to v2.2.0 to fix REST API key creation (closes #197)
* Overrode Django's `get_full_name()` method used for the admin site so the user's proper full name is displayed in history logs
* Fixed project dashboard's "Import Oplog" button not pointing to the correct URL
* Fixed URL conflicts with export links for domains, servers, and findings

### Security

* Restricted edit and delete actions on notes to close possibility of other users editing or deleting notes they do not own

## [2.2.3] - 2022-02-16

### Added

* Expanded user profiles for project management and planning
  * Now visible to all users under /users/
  * Include timezone and phone number fields -Users can now edit their profiles to update their preferred name, phone, timezone, and email address

### Fixed

* Fixed display of minutes for project working hours
* Fixed "incomplete file" issue when attempting to download a report template
* Fixed report archiving failing to write zip file
* Fixed toast messages not showing up when swapping report templates
* Fixed sidebar tab appearing below delete confirmations
* Fixed cloud server forms requiring users to fill in all auxiliary IP addresses
* Fixed project serialization issue that prevented project data from loading automatically for domain and server checkout forms
* Fixed active project filtering for the list in the sidebar, so it will no longer contain some projects marked as completed
* Fixed a rare reporting error that could occur if the WYSIWYG editor created a block of nested HTML tags with no content
* Fixed ignore tags not working for Digital Ocean assets
* Fixed an error caused by cascading deletes when deleting a report under some circumstances
* Fixed template linter not recognizing phone numbers for project team members as valid (Fixes #190)
* Fixed a rare reporting issue related to nested lists that could occur if a nested list existed below an otherwise blank list item

### Changed

* Updated project list filtering
  * Added client name as a filter field
  * Changed default display filter to only show active projects
  * Adjusted project status filter to have three options: all projects, active projects, and completed projects
* Updated dashboard and calendar to show past and current events for browsing history within the calendar
  * Past events marked as completed will appear dimmed with a strike-through and `: Complete` added to the end
* Upgraded dependencies to their latest versions (where possible)
  * Django v3.1.13 -> v3.2.11
  * Did not upgrade `docxtpl`
    *  Awaiting to see how the developer wants to proceed with [issue #114](https://github.com/elapouya/python-docx-template/issues/414)
    * Not upgrading from 0.12 to the latest 0.15.2 has no effect on Ghostwriter at this time
* Collapsed the `Domain` model's various categorization fields into a single `categorization` field with PostgreSQL's `JSONField` type
  * An important milestone/change for the upcoming GraphQL API
  * Categorization is no longer limited to specific vendors
  * Going forward, the field can be manually updated with valid JSON
  * Ghostwriter will look for JSON formatted as a series of keys and values: `{"COMPANY": "CATEGORY", "COMPANY": "CATEGORY",}`
* Converted the `ReportTemplate` model's `lint_result` field to a PostgreSQL `JSONField`
  * An important milestone/change for the upcoming GraphQL API
  * This change increases reliability and performance by removing any need to transform a string representation back into a `dict`
  * Little to no impact on users but templates may need to be linted again after the upgrade
  * If a template is affected, the status will change to "Unknown" with a single warning note: "Need to re-run linting following your Ghostwriter upgrade"
* Converted the `Domain` model's `dns_record` field to a PostgreSQL `JSONField` and renamed it to `dns` for simplicity
  * An important milestone/change for the upcoming GraphQL API
  * This change increases reliability and performance by removing any need to transform a string representation back into a `dict`
  * This field was always intended to be edited only by the server, so this change should not require any actions before or after upgrading
  * If an existing record's DNS data cannot be converted to JSON it will be cleared and user's can re-run the DNS update task
* Added a "sticky" sidebar tracker to user sessions so the sidebar will stay open or closed between visits and page changes
* Removed the legacy `health_dns` field from the `Domain` model
  * This field was part of the original Shepherd project and was an interesting experiment in using passive DNS monitoring to try to determine if a domain was "burned"
  * It became mostly irrelevant when services that supported this feature (e.g., eSentire's Cymon) were retired
* Changed some code that will be deprecated in future versions of Django v4.x and Python Faker
* Made it possible to sort the report template list
  * Sorting on this table is reversed so clicking "Status" once will sort templates with passing linter checks first
* Updated the admin panel to make it easier to manage domains for those who prefer the admin panel
* Projects now sort in reverse so the most recent projects appear first
* Updated the report selection section of the sidebar to make it easier to switch reports when working on multiple and navigate to your current report
* The logging API key message now includes the project ID to make it easier to set up a tool like mythic\_sync
* Removed the "Upload Evidence" button from editors where it does not apply (e.g., in the Finding Library outside of a report) (Fixes #185)
* Updated the Namecheap sync task to use paging so Namecheap libraries with more than 100 domains can be fully synced (Fixes #188)
* Dashboard once again has a "Project Assignments" card to make it easier to see and click projects
  * The calendar remains on the dashboard and is still clickable, but some people found it less intuitive as a shortcut
* Some general code clean-up for maintainability

### Security

* Updated Django to v3.2.11 as v3.1 is no longer supported and considered "insecure" going forward
* Fixed unauthenticated access to domain and server library exports
* Updated TinyMCE to v5.10.1 to address several moderate security issues with <5.10

## [2.2.3-rc2] - 2022-02-09

### Fixed

* Fixed "incomplete file" issue when attempting to download a report template
* Fixed report archiving failing to write zip file
* Fixed toast messages not showing up when swapping report templates
* Fixed sidebar tab appearing below delete confirmations

### Changed

* Upgraded dependencies to their latest versions (where possible)
  * Django v3.1.13 -> v3.2.11
  * Did not upgrade `docxtpl`&#x20;
    * Awaiting to see how the developer wants to proceed with [issue #114](https://github.com/elapouya/python-docx-template/issues/414)
    * Not upgrading from 0.12 to the latest 0.15.2 has no effect on Ghostwriter at this time
* Collapsed the `Domain` model's various categorization fields into a single `categorization` field with PostgreSQL's `JSONField` type
  * An important milestone/change for the upcoming GraphQL API
  * Categorization is no longer limited to specific vendors
  * Going forward, the field can be manually updated with valid JSON
  * Ghostwriter will look for JSON formatted as a series of keys and values: `{"COMPANY": "CATEGORY", "COMPANY": "CATEGORY",}`
* Converted the `ReportTemplate` model's `lint_result` field to a PostgreSQL `JSONField`
  * An important milestone/change for the upcoming GraphQL API
  * This change increases reliability and performance by removing any need to transform a string representation back into a `dict`
  * Little to no impact on users but templates may need to be linted again after the upgrade
  * If a template is affected, the status will change to "Unknown" with a single warning note: "Need to re-run linting following your Ghostwriter upgrade"
* Converted the `Domain` model's `dns_record` field to a PostgreSQL `JSONField` and renamed it to `dns` for simplicity
  * An important milestone/change for the upcoming GraphQL API
  * This change increases reliability and performance by removing any need to transform a string representation back into a `dict`
  * This field was always intended to be edited only by the server, so this change should not require any actions before or after upgrading
  * If an existing record's DNS data cannot be converted to JSON it will be cleared and user's can re-run the DNS update task
* Added a "sticky" sidebar tracker to user sessions so the sidebar will stay open or closed between visits and page changes
* Removed the legacy `health_dns` field from the `Domain` model
  * This field was part of the original Shepherd project and was an interesting experiment in using passive DNS monitoring to try to determine if a domain was "burned"
  * It became mostly irrelevant when services that supported this feature (e.g., eSentire's Cymon) were retired
* Changed some code that will be deprecated in future versions of Django v4.x and Python Faker
* Made it possible to sort the report template list
  * Sorting on this table is reversed so clicking "Status" once will sort templates with passing linter checks first
* Updated the admin panel to make it easier to manage domains for those who prefer the admin panel
* Some general code clean-up for maintainability

### Security

* Updated Django to v3.2.11 as v3.1 is no longer supported and considered "insecure" going forward
* Fixed unauthenticated access to domain and server library exports

## [2.2.3-rc1] - 2022-01-28

### Added

* Expanded user profiles for project management and planning
  * Now visible to all users under /users/
  * Include timezone and phone number fields -Users can now edit their profiles to update their preferred name, phone, timezone, and email address

### Fixed

* Fixed cloud server forms requiring users to fill in all auxiliary IP addresses
* Fixed project serialization issue that prevented project data from loading automatically for domain and server checkout forms
* Fixed active project filtering for the list in the sidebar, so it will no longer contain some projects marked as completed
* Fixed a rare reporting error that could occur if the WYSIWYG editor created a block of nested HTML tags with no content
* Fixed ignore tags not working for Digital Ocean assets
* Fixed an error caused by cascading deletes when deleting a report under some circumstances
* Fixed template linter not recognizing phone numbers for project team members as valid (Fixes #190)
* Fixed a rare reporting issue related to nested lists that could occur if a nested list existed below an otherwise blank list item

### Changed

* Projects now sort in reverse so the most recent projects appear first
* Updated the report selection section of the sidebar to make it easier to switch reports when working on multiple and navigate to your current report
* The logging API key message now includes the project ID to make it easier to set up a tool like mythic\_sync
* Removed the "Upload Evidence" button from editors where it does not apply (e.g., in the Finding Library outside of a report) (Fixes #185)
* Updated the Namecheap sync task to use paging so Namecheap libraries with more than 100 domains can be fully synced (Fixes #188)
* Dashboard once again has a "Project Assignments" card to make it easier to see and click projects
  * The calendar remains on the dashboard and is still clickable, but some people found it less intuitive as a shortcut
* Some general clean-up of CSS

### Security

* Updated TinyMCE to v5.10.1 to address several moderate security issues with <5.10

## [2.2.2] - 2021-10-22

### Added

* Added new filters for report templates
  * `add_days`: Add some number of business days to a date
  * `format_datetime`: Change the format of the provided datetime string
* The cloud monitoring task can now collect information about AWS Lightsail instances and S3 buckets
* A new "Notification Delay" setting is available under the Cloud Configurations
  * This setting delays cloud infrastructure teardown notifications by X days
  * Useful if you want to run the cloud monitor task more frequently and not get teardown reminders for some period of time after a project ends
* Projects now have fields for  timezone, start time, and end time to track working hours
* Client contacts now have a timezone field
* You can now save up to three additional IP addresses for cloud servers (they are stored in an array for easy iteration)

### Fixed

* Fixed the sorting of the domain age column in the domain table
* Fixed issue with the JavaScript for deleting entries in a formset selecting other checkboxes
* Fixed `WhoisStatus` model's `count` property
* Fixed error handling that could suppress report generation error messages when generating all reports
* Fixed error that could lead to WebSocket disconnections and errors when editing the timestamp values of a log entry
* Fixed a typo in the emoji used by the default Slack message for an untracked server
* Fixed a logic issue that could result in an "ignore tag" being missed when reporting on cloud infrastructure

### Changed

* Adjusted the report data to replace a blank short name with the client's full name (rather than a blank space in a report)
* Moved some form validation logic to Django Signals in preparation for the API
* Added a custom "division by zero" error message for times when a Jinja2 template attempts to divide a value (e.g., total num of completed objectives) that is zero without first checking the value
* Bumped Toastr message opacity to `.9` (up from `.8`) to improve readability
* Bumped 50-character limit on certain `OplogEntry` values to 255 (the standard for other models)
* Condensed Docker image layers and disabled caching for `pip` and `apk` to reduce image sizes by about 0.2 to 0.3GB
* Optimized and improved code quality throughout the project based on recommendations from Code Factor ([https://www.codefactor.io/repository/github/ghostmanager/ghostwriter](https://www.codefactor.io/repository/github/ghostmanager/ghostwriter))
* Added Signals to release a checked-out server or domain if the current checkout is deleted (so it is released immediately rather than waiting for a scheduled task to run)
* When updating a project's dates, Ghostwriter will no longer update the dates on domain and server checkouts if the checkout has already expired
* If an in-use domain is flagged as "burned" by the health check task, a notification will now be sent to the project's Slack channel if a Slack channel is configured
* All core libraries have been bumped up to their latest versions and Django has been upgraded to v3.1 from v3.0

### Security

* Upgraded the Django image to Alpine v3.14 to address potential security vulnerabilities in the base image
* Upgraded Postgres image to Postgres v11.12 to address potential security vulnerabilities in previously used version/base image
* Pinned nginx image to v1.12.1 for security and stability
* Upgraded TinyMCE to v5.8.2 to address potential XSS discovered in older TinyMCE versions

## [2.2.2-rc3] - 2021-09-27

### Added

* Projects now have fields for  timezone, start time, and end time to track working hours
* User profiles and client contacts now have a timezone field
* You can now save up to three additional IP addresses for cloud servers \(they are stored in an array for easy iteration\)

## [2.2.2-rc2] - 2021-09-22

### Added

* The cloud monitoring task can now collect information about AWS Lightsail instances and S3 buckets
* A new "Notification Delay" setting is available under the Cloud Configurations
  * This setting delays cloud infrastructure teardown notifications by X days
  * Useful if you want to run the cloud monitor task more frequently and not get teardown reminders for some period of time after a project ends

### Changed

* Added Signals to release a checked-out server or domain if the current checkout is deleted \(so it is released immediately rather than waiting for a scheduled task to run\)
* If an in-use domain is flagged as "burned" by the health check task, a notification will now be sent to the project's Slack channel if a Slack channel is configured

## [2.2.2-rc1] - 2021-09-15

### Fixed

* Fixed issue with the JavaScript for deleting entries in a formset selecting other checkboxes
* Fixed `WhoisStatus` model's `count` property
* Fixed error handling that could suppress report generation error messages when generating all reports
* Fixed error that could lead to WebSocket disconnections and errors when editing the timestamp values of a log entry
* Fixed a typo in the emoji used by the default Slack message for an untracked server
* Fixed a logic issue that could result in an "ignore tag" being missed when reporting on cloud infrastructure

### Changed

* Adjusted the report data to replace a blank short name with the client's full name \(rather than a blank space in a report\)
* Moved some form validation logic to Django Signals in preparation for the API
* Added a custom "division by zero" error message for times when a Jinja2 template attempts to divide a value \(e.g., total num of completed objectives\) that is zero without first checking the value
* Bumped Toastr message opacity to `.9` \(up from `.8`\) to improve readability
* Bumped 50-character limit on certain `OplogEntry` values to 255 \(the standard for other models\)
* Condensed Docker image layers and disabled caching for `pip` and `apk` to reduce image sizes by about 0.2 to 0.3GB
* Optimized and improved code quality throughout the project based on recommendations from Code Factor \([https://www.codefactor.io/repository/github/ghostmanager/ghostwriter](https://www.codefactor.io/repository/github/ghostmanager/ghostwriter)\)

### Security

* Upgraded TinyMCE to v5.8.2 to address potential XSS discovered in older TinyMCE versions
* Upgraded the Django image to Alpine v3.14 to address potential security vulnerabilities in the base image
* Upgraded Postgres image to Postgres v11.12 to address potential security vulnerabilities in previously used version/base image
* Pinned nginx image to v1.12.1 for security and stability

## [2.2.1] - 2021-05-28

### Added

* Every page now includes a footer at the bottom of the content that displays the version number of the  Ghostwriter server.

### Fixed

* Findings with no assigned editors will no longer prevent report generation.

### Changed

* Findings in a report now have an `ordering` value that represents their position in the report \(starting at zero with the top finding in the most severe category\).
* Headings throughout the interface are no longer all caps by default \(this could negatively affect readability\).
* Some form elements will no longer appear far apart when the interface is fullscreen on a very high-resolution or wide-screen display.

## [2.2.0] - 2021-05-10

### Added

* Added new `filter_type` filter to report templates \(submitted by @5il with PR \#152\).
* Introduced the new `ReportData` serializer. This is nearly invisible to users but is a huge efficiency and performance upgrade for the back-end. Changes to project data models will now automatically appear in the raw JSON reports and be accessible within DOCX reports.
* The new serializer has modified some Jinja2 template expressions. View a JSON report to see everything available. For example, instead of writing `{{ project_codename }}`, you will access this project value with `{{ project.codename }}`.
* Ghostwriter now handles dates differently to better support all international date formats. Dates displayed in the interface and dates within reports \(e.g., `report_date`\) will match the date locale set in your server settings \(`en-us` by default\).

### Fixed

* Updated broken POC contact edit URL on the client details page
* Project assignment dates will no longer be improperly adjusted on updates
* Template linter context now has entries for new RichText objects
* Adjusted HTML parser to account for the possibility for empty fields following an update from one of the older versions of Ghostwriter  \(submitted by @Abstract-9 with PR \#158\)
* Adjusted Dockerfile files to fix potential filesystem issues with the latest Alpine Linux image \(submitted by @studebacon with PR \#143\).
* Added a missing field in the Report Template admin panel
* "Add to Report" on the finding details page now works
* Updated delete actions for operation logs to avoid an error that could prevent the deletion of entries when deleting an entire log
* Domain age calculations are now accurate
* An invalid value for domain purchase date no longer causes a server error during validation
* Constrained `Twisted` library to v20.3.0 to fix a potential issue that could come up with Django Channels
  * [https://github.com/django/channels/issues/1639](https://github.com/django/channels/issues/1639)
* Improved the reporting engine to handle even the wildest nested styling

### Changed

* Adjusted finding severity lists to sort by the severity's weight instead of alphabetically.
* Re-enabled evidence uploads in all WYSIWYG editors \(it was previously excluded from certain finding fields\).
* Adjusted sidebar organization to improve visibility of a few sections that could be difficult to locate.
* Updated BootStrap and FontAwesome CSS versions.
* Updated all Python libraries to their latest versions.
* Animated the hamburger menus for fun.
* Switched ASGI servers \(from Daphne server to Uvicorn\) for WebSockets and better performance.
* Updated the sample _template.docx_ to act as a walkthrough for the new report data and changes in Jinja2 expressions.

## [2.2.0-rc2] - 2022-04-13

### Added

* Introduced the new `ReportData` serializer. This is nearly invisible to users but is a huge efficiency and performance upgrade for the back-end. Changes to project data models will now automatically appear in the raw JSON reports and be accessible within DOCX reports.
* The new serializer has modified some Jinja2 template expressions. View a JSON report to see everything available. For example, instead of writing `{{ project_codename }}`, you will access this project value with `{{ project.codename }}`.
* Ghostwriter now handles dates differently to better support all international date formats. Dates displayed in the interface and dates within reports \(e.g., `report_date`\) will match the date locale set in your server settings \(`en-us` by default\).

### Fixed

* Added a missing field in the Report Template admin panel.
* "Add to Report" on the finding details page now works.
* Updated delete actions for operation logs to avoid an error that could prevent the deletion of entries when deleting an entire log.
* Domain age calculations are now accurate.
* An invalid value for domain purchase date no longer causes a server error during validation.
* Constrained `Twisted` library to v20.3.0 to fix a potential issue that could come up with Django Channels
  * [https://github.com/django/channels/issues/1639](https://github.com/django/channels/issues/1639)
* Improved the reporting engine to handle even the wildest nested styling.

### Changed

* Adjusted finding severity lists to sort by the severity's weight instead of alphabetically.
* Re-enabled evidence uploads in all WYSIWYG editors \(it was previously excluded from certain finding fields\).
* Adjusted sidebar organization to improve visibility of a few sections that could be difficult to locate.
* Updated BootStrap and FontAwesome CSS versions.
* Updated all Python libraries to their latest versions.
* Animated the hamburger menus for fun.
* Switched ASGI servers \(from Daphne server to Uvicorn\) for WebSockets and better performance.
* Updated the sample _template.docx_ to act as a walkthrough for the new report data and changes in Jinja2 expressions.

## [2.1.1] - 2021-03-05

### Fixed

* Fixed server error when trying to create a new project with an assignment or objective
* Fixed edge case that could cause a new task below an objective to be duplicated
* Fixed edge case that would flag a project target form as invalid if it had a note and did not also have both an IP address and hostname
* Fixed toggle arrow working in reverse when a user marks an objective complete while tasks are expanded

### Changed

* Made it so objective completion percentage updates when a new task is added or deleted
* Made it possible to use `@` targets for Slack channels instead of only `#` channels
* The `uploaded_by` values are now set on report templates on the server-side

## [2.1] - 2021-03-03

### Added

* Implemented project scope tracking (closes #59)
    * Enabled tracking of one or more scope lists flagged as allowed/disallowed or requiring caution
* Implemented project target tracking
    * Enabled tracking of specific hosts with notes
* Committed redesigned project dashboards
    * Notable changes and adjustments:
        * Added a project calendar to track assignments, objectives, tasks, and project dates
        * Added new objective tracker with task management, prioritization, and sorting
* Implemented a new server search in the sidebar (under _Servers_) that searches all static servers, cloud servers in projects, and alternate addresses tied to servers
* Added template linting checks for additional styles that may not be present in a report (closes #139)
* Added Clipboard.js to support better, more flexible "click to copy to clipboard" in the UI
* Added several new Jinja2 expressions, statements, and filters for Word DOCX reports
    * Added `project_codename` and `client_codename` (closes #138)
    * Added expressions and filters for new objectives, targets, and scope lists
    * See wiki documentation
* Implemented initial support for WebSocket channels for reports

### Changed

* Tagged release, v2.1
    * Release will require database migrations
    * New features will require reloading the `seed_data` file
        * e.g., `docker-compose -f local.yml run --rm django /seed_data`
* Improved page loading with certain large forms
    * WYSIWYG editor is now loaded much more selectively
    * Extra forms are no longer created by default when _editing_ a project or client
        * Extra forms can still be added as needed
        * Extra forms still load automatically when _creating_ a new project or client
* Improved performance of operation log entry views with pagination
    * Very large logs could push browsers to their limits

### Fixed

* Fixed downloads of document names that included periods and commas (closes #149)
* Fixed evidence filenames with all uppercase extensions not appearing in reports (closes #74)
* Fixed a recursive HTML/JavaScript escape in log entries (closes #133)
* Fixed incorrect link in the menu for a point of contact under a client (closed #141 and #141)
* Fixed `docker-compose` errors related to latest version of the `cryptography` library (closes #147)
* Fixed possible issue with assigning a name to an AWS asset in the cloud monitor task
* Closed loophole that could allow a non-unique domain name

### Security

* Updated TinyMCE WYSIWYG editor and related JavaScript to v5.7.0
    * Resolved potential Cross-Site Scripting vulnerability discovered in previous version

## [2.0.2] - 2021-01-15

### Changed

* Added error handling for cases where an image file has a corrupted file header and can't be recognized for inserting into Word
* Moved 99% of icons and style elements to the _styles.css_ file

### Fixed

* Fixed notifications going to the global Slack channel when project channels were available
* Fixed uppercase file extensions blocking evidence files from appearing on pages
* Fixed rare `style` exception with specific nested HTML elements

## [2.0.2] - 2020-12-18

### Changed

* Updated styles and forms to make it clear what is placeholder text
* Reverted the new finding form to a one-page form–i.e., no tabbed sections–to make it easier to use
* Broke-up stylesheets for easier management of global variables

### Fixed

* Fixed error in cloud monitor notification messages that caused messages to contain the same external IP addresses for all VPS instances
* Fixed bug that caused delete actions on cloud server entries to not be committed
* Fixed `ref` tags in findings that were ignored if they followed a `ref` tag with a different target
* Fixed PowerPoint "Conclusion" slide's title
* Fixed filtering for report template selection dropdowns that caused both document types to appear in all dropdown menus

## [2.0.1] - 2020-12-03

### Added

* Added project objectives to the report template variables
    * New template keywords: `objectives` (List), `objectives_total` (Int), `objectives_complete` (Int)

### Changed

* Modified project "complete" toggle and instructions for clarity
* Set all domain names to lowercase and strip any spaces before creating or updating
    * Addressed cases where a user error could create a duplicate entry
* Clicking prepended text (e.g., filter icon) on filter form fields will now submit the filter

### Fixed

* Fixed error that could cause Oplog entries to not display
* Oplog entries list now shows loading messages and properly displays "no entries" messages
* Fixed incorrect filenames for CSV exports of Oplogs

## [2.0.0] - 2020-11-20

### Added

* Initial commit of CommandCenter application and related configuration options
    * VirusTotal Configuration
    * Global Report Configuration
    * Slack Configuration
    * Company information
    * Namecheap Configuration
* Initial support for adding users to groups for Role-Based Access Controls
* Automated Activity Logging (Oplog application) moved out of beta
* Implemented initial "overwatch" notifications
    * Domain check-out: alert if domain will expire soon and is not set to auto-renew
    * Domain check-out: alert if domain is marked as burned
    * Domain check-out: alert if domain has been previously used with selected client

### Changed

* Upgraded to Django 3 and updated all dependencies
* Updated user interface elements
    * New tabbed dashboards for clients, projects, and domains
    * New inline forms for creating and managing clients and projects and related items
    * New sidebar menu to improve legibility
    * Migrated buttons and background tasks to WebSockets and AJAX for a more seamless experience
* Initial release of refactored reporting engine (closes #89)
    * New drag-and-drop report management interface
    * Added many more options to the WYSIWYG editor's formatting menus
    * Initial support for rich text objects for Word documents
    * Added new `filter_severity` filter for Word templates
* Initial support for report template and management (closes #28 and #90)
    * Upload report template files for Word and PowerPoint
    * New template linter to check and verify templates
* Removed web scraping from domain health checks (closed #50 and #84)
    * Checks now use VirusTotal and link to the results
* Numerous bug fixes and enhancements to address reported issues (closes #54, #55, #69, #92, #93, and #98)

### Security

* Resolved potential stored cross-site scripting in operational logs
* Resolved unvalidated evidence file uploads and new note creation
    * Associated user account is now set server-side
* Resolved issues with WebSocket authentication
* Locked-down evidence uploads to close potential loopholes
    * Evidence form now only allows specific filetypes: md, txt, log, jpg, jpeg, png
    * Requesting an evidence file requires an active user session
