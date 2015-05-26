/**
* Components and binding handlers for the dashboard "onboarding" interface.
* Includes a custom component for OSF project typeahead search, as well
* the viewmodels for each of the individual onboarding widgets.
*/
'use strict';

// CSS
require('css/onboarding.css');
require('css/typeahead.css');

var Dropzone = require('dropzone');
var Handlebars = require('handlebars');
var Raven = require('raven-js');
var ko = require('knockout');
var $ = require('jquery');
require('typeahead.js');


require('js/projectCreator.js');
var waterbutler = require('js/waterbutler');
var $osf = require('js/osfHelpers');

function noop() {}
var MAX_RESULTS = 14;
var DEFAULT_FETCH_URL = '/api/v1/dashboard/get_nodes/';

var substringMatcher = function(strs) {
    return function findMatches(q, cb) {

        // an array that will be populated with substring matches
        var matches = [];

        // regex used to determine if a string contains the substring `q`

        var substrRegex = new RegExp(q, 'i');
        var count = 0;
        // iterate through the pool of strings and for any string that
        // contains the substring `q`, add it to the `matches` array
        $.each(strs, function(i, str) {
            if (substrRegex.test(str.name)) {
                count += 1;
                // the typeahead jQuery plugin expects suggestions to a
                // JavaScript object, refer to typeahead docs for more info
                matches.push({ value: str });

                //alex's hack to limit number of results
                if(count > MAX_RESULTS){
                    return false;
                }
                // above you can return name or a dict of name/node id,
            }
            // add an event to the input box -- listens for keystrokes and if there is a keystroke then it should clearrr
            //
        });

        cb(matches);
    };
};

function initTypeahead(element, nodes, viewModel, params){
    var $inputElem = $(element);
    var myProjects = nodes.map(serializeNode);
    $inputElem.typeahead({
        hint: false,
        highlight: true,
        minLength: 0
    },
    {
        // name: 'projectSearch' + nodeType + namespace,
        displayKey: function(data) {
            return data.value.name;
        },
        templates: {
            suggestion: Handlebars.compile('<p>{{value.name}}</p> ' +
                                            '<p><small class="ob-suggestion-date text-muted">' +
                                            'modified {{value.dateModified.local}}</small></p>')
        },
        source: substringMatcher(myProjects)
    });

    $inputElem.bind('typeahead:selected', function(obj, datum) {
        // Call the parent viewModel's onSelected
        var onSelected = params.onSelected || viewModel.onSelected;
        onSelected(datum.value);
    });
    var onFetched = ko.unwrap(params.onFetched);
    if (onFetched) {
        onFetched(myProjects);
    }
    return $inputElem;
}

// Defines the format of items in the typeahead data source
function serializeNode(node) {
    var dateModified = new $osf.FormattableDate(node.date_modified);
    return {
        name: node.title,
        id: node.id,
        dateModified: dateModified,
        urls: {
            web: node.url,
            api: node.api_url,
            register: node.url + 'register/',
            files: node.url + 'files/',
            children: node.api_url + 'get_children/?permissions=write'
        }
    };
}

/**
    * Binding handler for attaching an OSF typeahead search input.
    * Takes an optional parameter onSelected, which is called when a project
    * is selected.
    *
    * Params:
    *  data: An Array of data or a URL where to fetch nodes. Defaults to the dashboard node endpoint.
    *  onSelected: Callback for when a node is selected.
    *  onFetched: Callback for when nodes are fetched from server.
    *
    * Example:
    *
    *  <div data-bind="projectSearch: {url: '/api/v1/dashboard/get_nodes/',
    *                                     onSelected: onSelected}></div>
    */
ko.bindingHandlers.projectSearch = {
    update: function(element, valueAccessor, allBindings, viewModel) {
        var params = valueAccessor() || {};
        // Either an Array of nodes or a URL
        var nodesOrURL = ko.unwrap(params.data);
        if (params.clearOn && params.clearOn()) {
            $(element).typeahead('destroy');
            return;
        }
        if (Array.isArray(nodesOrURL)) {
            var nodes = params.data;
            // Compute relevant URLs for each search result
            initTypeahead(element, nodes, viewModel, params);
        } else if (typeof nodesOrURL === 'string') { // params.data is a URL
            var url = nodesOrURL;
            var request = $.getJSON(url, function (response) {
                // Compute relevant URLs for each search result
                initTypeahead(element, response.nodes, viewModel, params);
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Could not fetch dashboard nodes.', {
                    url: url, textStatus: textStatus, error: error
                });
            });
        }
    }
};

