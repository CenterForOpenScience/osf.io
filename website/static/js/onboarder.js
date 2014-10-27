/**
 * Components and binding handlers for the dashboard "onboarding" interface.
 * Includes a custom component for OSF project typeahead search, as well
 * the viewmodels for each of the individual onboarding widgets.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['typeahead'], function() {
            factory(jQuery, ko);
            $script.done('onboarder');
        });
    } else {
        factory(jQuery, ko);
    }
}(this, function ($, ko) {
    'use strict';

    function noop() {}
    var MAX_RESULTS = 14;

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

    function initTypeahead(element, myProjects, viewModel, params){
        var $inputElem = $(element);
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
            source: substringMatcher(myProjects)
        });

        $inputElem.bind('typeahead:selected', function(obj, datum) {
            // TODO: Use data-binds to apply these styles
            // $inputElem.css('background-color', '#f5f5f5')
            //     .css('border', '2px solid LightGreen');
            // Call the parent viewModel's onSelected
            var onSelected = params.onSelected || viewModel.onSelected;
            onSelected(datum.value);
        });
        return $inputElem;
    }

    /**
     * Binding handler for attaching an OSF typeahead search input.
     * Takes an optional parameter onSelected, which is called when a project
     * is selected.
     *
     * Example:
     *
     *  <div data-bind="projectSearch: {onSelected: onSelected}></div>
     */
    var DEFAULT_FETCH_URL = '/api/v1/dashboard/get_nodes/';
    ko.bindingHandlers.projectSearch = {
        init: function(element, valueAccessor, allBindings, viewModel) {
            var params = valueAccessor();
            var url = params.url || DEFAULT_FETCH_URL;
            var request = $.getJSON(url, function (projects) {
                var myProjects = projects.nodes.map(
                    function(item){return {
                        name: item.title,
                        id: item.id,
                        urls: {
                            web: item.url,
                            api: item.api_url,
                            register: item.url + 'register/',
                        }
                    };
                });
                var $typeahead = initTypeahead(element, myProjects, viewModel, params);
                viewModel.$typeahead = $typeahead;
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Could not fetch dashboard nodes.', {
                    url: url, textStatus: textStatus, error: error
                });
            });
        }
    };

    /**
     * ViewModel for the OSF project typeahead search widget.
     *
     * Template: osf-project-search element in components/dashboard_templates.mako
     *
     * Params:
     *  onSubmit: Function to call on submit. Receives the selected item.
     */
    function ProjectSearchViewModel(params) {
        var self = this;
        self.params = params;
        self.heading = params.heading;
        /* Observables */
        self.selectedProject = ko.observable(null);
        /* Computeds */
        self.hasSelected = ko.computed(function() {
            return self.selectedProject() !== null;
        });
        // Project name to display in the text input
        self.selectedProjectName = ko.computed(function() {
            return self.selectedProject() ? self.selectedProject().name : '';
        });
        /* Functions */
        self.onSubmit = function() {
            var func = params.onSubmit || noop;
            func(self.selectedProject());
        };
        self.onSelected = function(selected) {
            self.selectedProject(selected);
        };
        self.clearSearch = function() {
            self.selectedProject(null);
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
        self.params = params;
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

    /** Redirect to a project or component based on its linkId property **/
    function redirectToPOC(poc){ // str project or componenet (poc)
        var url = '/'+ $addLink.prop('linkID' + poc);
        if(url !== '/undefined'){
            window.location = url;
        }
    }

    // ensure it is not
    function getRoute(addLink){
        if(addLink.prop('routeIDComponent')){
            return addLink.prop('routeIDComponent');
        } else{
            return addLink.prop('routeIDProject');
        }
    }

    // this takes a filename and finds the icon for it
    function getFiletypeIconName(file_name){
        var ext = file_name.split('.').pop().toLowerCase();
        if(iconList.indexOf(ext)  !== -1){
            return ext + '.png';
        }else{
            return '_blank.png';
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
     * ViewModel for the onboarding Dropzone component
     */
    function OBDropzoneViewModel(params) {
        var self = this;
        self.params = params || {};
        self.selector = self.params.selector || '#obDropzone';
        /* Observables */
        self.progress = ko.observable(0);
        self.showProgress = ko.observable(false);
        self.errorMessage = ko.observable('');
        self.enableUpload = ko.observable(true);
        self.filename = ko.observable('');
        self.iconSrc = ko.observable('//:0');
        self.uploadCount = ko.observable(0);

        /* Functions */
        self.startUpload = function() {
            self.clearErrors();
            console.log('starting upload');
            // var projectRoute = getRoute($addLink);
//             $addLink.attr('disabled', true);
//             $uploadProgress.show();
            self.showProgress(true);
            // self.dropzone.options = projectRoute + 'osffiles/';
            // self.dropzone.processQueue();

        };
        self.clearErrors = function() {
            console.log('clearing errors');
            self.errorMessage('');
        };
        self.clearDropzone = function() {
            self.enableUpload(true);
            self.dropzone.removeAllFiles();
            self.clearErrors();
        };

        var dropzoneOpts = {

            url: '/', // specified per upload
            autoProcessQueue: false,
            createImageThumbnails: false,
            //over
            maxFiles: 9001,
            uploadMultiple: false,
            //in mib
            maxFilesize: 128,

            uploadprogress: function(file, progress) { // progress bar update
                self.progress(progress);
            },

            init: function() {
                var dropzone = this;

                // file add error logic
                this.on('error', function(file){
                    var fileName = file.name;
                    var fileSize = file.size;
                    dropzone.removeFile(file);
                    if(dropzone.files.length === 0){
                        self.enableUpload(true);
                        dropzone.removeAllFiles();
                    }

                    if(fileSize > self.options.maxFilesize){
                        self.errorMessage(fileName + ' is too big (max = ' +
                                         self.options.maxFilesize +
                                         ' MiB) and was not added to the upload queue.');
                    } else {
                        self.errorMessage(fileName + 'could not be added to the upload queue');
                        Raven.captureMessage('Could not upload: ' + fileName);
                    }
                });
                this.on('drop',function(){ // clear errors on drop or click
                    self.clearErrors();
                });
                // upload and process queue logic
                this.on('success',function(){
                    self.filename(self.uploadCount() + ' / ' + dropzone.files.length + ' files');
                    self.processQueue(); // this is a bit hackish -- it fails to process full queue but this ensures it runs the process again after each success.
                    self.uploadCount(self.uploadCount() + 1);

                    if(uploadCounter > dropzone.files.length){ // when finished redirect to project/component page where uploaded.
                        console.log('TODO: redirect to project page');
                        // //redirect to project or componenet
                        // if(typeof $addLink.prop('linkIDComponent')!=='undefined'){
                        //     redirectToPOC('Component');
                        // }else{
                        //     redirectToPOC('Project');
                        // }
                    }
                });

                // add file logic and dropzone to file display swap
                this.on('addedfile', function() {
                    if(dropzone.files.length>1){
                        self.iconSrc('/static/img/upload_icons/multiple_blank.png');
                        self.filename(dropzone.files.length + ' files');
                    }else{
                        // $('#obDropzone').click();
                        var fileName = truncateFilename(dropzone.files[0].name);
                        self.iconSrc('/static/img/upload_icons/' + getFiletypeIconName(fileName));
                        self.filename(fileName);
                    }
                    self.enableUpload(false);

                    // TODO: Focus project search
                    // $inputProjectAddFile.focus();
                    // $inputProjectAddFile.css('background-color', 'white !important;');
                });
            }
        };
        self.dropzone = new Dropzone(self.selector, dropzoneOpts);
    }

    ko.components.register('osf-ob-dropzone', {
        viewModel: OBDropzoneViewModel,
        template: {element: 'osf-ob-dropzone'}
    });

    /**
     * ViewModel for the onboarding uploader
     */
    function OBUploaderViewModel(params) {
        var self = this;
        self.params = params;
    }

    ko.components.register('osf-ob-uploader', {
        viewModel: OBUploaderViewModel,
        template: {element: 'osf-ob-uploader'}
    });
}));
