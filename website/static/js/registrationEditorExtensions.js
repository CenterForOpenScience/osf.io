var $ = require('jquery');
var URI = require('URIjs');
var moment = require('moment');
var ko = require('knockout');

var FilesWidget = require('js/FilesWidget');
var Fangorn = require('js/fangorn');
var $osf = require('js/osfHelpers');

var node = window.contextVars.node;

ko.bindingHandlers.osfUploader = {
    init: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        var fw = new FilesWidget(
            element.id,
            node.urls.api + 'files/grid/',
            {
                onSelectRow: function(item) {
                    debugger;
                },
                dropzone : {                                           // All dropzone options.
                    url: function(files) {return files[0].url;},
                    clickable : "#" + element.id,
                    addRemoveLinks: false,
                    previewTemplate: '<div></div>',
                    parallelUploads: 1,
                    acceptDirectories: false,
                    fallback: function(){}
                }
            }
        );
        fw.init();
    },
    update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        
    }
};

var Uploader = function(data) {
    
    var self = this;

    $.extend(self, data);
};