/**
    * ViewModel for the OSF project typeahead search widget.
    *
    * Template: osf-project-search element in components/dashboard_templates.mako
    *
    * Params:
    *  onSubmit: Function to call on submit. Receives the selected item.
    *  onSelected: Function to call when a typeahead selection is made.
    *  onFetchedComponents: Function to call when components for the selected project
    *      are fetched.
    *  onClear: Function to call when the clear button is clicked.
    */
function ProjectSearchViewModel(params) {
    var self = this;
    self.params = params || {};
    self.heading = params.heading;
    // Data passed to the project typehead
    self.data = params.data  || DEFAULT_FETCH_URL;
    self.submitText = params.submitText || 'Submit';
    self.projectPlaceholder = params.projectPlaceholder || 'Type to search for a project';
    self.componentPlaceholder = params.componentPlaceholder || 'Optional: Type to search for a component';

    /* Observables */
    // If params.enableComponents is passed in, use that value, otherwise default to true
    var enableComps = params.enableComponents;
    self.enableComponents = typeof enableComps !== 'undefined' ? enableComps : true;
    self.showComponents = ko.observable(self.enableComponents);
    self.selectedProject = ko.observable(null);
    self.selectedComponent = ko.observable(null);
    // The current user input. we store these so that we can show an error message
    // if the user clicks "Submit" when their selection isn't complete
    self.projectInput = ko.observable('');
    self.componentInput = ko.observable('');

    /* Computeds */
    self.hasSelectedProject = ko.computed(function() {
        return self.selectedProject() !== null;
    });
    self.hasSelectedComponent = ko.computed(function() {
        return self.selectedComponent() !== null;
    });

    self.showSubmit = ko.computed(function() {
        return self.hasSelectedProject();
    });

    // Used by the projectSearch binding to trigger teardown of the component typeahead
    // when the clear button is clicked
    self.cleared = ko.computed(function() {
        return self.selectedProject() == null;
    });

    // Project name to display in the text input
    self.selectedProjectName = ko.computed(function() {
        return self.selectedProject() ? self.selectedProject().name : '';
    });
    // Component name to display in the text input
    self.selectedComponentName = ko.computed(function() {
        return self.selectedComponent() ? self.selectedComponent().name : self.componentInput();
    });

    self.componentURL = ko.computed(function() {
        return self.selectedProject() ? self.selectedProject().urls.children : null;
    });

    /* Functions */
    self.onSubmit = function() {
        var func = params.onSubmit || noop;
        func(self.selectedProject(), self.selectedComponent(), self.projectInput(), self.componentInput());
    };
    self.onSelectedProject = function(selected) {
        self.selectedProject(selected);
        self.projectInput(selected.name);
        var func = params.onSelected || noop;
        func(selected);
    };
    self.onSelectedComponent = function(selected) {
        self.selectedComponent(selected);
        self.componentInput(selected.name);
        var func = params.onSelected || noop;
        func(selected);
    };
    self.onFetchedComponents = function(components) {
        // Show component search only if selected project has components
        self.showComponents(Boolean(components.length));
        var func = params.onFetchedComponents || noop;
        func(components);
    };
    self.clearSearch = function() {
        self.selectedComponent(null);
        self.componentInput('');
        self.selectedProject(null);
        self.projectInput('');
        // This must be set after clearing selectedProject
        // to avoid sending extra request in the projectSearch
        // binding handler
        self.showComponents(true);
        var func = params.onClear || noop;
        func();
    };
    self.clearComponentSearch = function() {
        self.selectedComponent(null);
        self.componentInput('');
        self.showComponents(true);
    };
}

ko.components.register('osf-project-search', {
    viewModel: ProjectSearchViewModel,
    template: {element: 'osf-project-search'}
});


///// Register /////

/**
    * ViewModel for the onboarding project registration component.
    *
    * Template: osf-ob-register element in components/dashboard_templates.mako
    */
