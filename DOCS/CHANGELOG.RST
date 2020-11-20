Changelog
=========

20 November 2020
----------------
* Tagged release v2.0
    * More details: https://posts.specterops.io/ghostwriter-v2-0-release-638cef16deb7
* Upgraded to Django 3 and updated all dependencies
* Initial commit of CommandCenter application and related configuration options
    * VirusTotal Configuration
    * Global Report Configuration
    * Slack Configuration
    * Company information
    * Namecheap Configuration
* Initial support for adding users to groups for Role-Based Access Controls
* Automated Acitivty Logging (Oplog application) moved out of beta
* Implemented initial "overwatch" notifications
    * Domain check-out: alert if domain will expire soon and is not set to auto-renew
    * Domain check-out: alert if domain is marked as burned
    * Domain check-out: alert if domain has been previously used with selected client
* Updated user interface elements
    * New tabbed dashboards for clients, projects, and domains
    * New inline forms for creating and managing clients and projects and related items
    * New sidebar menu to improve legibility
    * Migrated buttons and background tasks to WebSockets and AJAX for a more seamless experience
* Initial release of refactored reporting engine
    * New drag-and-drop report management interface
    * Added many more options to the WYSIWYG editor's formatting menus
    * Initial support for rich text objects for Word documents
    * Added new `filter_severity` filter for Word templates
    * Closes #89
* Initial support for report template and management
    * Upload report tempalte files for Word and PowerPoint
    * New template linter to check and verify templates
    * Closes #28
    * Closes #90
* Security updates and fixes
    * Resolved potential stored cross-site scripting in operational logs
    * Resolved unvalidated evidence file uploads and new note creation
        * Associated user account is now set server-side
    * Resolved issues with WebSocket authentication
    * Locked-down evidence uploads to close potential loopholes
        * Evidence form now only allows specific filetypes: md, txt, log, jpg, jpeg, png
        * Requesting an evidence file requires an active user session
* Removed web scraping from domain health checks
    * Checks now use VirusTotal and link to the results
    * Closes #50
    * Closes #84
* Numerous bug fixes and enhancements to address reported issues
    * Closes #54
    * Closes #55
    * Closes #69
    * Closes #92
    * Closes #93
    * Closes #98

25 August 2020
--------------
* Cleaned and refactored each application to improve UI/UX and performance
    * See the code style guide in the wiki
* Added admin documentation for template filters and tags, views, and models
    * Added `docutils==0.16` to requirements
    * Added `django.contrib.admindocs` to base.py
    * Visit the Django administration panel and click "Documentation" in the upper-right corner
* Removed `django-tinymce` from the project
    * Determined this library was the root cause of several inconsistencies and issues
    * Ghostwriter did not use the library's major features, so removing it entirely simplified development
    * Model fields that were `HTMLField` are now `TextField` once again
    * Library remains listed in the requirements for backwards compatibility with migrations that import `django-tinymce.HTMLField`
* Converted many views to AJAX requests
* Introduced `django-channels` and support for WebSockets
* Added aupport for automatic project activity logging with new application and WebSockets
    * See the wiki for more information
* Fixed several issues related to report generation
    * Modified Open XML for image borders in Word reports to address cases where a border edge could go missing
    * Created an allowlist for HTML tags to avoid parsing errors when encountering unsupported HTML elements (e.g., `<br />`)
* Added `django-bleach` and `Bleach` to the project to sanitize WYSIWYG HTML in rare cases it must be rendered (e.g., previewing a finding)

15 June 2020
------------
* FIXED: Evidence files deleted during updates
    * This happened because of logic intended to clean-up evidence files when a user replaced an evidence file with a new upload
    * Function broke when the evidence upload location changed post-Dockerization
* FIXED: Finding References lists were not left-aligned in Word reports
    * All lists will now default to left-aligned vs. justified
    * This addresses list items with longer words/hostnames spreading out across the page in Word
* FIXED: Updating evidence required changing the `friendly_name` field
    * This check triggered on updates and checked if the name was unique for that finding
    * Check would fail because current name would match itself
* FIXED: Images were not centered
    * Images were set to 6.5" by default, which "centered" them
    * All images are now centered in case users change the size
* FIXED: Transparent areas in images become solid black
    * Alpha layers in PNG files converted to solid black during image processing
    * That image processing has been completely removed
* FIXED: Images needed proper borders
    * Ghostwriter now inserts the necessary Open XML elements to add a 1pt #2d2b6b border to all images
    * The fake borders added to images via PIL and image processing are gone
    * Border color can be changed by editing the class variables `border_color` and `border_color_hex` in reportwriter.py
