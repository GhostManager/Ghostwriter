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

    GW_TINYMCE_DEFAULT_CONFIG = {
        entity_encoding: 'raw',
        branding: false,
        width: '100%',
        theme: 'silver',
        skin: 'Ghostwriter',
        selector: 'textarea:not(.empty-form textarea, .empty-form, .no-auto-tinymce)',
        content_css: '/static/css/wysiwyg_styles.css',
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

    $(() => tinymce.init(GW_TINYMCE_FINDING_CONFIG));

    /*
    Initiate TinyMCE targeting all ``textarea`` inputs

    The init is wrapped in a function, so it can be called to reinitialize TinyMCE as needed

    Editors must be reinitialized when an empty formset form is copied and added to a form
    */

    function tinyInit() {
        tinymce.init(GW_TINYMCE_BASIC_CONFIG);
    }
    $(tinyInit);

})($ || django.jQuery);