function OBRegisterViewModel(params) {
    var self = this;
    self.params = params || {};
    self.data = params.data || DEFAULT_FETCH_URL;
    /* Observables */
    self.isOpen = ko.observable(false);
    /* Functions */
    self.open = function() {
        self.isOpen(true);
    };
    self.close = function() {
        self.isOpen(false);
    };
    self.toggle = function() {
        if (!self.isOpen()) {
            self.open();
        } else {
            self.close();
        }
    };
    /* On submit, redirect to the selected page's registration page */
    self.onRegisterSubmit = function(selected) {
        window.location = selected.urls.register;
    };
}

ko.components.register('osf-ob-register', {
    viewModel: OBRegisterViewModel,
    template: {element: 'osf-ob-register'}
});

///// UPLOADER //////
var iconList = [
'_blank',
'_page',
'aac',
'ai',
'aiff',
'avi',
'bmp',
'c',
'cpp',
'css',
'dat',
'dmg',
'doc',
'dotx',
'dwg',
'dxf',
'eps',
'exe',
'flv',
'gif',
'h',
'hpp',
'html',
'ics',
'iso',
'java',
'jpg',
'js',
'key',
'less',
'mid',
'mp3',
'mp4',
'mpg',
'odf',
'ods',
'odt',
'otp',
'ots',
'ott',
'pdf',
'php',
'png',
'ppt',
'psd',
'py',
'qt',
'rar',
'rb',
'rtf',
'sass',
'scss',
'sql',
'tga',
'tgz',
'tiff',
'txt',
'wav',
'xls',
'xlsx',
'xml',
'yml',
'zip'
];

// this takes a filename and finds the icon for it
function getFiletypeIcon(file_name){
    var baseUrl ='/static/img/upload_icons/';
    var ext = file_name.split('.').pop().toLowerCase();
    if(iconList.indexOf(ext)  !== -1){
        return baseUrl + ext + '.png';
    }else{
        return baseUrl + '_blank.png';
    }
}

// if has an extention return it, else return the last three chars
function getExtension(string){
    if(string.indexOf('.') !== -1){
        return string.split('.').pop().toLowerCase();
    }else{
        return string.substring(string.length - 3);
    }
}

// truncate long file names
function truncateFilename(string){
    var ext = getExtension(string);
    if (string.length > 40){
        return string.substring(0, 40-ext.length-3) + '...' + ext;
    } else{
        return string;
    }
}

/**
    * ViewModel for the onboarding uploader
    */
