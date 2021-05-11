// TinyMCE OpenURL dialog config only accepts height/width in pixels
// Get browser windows width and height and calculate pixels from a percentage to avoid overflow
var dialog_percentage = .7
var window_width = window.innerWidth;
var window_height = window.innerHeight;
var dialog_width = window_width * dialog_percentage;
var dialog_height = window_height * dialog_percentage;
// Monitor for window resizing and adjust dialog as needed
window.addEventListener("resize", adjust_dialog);

function adjust_dialog() {
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
    };
}

// Default config for all TinyMCE editors
var default_config = {
    entity_encoding: 'raw',
    branding: false,
    width: '100%',
    theme: 'silver',
    skin: 'Ghostwriter',
    selector: 'textarea:not(.empty-form textarea, .empty-form)',
    content_css: '/static/css/wysiwyg_styles.css',
    editor_deselector: 'empty-form',
    menubar: 'file edit insert view format tools',
    visualchars_default_state: false,
    menu: {
        file: { title: 'File', items: 'newdocument restoredraft' },
        edit: { title: 'Edit', items: 'undo redo | cut copy paste | selectall | searchreplace' },
        view: { title: 'View', items: 'code | visualchars visualblocks | preview' },
        insert: { title: 'Insert', items: 'evidenceUpload codesample link' },
        format: { title: 'Format', items: 'bold italic underline strikethrough superscript subscript codeformat | formats fontformats fontsizes align | forecolor | removeformat' },
        tools: { title: 'Tools', items: 'code wordcount' },
      },
    toolbar_mode: 'floating',
    plugins: 'visualchars visualblocks save preview lists image hr autosave advlist code wordcount codesample searchreplace paste link',
    toolbar: 'subscript superscript bold italic underline link | bullist numlist | codesample codeInline | evidenceUpload | removeformat save',
    contextmenu: 'bold italic link removeformat',
    paste_as_text: true,
    paste_data_images: false,
    browser_spellcheck: true,
    content_style: '.left { text-align: left; }' +
        'img.left { float: left; }' +
        'table.left { float: left; }' +
        '.right { text-align: right; }' +
        'img.right { float: right; }' +
        'table.right { float: right; }' +
        '.center { text-align: center; }' +
        'img.center { display: block; margin: 0 auto; }' +
        'table.center { display: block; margin: 0 auto; }' +
        '.full { text-align: justify; }' +
        'img.full { display: block; margin: 0 auto; }' +
        'table.full { display: block; margin: 0 auto; }' +
        '.bold { font-weight: bold; }' +
        '.italic { font-style: italic; }' +
        '.underline { text-decoration: underline; }' +
        '.tablerow1 { background-color: #D3D3D3; }',
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
            inline : 'span',
            classes : 'highlight',
            styles : {
                backgroundColor : 'yellow'
            }
        },
    },
    style_formats: [
        { title: 'Headings', items: [
          { title: 'Heading 1', format: 'h1' },
          { title: 'Heading 2', format: 'h2' },
          { title: 'Heading 3', format: 'h3' },
          { title: 'Heading 4', format: 'h4' },
          { title: 'Heading 5', format: 'h5' },
          { title: 'Heading 6', format: 'h6' }
        ]},
        { title: 'Inline', items: [
          { title: 'Bold', format: 'bold' },
          { title: 'Italic', format: 'italic' },
          { title: 'Underline', format: 'underline' },
          { title: 'Strikethrough', format: 'strikethrough' },
          { title: 'Superscript', format: 'superscript' },
          { title: 'Subscript', format: 'subscript' },
          { title: 'Code', format: 'code' },
          { title: 'Highlight', format: 'highlight' }
        ]},
        { title: 'Align', items: [
          { title: 'Left', format: 'alignleft' },
          { title: 'Center', format: 'aligncenter' },
          { title: 'Right', format: 'alignright' },
          { title: 'Justify', format: 'alignjustify' }
        ]}
      ]
}

/*
Setup a basic config for most Ghostwriter textarea inputs that is combined with the above default config

Combined using object spread so this config will overwrite shared values in the default config
*/

basic_config = {
    setup: function (editor) {
        editor.ui.registry.addButton('codeInline', {
            icon: 'sourcecode',
            text: '',
            tooltip: 'Format selected text as inline code',
            onAction: function (_) {
                tinymce.activeEditor.formatter.toggle('code')
            },
        });
    },
}

basic_config = {
    ...default_config,
    ...basic_config
};

/*
Setup a config with additional evidence upload options for finding textareas witin a report

Combine it with the default config above
*/

finding_config = {
    selector: "textarea.enable-evidence-upload",
    setup: function (editor) {
        editor.ui.registry.addButton('codeInline', {
            icon: 'sourcecode',
            text: 'Inline Code',
            tooltip: 'Format selected text as inline code',
            onAction: function (_) {
                tinymce.activeEditor.formatter.toggle('code')
            },
        });

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
                    editor.insertContent(`\n<p>\{\{.${value.friendly_name}\}\}</p>`);
                    // A brief block to prevent users from jamming the close button immediately
                    _dialog.block('Uploading...');
                    setTimeout(() => {
                        _dialog.unblock();
                    }, 1000);
                    // Push the new evidence into the AutoComplete dict
                    evidenceFiles.push({
                        text: evidence_placeholder,
                        value: evidence_placeholder
                    })
                }
            }
        });

        editor.ui.registry.addAutocompleter('evidence', {
            ch: '@',
            minChars: 1,
            columns: 1,
            fetch: function (pattern) {
                var matchedChars = evidenceFiles.filter(function (quote) {
                    return quote.text.indexOf(pattern) !== -1;
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
    },
}

report_config = {
    ...default_config,
    ...finding_config
};

/*
Initiate TinyMCE targeting ``textarea.enable-evidence-upload`` inputs

This must be initiated first because the default config will initiate all ``textarea`` inputs
*/

tinymce.init(report_config)

/*
Initiate TinyMCE targeting all ``textarea`` inputs

The init is wrapped in a function so it can be called to reinitialize TinyMCE as needed

Editors must be reinitiated when an empty formset form is copied and added to a form
*/

function tinyInit() {
    tinymce.init(basic_config);
};
tinyInit();
