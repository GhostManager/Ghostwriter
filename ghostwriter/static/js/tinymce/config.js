(function ($) {
    // TinyMCE OpenURL dialog config only accepts height/width in pixels
    // Get browser windows width and height and calculate pixels from a percentage to avoid overflow
    var dialog_percentage = .7
    var window_width = window.innerWidth;
    var window_height = window.innerHeight;
    var dialog_width = window_width * dialog_percentage;
    var dialog_height = window_height * dialog_percentage;
    // Monitor for window resizing and adjust dialog as needed
    window.addEventListener("resize", function () {
        var window_width = window.innerWidth;
        var window_height = window.innerHeight;
        var dialog_width = window_width * dialog_percentage;
        var dialog_height = window_height * dialog_percentage;
        var dialog_box = document.getElementsByClassName('tox-dialog')[0];
        if (typeof dialog_box !== 'undefined') {
            tinyMCE.DOM.setStyle(tinyMCE.DOM.get(dialog_box), 'height', dialog_height + 'px');
            tinyMCE.DOM.setStyle(tinyMCE.DOM.get(dialog_box), 'width', dialog_width + 'px');
            tinyMCE.DOM.setStyle(tinyMCE.DOM.get(dialog_box), 'max-height', dialog_height + 'px');
            tinyMCE.DOM.setStyle(tinyMCE.DOM.get(dialog_box), 'max-width', dialog_width + 'px');
        }

    });

    function gwGetTinyMceTheme() {
        const documentTheme = document.documentElement.getAttribute('data-theme');
        if (documentTheme === 'dark' || documentTheme === 'light') {
            return documentTheme;
        }

        try {
            const storedTheme = localStorage.getItem('ghostwriter-theme');
            if (storedTheme === 'dark' || storedTheme === 'light') {
                return storedTheme;
            }

            if (storedTheme === 'auto' && window.matchMedia) {
                return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            }
        } catch (error) {
            // Fall back to the default light theme if storage is unavailable.
        }

        return 'light';
    }

    function gwGetTinyMceSkin() {
        return gwGetTinyMceTheme() === 'dark' ? 'GhostwriterDark' : 'Ghostwriter';
    }

    function gwGetTinyMceContentCss() {
        const tinyContentCss = gwGetTinyMceTheme() === 'dark'
            ? '/static/js/tinymce/skins/content/GhostwriterDark/content.min.css'
            : '/static/js/tinymce/skins/content/default/content.min.css';

        return [tinyContentCss, '/static/css/wysiwyg_styles.css'];
    }

    function gwGetTinyMceThemeConfig(config) {
        return {
            ...config,
            skin: gwGetTinyMceSkin(),
            content_css: gwGetTinyMceContentCss(),
        };
    }

    window.gwGetTinyMceThemeConfig = gwGetTinyMceThemeConfig;

    function gwApplyTinyMceTheme(editor) {
        if (!editor || editor.removed) {
            return;
        }

        const theme = gwGetTinyMceTheme();
        const container = editor.getContainer();
        if (container) {
            container.classList.toggle('gw-tinymce-dark', theme === 'dark');
        }

        const body = editor.getBody();
        if (body) {
            body.classList.toggle('gw-tinymce-dark', theme === 'dark');
            body.setAttribute('data-gw-theme', theme);
        }
    }

    function gwRefreshTinyMceLayout(editor) {
        if (!editor || editor.removed || !editor.initialized || !editor.getBody()) {
            return;
        }

        if (editor._gwTinyMceRefreshRafId) {
            window.cancelAnimationFrame(editor._gwTinyMceRefreshRafId);
            editor._gwTinyMceRefreshRafId = null;
        }

        gwApplyTinyMceTheme(editor);

        if (typeof editor.execCommand === 'function') {
            editor._gwTinyMceRefreshRafId = window.requestAnimationFrame(function () {
                editor._gwTinyMceRefreshRafId = null;
                if (!editor.removed && editor.initialized && editor.getBody()) {
                    editor.execCommand('mceAutoResize');
                }
            });
        }
    }

    function gwClearTinyMceRefreshTimers(editor) {
        if (!editor) {
            return;
        }

        if (editor._gwTinyMceRefreshScheduleRafId) {
            window.cancelAnimationFrame(editor._gwTinyMceRefreshScheduleRafId);
            editor._gwTinyMceRefreshScheduleRafId = null;
        }

        if (editor._gwTinyMceRefreshTimeoutIds) {
            editor._gwTinyMceRefreshTimeoutIds.forEach(function (timeoutId) {
                window.clearTimeout(timeoutId);
            });
        }

        editor._gwTinyMceRefreshTimeoutIds = [];
    }

    function gwScheduleTinyMceLayoutRefresh(editor) {
        if (!editor || editor.removed) {
            return;
        }

        gwClearTinyMceRefreshTimers(editor);

        editor._gwTinyMceRefreshScheduleRafId = window.requestAnimationFrame(function () {
            editor._gwTinyMceRefreshScheduleRafId = null;
            gwRefreshTinyMceLayout(editor);
        });

        editor._gwTinyMceRefreshTimeoutIds = [100, 300].map(function (delay) {
            return window.setTimeout(function () {
                gwRefreshTinyMceLayout(editor);
            }, delay);
        });
    }

    function gwIsTinyMceEditorVisible(editor) {
        if (!editor || editor.removed) {
            return false;
        }

        const container = editor.getContainer();
        if (!container) {
            return false;
        }

        return !!(container.offsetWidth || container.offsetHeight || container.getClientRects().length);
    }

    function gwEditorNeedsThemeReinit(editor) {
        if (!editor || editor.removed) {
            return false;
        }

        const nextThemeConfig = gwGetTinyMceThemeConfig({});
        const currentContentCss = Array.isArray(editor.settings.content_css)
            ? editor.settings.content_css.join('|')
            : editor.settings.content_css;
        const nextContentCss = Array.isArray(nextThemeConfig.content_css)
            ? nextThemeConfig.content_css.join('|')
            : nextThemeConfig.content_css;

        return editor.settings.skin !== nextThemeConfig.skin || currentContentCss !== nextContentCss;
    }

    function gwReinitializeTinyMceEditor(editor) {
        if (!editor || editor.removed || !editor.targetElm) {
            return;
        }

        const wasFocused = typeof editor.hasFocus === 'function' && editor.hasFocus();
        let bookmark = null;
        if (wasFocused && editor.selection) {
            try {
                bookmark = editor.selection.getBookmark(2, true);
            } catch (error) {
                bookmark = null;
            }
        }

        editor.save();

        const settings = {
            ...gwGetTinyMceThemeConfig(editor.settings),
            target: editor.targetElm,
        };
        delete settings.selector;

        const existingInitInstanceCallback = settings.init_instance_callback;
        settings.init_instance_callback = function (newEditor) {
            if (typeof existingInitInstanceCallback === 'function') {
                existingInitInstanceCallback(newEditor);
            }

            if (wasFocused) {
                newEditor.focus();
                if (bookmark && newEditor.selection) {
                    try {
                        newEditor.selection.moveToBookmark(bookmark);
                    } catch (error) {
                        // Ignore selection restore failures and leave the editor focused.
                    }
                }
            }
        };

        editor.remove();
        tinymce.init(settings);
    }

    let gwObservedTinyMceTheme = gwGetTinyMceTheme();
    let gwTinyMceThemeObserverStarted = false;

    function gwObserveTinyMceTheme() {
        if (gwTinyMceThemeObserverStarted) {
            return;
        }

        gwTinyMceThemeObserverStarted = true;

        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type !== 'attributes' || mutation.attributeName !== 'data-theme') {
                    return;
                }

                const nextTheme = gwGetTinyMceTheme();
                if (nextTheme === gwObservedTinyMceTheme) {
                    return;
                }

                gwObservedTinyMceTheme = nextTheme;
                tinymce.editors.slice().forEach(function (editor) {
                    if (gwEditorNeedsThemeReinit(editor) && (gwIsTinyMceEditorVisible(editor) || editor.hasFocus())) {
                        gwReinitializeTinyMceEditor(editor);
                    }
                });
            });
        });

        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-theme'],
        });
    }

    GW_TINYMCE_DEFAULT_CONFIG = {
        entity_encoding: 'raw',
        branding: false,
        width: '100%',
        theme: 'silver',
        selector: 'textarea:not(.empty-form textarea, .empty-form, .no-auto-tinymce)',
        menubar: 'file edit insert view format table tools',
        visualchars_default_state: false,
        menu: {
            file: {title: 'File', items: 'newdocument restoredraft'},
            edit: {title: 'Edit', items: 'undo redo | cut copy paste | selectall | searchreplace'},
            view: {title: 'View', items: 'code | visualchars visualblocks | preview'},
            insert: {title: 'Insert', items: 'table evidenceUpload codesample link pagebreak'},
            format: {
                title: 'Format',
                items: 'bold italic underline strikethrough superscript subscript codeformat richcode case | formats fontformats fontsizes align | forecolor | removeformat'
            },
            table: {title: 'Table', items: 'inserttable | cell row column | tableprops deletetable'},
            tools: {title: 'Tools', items: 'code wordcount'},
        },
        max_height: window_height - 250,
        min_height: 160,
        autoresize_bottom_margin: 10,
        toolbar_mode: 'floating',
        plugins: 'searchreplace autoresize visualchars visualblocks save preview lists image hr autosave advlist code wordcount codesample searchreplace paste link case table pagebreak',
        toolbar: 'subscript superscript bold italic underline link blockquote case highlight | bullist numlist | richcode codeInline | table tablerowheader | evidenceUpload | searchreplace removeformat save | editorsHints',
        contextmenu: 'table formats bold italic underline link removeformat',
        // paste_as_text: true,
        paste_data_images: false,
        browser_spellcheck: true,
        resize: true,
        content_style: `
            body.mce-content-body[data-mce-placeholder]:not(.mce-visualblocks)::before { color: #999; opacity: 1; }
            .left { text-align: left; }
            img.left { float: left; }
            table.left { float: left; }
            .right { text-align: right; }
            img.right { float: right; }
            table.right { float: right; }
            .center { text-align: center; }
            img.center { display: block; margin: 0 auto; }
            table.center { display: block; margin: 0 auto; }
            .full { text-align: justify; }
            img.full { display: block; margin: 0 auto; }
            table.full { display: block; margin: 0 auto; }
            .bold { font-weight: bold; }
            .italic { font-style: italic; }
            .underline { text-decoration: underline; }
            .tablerow1 { background-color: #D3D3D3; }
            blockquote { border-left: 5px solid #ccc; padding: 0.5em; margin: 0.5em; }
            pre.rich-code { background: #f5f2f0; padding: 1em; margin: 0.5em 0; overflow: auto; }
        `,
        formats: {
            alignleft: {
                selector: 'p,h1,h2,h3,h4,h5,h6,td,th,div,ul,ol,li,table,img',
                classes: 'left'
            },
            aligncenter: {
                selector: 'p,h1,h2,h3,h4,h5,h6,td,th,div,ul,ol,li,table,img',
                classes: 'center'
            },
            alignright: {
                selector: 'p,h1,h2,h3,h4,h5,h6,td,th,div,ul,ol,li,table,img',
                classes: 'right'
            },
            alignjustify: {
                selector: 'p,h1,h2,h3,h4,h5,h6,td,th,div,ul,ol,li,table,img',
                classes: 'justify'
            },
            bold: {
                inline: 'span',
                classes: 'bold'
            },
            italic: {
                inline: 'span',
                classes: 'italic'
            },
            underline: {
                inline: 'span',
                classes: 'underline',
                exact: true
            },
            strikethrough: {
                inline: 'del'
            },
            subscript: {
                inline: 'sub'
            },
            superscript: {
                inline: 'sup'
            },
            highlight: {
                inline: 'span',
                classes: 'highlight',
                styles: {
                    backgroundColor: 'yellow'
                }
            },
            blockquote: {
                block: 'blockquote',
                classes: 'blockquote'
            },
            richcode: {
                block: 'pre',
                classes: 'rich-code',
            },
        },
        style_formats: [
            {
                title: 'Headings', items: [
                    {title: 'Heading 1', format: 'h1'},
                    {title: 'Heading 2', format: 'h2'},
                    {title: 'Heading 3', format: 'h3'},
                    {title: 'Heading 4', format: 'h4'},
                    {title: 'Heading 5', format: 'h5'},
                    {title: 'Heading 6', format: 'h6'}
                ]
            },
            {
                title: 'Inline', items: [
                    {title: 'Bold', format: 'bold'},
                    {title: 'Italic', format: 'italic'},
                    {title: 'Underline', format: 'underline'},
                    {title: 'Strikethrough', format: 'strikethrough'},
                    {title: 'Superscript', format: 'superscript'},
                    {title: 'Subscript', format: 'subscript'},
                    {title: 'Code', format: 'code'},
                    {title: 'Highlight', format: 'highlight'},
                    {title: 'Blockquote', format: 'blockquote'}
                ]
            },
            {
                title: 'Align', items: [
                    {title: 'Left', format: 'alignleft'},
                    {title: 'Center', format: 'aligncenter'},
                    {title: 'Right', format: 'alignright'},
                    {title: 'Justify', format: 'alignjustify'}
                ]
            },
        ],
        font_formats: "Andale Mono=andale mono,times; Arial=arial,helvetica,sans-serif; Arial Black=arial black,avant garde; Book Antiqua=book antiqua,palatino; Calibri=calibri; Courier New=courier new,courier; Georgia=georgia,palatino; Helvetica=helvetica; Impact=impact,chicago; Symbol=symbol; Tahoma=tahoma,arial,helvetica,sans-serif; Terminal=terminal,monaco; Times New Roman=times new roman,times; Trebuchet MS=trebuchet ms,geneva; Verdana=verdana,geneva;",
        table_default_styles: {'border-collapse': 'collapse', 'width': '100%', 'border-style': 'solid', 'border-width': '1px'},
        table_default_attributes: {class: 'table table-sm table-striped table-bordered'},
        table_header_type: 'sectionCells',
        setup: function(editor) {
            editor.ui.registry.addButton('codeInline', {
                context: 'format',
                icon: 'sourcecode',
                tooltip: 'Format selected text as inline code',
                onAction: function (_) {
                    tinymce.activeEditor.formatter.toggle('code')
                },
            });

            editor.ui.registry.addButton('highlight', {
                context: 'format',
                icon: 'highlight-bg-color',
                tooltip: 'Highlight selected text',
                onAction: function (_) {
                    tinymce.activeEditor.formatter.toggle('highlight')
                },
            });

            editor.ui.registry.addButton('richcode', {
                context: 'format',
                icon: 'code-sample',
                tooltip: 'Code snippet with formatting support',
                onAction: function(_) {
                    tinymce.activeEditor.formatter.toggle('richcode');
                }
            });

            editor.ui.registry.addMenuItem('richcode', {
                context: 'format',
                icon: 'code-sample',
                text: 'Rich Code',
                tooltip: 'Code snippet with formatting support',
                onAction: function(_) {
                    tinymce.activeEditor.formatter.toggle('richcode');
                }
            });

            editor.on('init', function () {
                gwScheduleTinyMceLayoutRefresh(editor);
                gwObserveTinyMceTheme();
            });

            editor.on('SetContent ResizeEditor', function () {
                gwScheduleTinyMceLayoutRefresh(editor);
            });

            editor.on('remove', function () {
                gwClearTinyMceRefreshTimers(editor);
                if (editor._gwTinyMceRefreshRafId) {
                    window.cancelAnimationFrame(editor._gwTinyMceRefreshRafId);
                    editor._gwTinyMceRefreshRafId = null;
                }
            });
        },
        paste_preprocess: function(_, event) {
            if(tinymce.activeEditor.formatter.match("richcode")) {
                // When pasting into rich code, strip <p>, which will cause the text to be inserted after the rich code block,
                // which is not what we want.
                const parser = tinymce.html.DomParser({}, tinymce.activeEditor.schema);
                parser.addNodeFilter("p", nodes => {
                    tinymce.util.Tools.each(nodes, node => {
                        node.unwrap();
                    });
                });
                const fragment = parser.parse(event.content, { force_root_block: false, isRootContent: true });
                event.content = tinymce.html.Serializer({}, tinymce.activeEditor.schema).serialize(fragment);
            }
        },
    };

    // TinyMCE config for most fields
    GW_TINYMCE_BASIC_CONFIG = {
        ...GW_TINYMCE_DEFAULT_CONFIG,
    };

    // TinyMCE config for finding fields, with additional functionality for evidence uploads
    GW_TINYMCE_FINDING_CONFIG = {
        ...GW_TINYMCE_BASIC_CONFIG,
        selector: "textarea.enable-evidence-upload",
        setup: function (editor) {
            GW_TINYMCE_BASIC_CONFIG.setup.call(this, editor);

            // https://www.martyfriedel.com/blog/tinymce-5-url-dialog-component-and-window-messaging
            editor.ui.registry.addButton('evidenceUpload', {
                icon: 'upload',
                text: 'Upload Evidence',
                tooltip: 'Attach an evidence file to this finding to reference in the editor',
                onAction: function () {
                    _dialog = editor.windowManager.openUrl({
                        title: 'Upload Evidence',
                        url: window.parent.upload_url,
                        height: dialog_height,
                        width: dialog_width,
                        buttons: [{
                            type: 'custom',
                            name: 'action',
                            text: 'Upload & Insert Evidence',
                            primary: true,
                        },
                            {
                                type: 'cancel',
                                name: 'cancel',
                                text: 'Close'
                            }
                        ],
                        onAction: function (instance, trigger) {
                            instance.sendMessage({
                                mceAction: 'evidence_upload'
                            });
                        }
                    });
                },
            });

            editor.addCommand('upload_and_insert', function (ui, value) {
                if (value.friendly_name == '' || value.evidence_file == '' || value.caption == '') {
                    // editor.windowManager.alert('The form is incomplete. You need a file, friendly name, and a caption.');
                } else {
                    if (value.used_friendly_names.includes(value.friendly_name)) {
                        // Do nothing – this is client-side validation that the same friendly name
                        // is not being used for two uploads
                        // This is NOT the primary validation, so client-side isn't a concern
                        // This just prevents the JS code from proceeding in the event the form
                        // submission is kicked back for name reuse
                    } else {
                        var evidence_placeholder = `\{\{.${value.friendly_name}\}\}`;
                        var ref_placeholder = `\{\{.ref ${value.friendly_name}\}\}`;
                        editor.insertContent(`\n<p>\{\{.${value.friendly_name}\}\}</p>`);
                        // A brief block to prevent users from jamming the close button immediately
                        _dialog.block('Uploading...');
                        setTimeout(() => {
                            _dialog.unblock();
                        }, 1000);
                        // Push the new evidence into the AutoComplete dict
                        evidenceFiles.push(
                            {
                                text: evidence_placeholder,
                                value: evidence_placeholder
                            },
                            {
                                text: ref_placeholder,
                                value: ref_placeholder
                            }
                        )
                    }
                }
            });

            editor.ui.registry.addAutocompleter('evidence', {
                ch: '@',
                minChars: 1,
                columns: 1,
                maxResults: 20,
                fetch: function (pattern) {
                    var matchedChars = evidenceFiles.filter(function (quote) {
                        return quote.text.toLowerCase().includes(pattern.toLowerCase());

                    });
                    return new tinymce.util.Promise(function (resolve) {
                        var results = matchedChars.map(function (quote) {
                            return {
                                value: quote.value,
                                text: quote.text
                            }
                        });
                        resolve(results);
                    });
                },
                onAction: function (autocompleteApi, rng, value) {
                    editor.selection.setRng(rng);
                    editor.insertContent(value);
                    autocompleteApi.hide();
                }
            });

            editor.ui.registry.addButton('editorsHints', {
              icon: 'info',
              text: 'CTRL+Right Click to access browser context menu',
              disabled: true,
              onAction: function (_) {},
              onSetup: function (buttonApi) {}
            });
        },
    };

    /*
    Initiate TinyMCE targeting ``textarea.enable-evidence-upload`` inputs

    This must be initiated first because the default config will initiate all ``textarea`` inputs
    */

    $(() => tinymce.init(gwGetTinyMceThemeConfig(GW_TINYMCE_FINDING_CONFIG)));

    /*
    Initiate TinyMCE targeting all ``textarea`` inputs

    The init is wrapped in a function, so it can be called to reinitialize TinyMCE as needed

    Editors must be reinitialized when an empty formset form is copied and added to a form
    */

    function tinyInit() {
        tinymce.init(gwGetTinyMceThemeConfig(GW_TINYMCE_BASIC_CONFIG));
    }
    $(tinyInit);

    $(document).on('shown.bs.modal shown.bs.tab shown.bs.collapse', function () {
        tinymce.editors.forEach(function (editor) {
            if (gwEditorNeedsThemeReinit(editor) && gwIsTinyMceEditorVisible(editor)) {
                gwReinitializeTinyMceEditor(editor);
                return;
            }
            gwScheduleTinyMceLayoutRefresh(editor);
        });
    });

})($ || django.jQuery);

function tinymceLogInit() {
    let logConfig = { ...GW_TINYMCE_BASIC_CONFIG };
    logConfig.selector = '.modal-content textarea:not(.empty-form textarea, .empty-form, .no-auto-tinymce)';
    tinymce.init(gwGetTinyMceThemeConfig(logConfig));
}

function tinymceRemove() {
    tinymce.remove();
}
