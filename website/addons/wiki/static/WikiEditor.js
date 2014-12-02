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

    function ViewModel(url) {
        var self = this;

        self.initText = '';
        self.wikiText = ko.observable();

        self.changed = ko.computed(function() {
            return self.initText !== self.wikiText();
        });

        //Fetch initial wiki text
        $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json',
            cache: false,
            success: function(response) {
                self.initText = response.wiki_content;
                self.wikiText(response.wiki_content);
            },
            error: function(xhr, textStatus, error) {
                $.osf.growl('Error','The wiki content could not be loaded.');
                Raven.captureMessage('Could not GET get wiki contents.', {
                    url: url,
                    textStatus: textStatus,
                    error: error
                });
            }
        });

        $(window).on('beforeunload', function() {
            if (self.changed()) {
                return 'There are unsaved changes to your wiki.';
            }
        });
    }

    function WikiEditor(selector, url) {
        var viewModel = new ViewModel(url);
        $.osf.applyBindings(viewModel, selector);
        var converter1 = Markdown.getSanitizingConverter();
        var editor1 = new Markdown.Editor(converter1);
        editor1.run();
    }

    return WikiEditor;
}));
