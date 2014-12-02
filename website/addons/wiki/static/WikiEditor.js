/**
 * Initializes the pagedown editor and prompts the user if
 * leaving the page with unsaved changes.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.WikiEditor  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';

    var editor;

    ko.bindingHandlers.ace = {
        init: function(element, valueAccessor) {
            editor = ace.edit(element.id);
            var value = ko.unwrap(valueAccessor());

            // Initialize editor value if not yet initialized.
            if (editor.getReadOnly() === true) {
                editor.setValue(value);
                editor.setReadOnly(false);
            }
            // Initialize view model if editor was initialized
            else {
                valueAccessor()(editor.getValue());
            }

            // TODO: Load data from server if no data from server

            // Updates the view model based on changes to the editor
            editor.getSession().on('change', function () {
                valueAccessor()(editor.getValue());
            });
        },
        update: function (element, valueAccessor) {
            var content = editor.getValue();        // Content of ace editor
            var value = ko.unwrap(valueAccessor()); // Value from view model

            // Updates the editor based on changes to the view model
            if (value !== undefined && content !== value) {
                editor.setValue(value);
            }
        }
    };

    ko.bindingHandlers.tooltip = {
        init: function(element, valueAccessor) {
            var value = ko.unwrap(valueAccessor());
            var options = {
                title: value,
                placement: 'bottom'
            };

            $(element).tooltip(options);
        }
    };

    function ViewModel(url) {
        var self = this;

        self.initText = ko.observable();
        self.wikiText = ko.observable();
        self.activeUsers = ko.observableArray([]);

        self.displayCollaborators = ko.computed(function() {
           return self.activeUsers().length > 1;
        });

        // TODO: Bug with multiple windows messing up changed value
        self.changed = ko.computed(function() {
            /* Always assume a changed state so we can edit. Once
               there is a better way to push save information from one
               browser window to another, it should be used to disable buttons.
             */
            return true;
            // return self.initText() !== self.wikiText();
        });

        self.revertChanges = function() {
            self.fetchData()
        };

        // Fetch initial wiki text
        self.fetchData = function() {
            $.ajax({
                type: 'GET',
                url: url,
                dataType: 'json',
                success: function (response) {
                    self.initText(response.wiki_content);
                    self.wikiText(response.wiki_content);
                },
                error: function (xhr, textStatus, error) {
                    $.osf.growl('Error','The wiki content could not be loaded.');
                    Raven.captureMessage('Could not GET wiki contents.', {
                        url: url,
                        textStatus: textStatus,
                        error: error
                    });
                }
            });
        };

        // TODO: Uncomment once "changed" property is correct
//        $(window).on('beforeunload', function() {
//            if (self.changed()) {
//                return 'If you leave this page, your changes will be ' +
//                    'saved as a draft for collaborators, but not made public.';
//            }
//        });
    }

    function WikiEditor(selector, url) {
        this.viewModel = new ViewModel(url);
        $.osf.applyBindings(this.viewModel, selector);
        var converter1 = Markdown.getSanitizingConverter();
        var editor1 = new Markdown.Editor(converter1);
        editor1.run(editor);
    }

    return WikiEditor;
}));