* FIXED: Reports skipped evidence with periods in the name
    * Evidence processing individually removed `{`, `}`, and `.` from identified keywords
    * Now `{{.` and `}}` are removed to avoid collateral damage
* FIXED: Missing evidence files caused a 500 error
    * This should never happen because of the above change to evidence updates
    * As a precaution, Ghostwriter now checks if the file path is valid and raises a `FileNotFoundError` instead of skipping the file or failing
    * Determined this was preferable to the image just not being the report or inserting a "missing file" message
* FIXED: Updating a report title caused a 500 error
    * The UpdateView was incompatible with changes made to the report form to support creating a report outside of a project
* FIXED: Lists with indented items did not translate to report output
    * Ghostwriter now fully supports indenting list items
    * Number/bullet styles apply only to the Word report output and are managed by editing the `Bullet List` an `Number List` styles in template.docx
    * In HTML, indented list items are actually nested `<ol />` or `<ul />` tags inside of `<li />` tags so this required big changes to the HTML parser
* FIXED: Indented lists caused a 500 error
    * This issue was related to the above issue with indented list items
    * The nature of HTML nested lists triggered the code for processing hyperlinks when no hyperlinks were present
* FIXED: Changing a finding's severity in a report could cause the finding's weight to overlap
    * This was a cosmetic issue – changing a Critical with a position of 1 to be High could lead to two High findings with a position of 1
    * The positions would clash until a user clicked the arrows to move one of the findings up/down
    * Addressed this by adding a position check (and adjustment) whenever a user saves an edited finding
    * Users can manually set a position while editing, so the position of the updated finding is maintained during the adjustments
* FIXED: Date ranges did not sort correctly in tables
    * The base_generic.html template now loads the necessary jQuery UI parser to handle date ranges
    * Applied a consistent date format across all tables
* FIXED: Notes and descriptions do not display bond/italic/underline formatting
    * The WYSIWYG editor uses `span` tags and classes to assign bold, italic, and underline styles
    * The WYSIWYG editor's CSS displays these styles, but Ghostwriter's CSS did not have these classes
    * Added bold, italic, and underline classes to the CSS to support these TinyMCE classes outside of the editor
* FIXED: Text in the database that pre-dated the WYSIWYG editor was displayed differently in the UI
    * When the WYSIWYG text was rendered, Django preserved the `p` tags which applied a different set of styles than the styling for the `td` tags
    * The `td` style now takes priority over other styles
* FIXED: Copying a report finding to the library might overwrite an existing finding
    * Copying a finding now pre-fills a finding creation form for easier editing/reviewing prior to submitting the new finding to the library
    * Submitted findings will not overwrite an existing finding of the same name
* FIXED: Exporting data from the admin console caused a 500 error
    * The base.txt requirements file now calls for `django-import-export==2.2.0`
    * As of 9 Feb 2020, the `django-import-export` library started requiring additional libraries for supporting tablib
    * The changes in base_formats.py removed a try/except used for importing `xlrd` and added an `import xlrd` elsewhere in the code, making this a mandatory library along with other libraries used in this update
    * The app's attempts to import these non-existent libraries caused the 500 error
* FIXED: DNS record update fails for records larger than 500 characters (#72)
    * Applied changes discussed in Issue #72
* FIXED: Bulk import for findings no longer working after `auto_renew` field added (#73)
    * Applied suggested changes from @lez0sec in report #73
* ENHANCEMENT: The Namecheap sync task now checks if a domain in the Ghostwriter library no longer exists under the Namecheap account
    * This indicates the domain expired and dropped off the account since the last task run
    * The task marks missing domains as expired
    * Task now returns JSON describing changes to the domain library
* ENHANCEMENT: The release domain task now accepts a `reset_dns` boolean
    * If set to True, the task will release the domain in the library and then use the Namecheap API to clear all DNS records
    * This feature only supports Namecheap as is, but can be edited to use other registrar API
    * Task now returns JSON describing changes to the domains
* ENHANCEMENT: Cloud infrastructure monitoring is now more robust
    * Updated the task in various ways to improve the output
    * Persistent cloud assets tagged with `gw_ignore` will now be ignored
    * If Slack alerts are enabled, task now uses two new functions that build nicely formatted Slack messages using blocks
    * Task returns JSON describing the cloud assets discovered and any related Ghostwriter projects
* ENHANCEMENT: Expanded use of `logging` library to provide feedback to the console for background tasks and other DEBUG, INFO, WARNING, and ERROR information
* ENHANCEMENT: Added a Cloud Infrastructure section to the Domain Update Controls page to manually kick-off cloud asset reviews
* TWEAK: Evidence files are now clickable and open the evidence details view from the report details page
* TWEAK: Choosing to edit a report now opens the report details instead of the list of all reports
