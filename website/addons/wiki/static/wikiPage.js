'use strict';
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('osfHelpers');

var mathrender = require('mathrender');
var md = require('markdown').full;
var mdQuick = require('markdown').quick;
var diffTool = require('wikiDiff');

var THROTTLE = 500;

//<div id="preview" data-bind="mathjaxify: {throttle: 500}>
ko.bindingHandlers.mathjaxify = {
    init: function(element, valueAccessor, allBindingsAccessor, data, context) {
        var opts = valueAccessor();
        var vm = context.$data;

        if(vm.allowMathjaxification() && vm.viewVM.allowFullRender()) {
            mathrender.mathjaxify(element.id);
        }
    }
};


function ViewWidget(visible, version, viewText, rendered, contentURL, allowMathjaxification, editor) {
    var self = this;
    self.version = version;
    self.viewText = viewText; // comes from EditWidget.viewText
    self.rendered = rendered;
    self.visible = visible;
    self.allowMathjaxification = allowMathjaxification;
    self.editor = editor;
    self.allowFullRender = ko.observable(false);
    self.renderTimeout = null;

    self.renderMarkdown = function(rawContent){
        if(self.allowFullRender()) {
            return(md.render(rawContent));
        } else {
            return(mdQuick.render(rawContent));
        }
    };

    if (typeof self.editor !== 'undefined') {
        self.editor.on('change', function () {
            // Quick render
            self.allowFullRender(false);
            // Full render
            clearTimeout(self.renderTimeout);

            self.renderTimeout = setTimeout(function () {
                self.allowFullRender(true);
            }, THROTTLE);
        });
    }

    self.displayText =  ko.computed(function() {
        var requestURL;
        if (typeof self.version() !== 'undefined') {
            if (self.version() === 'preview') {
                self.rendered(self.renderMarkdown(self.viewText()));
                return self.viewText();
            } else {
                if (self.version() === 'current') {
                    requestURL = contentURL;
                } else {
                    requestURL= contentURL + self.version();
                }
                var request = $.ajax({
                    url: requestURL
                });

                request.done(function (resp) {
                    var rawContent = resp.wiki_content || '*No wiki content*';
                    if (resp.wiki_rendered) {
                        // Use pre-rendered python, if provided. Don't mathjaxify
                        self.allowMathjaxification(false);
                        if(self.visible()) {
                            self.rendered(resp.wiki_rendered);
                        }
                    } else {
                        // Render raw markdown
                        if(self.visible()) {
                            self.allowMathjaxification(true);
                            self.rendered(self.renderMarkdown(rawContent));
                        }
                    }
                    return(rawContent);
                });
            }
        } else {
            return ('');
        }
    });
}

    // currentText comes from ViewWidget.displayText
function CompareWidget(visible, compareVersion, currentText, rendered, contentURL) {
    var self = this;

    self.compareVersion = compareVersion;
    self.currentText = currentText;
    self.rendered = rendered;
    self.visible = visible;
    self.compareText = ko.computed(function() {
        var requestURL;
        if (self.compareVersion() === 'current') {
            requestURL = contentURL;
        } else {
            requestURL= contentURL + self.compareVersion();
        }
        var request = $.ajax({
            url: requestURL
        });
        request.done(function (resp) {
            return(resp.wiki_content);
        });

    });

    self.compareOutput = ko.computed(function() {
        var current = '';
        var compare = '';


        current = self.currentText();
        compare = self.compareText();

        var output = diffTool.diff(current, compare);
        self.rendered(output);
    });

}


var defaultOptions = {
    editVisible: false,
    viewVisible: true,
    compareVisible: false,
    canEdit: true,
    viewVersion: 'current',
    compareVersion: 'current',
    contentURL: '',
    draftURL: '',
    metadata: {}
};

function ViewModel(options){
    var self = this;

    // enabled?
    self.editVis = ko.observable(options.editVisible);
    self.viewVis = ko.observable(options.viewVisible);
    self.compareVis = ko.observable(options.compareVisible);

    self.compareVersion = ko.observable(options.compareVersion);
    self.viewVersion = ko.observable(options.viewVersion);
    self.draftURL = options.draftURL;
    self.contentURL = options.contentURL;
    self.editorMetadata = options.metadata;
    self.canEdit = options.canEdit;

    self.viewText = ko.observable('');
    self.renderedView = ko.observable('');
    self.renderedCompare = ko.observable('');
    self.allowMathjaxification = ko.observable(false);




    if(self.canEdit) {
        self.editor = ace.edit('editor');

        var ShareJSDoc = require('addons/wiki/static/ShareJSDoc.js');
        self.editVM = new ShareJSDoc(self.draftURL, self.editorMetadata, self.viewText, self.editor);
    }
    self.viewVM = new ViewWidget(self.viewVis, self.viewVersion, self.viewText, self.renderedView, self.contentURL, self.allowMathjaxification, self.editor);
    self.compareVM = new CompareWidget(self.compareVis, self.compareVersion, self.viewVM.displayText, self.renderedCompare, self.contentURL);
}


var WikiPage = function(selector, options) {
    var self = this;
    self.options = $.extend({}, defaultOptions, options);

    this.viewModel = new ViewModel(self.options);
    $osf.applyBindings(self.viewModel, selector);
};

module.exports = WikiPage;

//self.ButtonController = {
//        view.onClick = function () {
//        // logic...
//        $(this).trigger('editEnabled')
//    };


//$('body').on('editEnabled', function () {
//    self.version('preview');
//});