function OBUploaderViewModel(params) {
    var self = this;
    self.params = params || {};
    self.selector = self.params.selector || '#obDropzone';
    self.data = params.data || DEFAULT_FETCH_URL;
    /* Observables */
    self.isOpen = ko.observable(true);
    self.progress = ko.observable(0);
    self.showProgress = ko.observable(false);
    self.errorMessage = ko.observable('');
    self.enableUpload = ko.observable(true);
    self.filename = ko.observable('');
    self.iconSrc = ko.observable('');
    self.uploadCount = ko.observable(1);
    self.disableComponents = ko.observable(false);
    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');
    // The target node to upload to to
    self.target = ko.observable(null);
    /* Functions */
    self.toggle = function() {
        self.isOpen(!self.isOpen());
    };
    self.startUpload = function(selectedProject, selectedComponent, projectInput, componentInput) {
        if (!selectedComponent && componentInput.length) {
            var msg = 'Not a valid component selection. Clear your search or select a component from the dropdown.';
            self.changeMessage(msg, 'text-warning');
            return false;
        }
        if (self.dropzone.getUploadingFiles().length) {
            self.changeMessage('Please wait until the pending uploads are finished.');
            return false;
        }
        if (!self.dropzone.getQueuedFiles().length) {
            self.changeMessage('Please select at least one file to upload.', 'text-danger');
            return false;
        }
        var selected = selectedComponent || selectedProject;
        self.target(selected);
        self.clearMessages();
        self.showProgress(true);
        self.dropzone.options.url = function(files) {
            //Files is always an array but we only support uploading a single file at once
            var file = files[0];
            return waterbutler.buildUploadUrl('/', 'osfstorage', selected.id, file);
        };
        self.dropzone.processQueue(); // Tell Dropzone to process all queued files.
    };
    self.clearMessages = function() {
        self.message('');
        self.messageClass('text-info');
    };
    self.clearDropzone = function() {
        if (self.dropzone.getUploadingFiles().length) {
            self.changeMessage('Upload canceled.', 'text-info');
        } else {
            self.clearMessages();
        }
        self.enableUpload(true);
        // Pass true so that pending uploads are canceled
        self.dropzone.removeAllFiles(true);
        self.filename('');
        self.iconSrc('');
        self.progress = ko.observable(0);
        self.showProgress(false);
        self.uploadCount(1);
    };
    self.onFetchedComponents = function(components) {
        if (!components.length) {
            self.disableComponents(true);
        }
    };
    /** Change the flashed message. */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.clearMessages();
            }, timeout);
        }
    };


    var dropzoneOpts = {

        sending: function(file, xhr) {
            //Inject Bearer token
            xhr = $osf.setXHRAuthorization(xhr);
            //Hack to remove webkitheaders
            var _send = xhr.send;
            xhr.send = function() {
                _send.call(xhr, file);
            };
        },

        url: '/', // specified per upload
        autoProcessQueue: false,
        createImageThumbnails: false,
        //over
        maxFiles: 9001,
        uploadMultiple: false,
        //in mib
        maxFilesize: 128,

        acceptDirectories: false,

        method: 'PUT',
        uploadprogress: function(file, progress) { // progress bar update
            self.progress(progress);
        },
        parallelUploads: 1,
        // Don't use dropzone's default preview
        previewsContainer: false,
        // Cusom error messages
        dictFileTooBig: 'File is too big ({{filesize}} MB). Max filesize: {{maxFilesize}} MB.',
        // Set up listeners on initialization
        init: function() {
            var dropzone = this;

            // file add error logic
            this.on('error', function(file, message){
                dropzone.removeFile(file);
                if (dropzone.files.length === 0){
                    self.enableUpload(true);
                    dropzone.removeAllFiles(true);
                }

                if(message.message) {
                    message = JSON.parse(message.message);
                }

                // Use OSF-provided error message if possible
                // Otherwise, use generic message
                var msg = message.message_long || message;
                if (msg === 'Server responded with 0 code.' || msg.indexOf('409') !== -1) {
                    msg = 'Could not upload file. The file may be invalid.';
                }
                self.changeMessage(msg, 'text-danger');
            });
            this.on('drop',function(){ // clear errors on drop or click
                self.clearMessages();
            });
            // upload and process queue logic
            this.on('success',function(){
                self.filename(self.uploadCount() + ' / ' + dropzone.files.length + ' files');
                dropzone.processQueue(); // this is a bit hackish -- it fails to process full queue but this ensures it runs the process again after each success.
                var oldCount = self.uploadCount();
                self.uploadCount(oldCount + 1);

                if(self.uploadCount() > dropzone.files.length){ // when finished redirect to project/component page where uploaded.
                    self.changeMessage('Success!', 'text-success');
                    window.location = self.target().urls.files;
                }
            });

            // add file logic and dropzone to file display swap
            this.on('addedfile', function(file) {
                if(dropzone.files.length>1){
                    self.iconSrc('/static/img/upload_icons/multiple_blank.png');
                    self.filename(dropzone.files.length + ' files');
                }else{
                    var fileName = truncateFilename(dropzone.files[0].name);
                    self.iconSrc(getFiletypeIcon(fileName));
                    self.filename(fileName);
                }
                self.enableUpload(false);
            });
        }
    };
    self.dropzone = new Dropzone(self.selector, dropzoneOpts);
}

ko.components.register('osf-ob-uploader', {
    viewModel: OBUploaderViewModel,
    template: {element: 'osf-ob-uploader'}
});


function OBGoToViewModel(params) {
    var self = this;
    self.params = params;
    self.data = params.data || DEFAULT_FETCH_URL;
    /* Observables */
    self.isOpen = ko.observable(true);
    self.hasFocus = ko.observable(true);
        self.submitText = '<i class="fa fa-angle-double-right"></i> Go';
    /* Functions */
    self.toggle = function() {
        if (!self.isOpen()) {
            self.isOpen(true);
            self.hasFocus = ko.observable(true);
        } else {
            self.isOpen(false);
            self.hasFocus = ko.observable(false);
        }
    };
    self.onSubmit = function(selectedProject, selectedComponent) {
        var node = selectedComponent || selectedProject;
        window.location = node.urls.web;
    };
}

ko.components.register('osf-ob-goto', {
    viewModel: OBGoToViewModel,
    template: {element: 'osf-ob-goto'}
});
