var m = require('mithril');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');
var AddProject = require('js/addProjectPlugin');

require('css/dropzone-plugin.css');
require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');
var Dropzone = require('dropzone');

// Don't show dropped content if user drags outside dropzone
window.ondragover = function (e) {
    e.preventDefault();
};
window.ondrop = function (e) {
    e.preventDefault();
};

var ShareWindowDropzone = {
    controller: function () {
        var dangerCount = 0;
        Dropzone.options.shareWindowDropzone = {
            // Dropzone is setup to upload multiple files in one request this configuration forces it to do upload file-by-
            //file, one request at a time.
            clickable: '#shareWindowDropzone',
            // number of files to process in parallel
            parallelUploads: 1,
            // prevents default uploading; call processQueue() to upload
            autoProcessQueue: false,
            withCredentials: true,
            uploadMultiple: true,
            method: 'put',
            // in MB; lower to test errors. Default is 256 MB.
            maxFilesize: 1,
            maxFiles: 10,
            // checks if file is valid; if so, then adds to queue
            init: function () {
                // When user clicks close button on top right, reset the number of files
                var _this = this;
                $('button.close').on('click', function () {
                    _this.files.length = 0;
                });

            },
            accept: function (file, done) {
                if (this.files.length <= 10) {
                    this.options.url = waterbutler.buildUploadUrl(false, 'osfstorage', window.contextVars['shareWindowId'], file, {});
                    this.processFile(file);
                }
                else {
                    dangerCount = document.getElementsByClassName('alert').length;
                    if (dangerCount === 0)
                        $osf.growl("Error", "You can only upload a maximum of 10 files at once.", "danger", 5000);

                    return this.emit("error", file);
                }
            },

            sending: function (file, xhr) {
                //Hack to remove webkitheaders
                var _send = xhr.send;
                xhr.send = function () {
                    _send.call(xhr, file);
                };
                $('.drop-zone-format').css({'padding-bottom': '10px'});
            },

            success: function (file, xhr) {
                this.processQueue();
                file.previewElement.classList.add("dz-success");
                file.previewElement.classList.add("dz-preview-background-success");
                if (this.getQueuedFiles().length === 0 && this.getUploadingFiles().length === 0) {
                    if (this.files.length === 1)
                        $osf.growl("Success", this.files.length + " file was successfully uploaded to your public files project.", "success", 5000);
                    else
                        $osf.growl("Success", this.files.length + " files were successfully uploaded to your public files project.", "success", 5000);

                }
            },


            error: function (file, message) {
                this.files.length--;
                file.previewElement.classList.add("dz-error");
                file.previewElement.classList.add("dz-preview-background-error");
                // Need the padding change twice because the padding doesn't resize when there is an error
                $('.drop-zone-format').css({'padding-bottom': '10px'});
            },

        };

        $('#shareWindowDropzone').dropzone({
            url: 'placeholder',
            previewTemplate: '<div class="dz-preview dz-processing dz-file-preview"><div class="dz-details"><div class="dz-filename"><span data-dz-name></span></div>' +
            '<div class="dz-size" data-dz-size></div><img data-dz-thumbnail /></div><div class="dz-progress"><span class="dz-upload" data-dz-uploadprogress></span></div>' +
            '<div class="dz-success-mark"><span class="glyphicon glyphicon-ok-circle"></span></div>' +
            '<div class="dz-error-mark"><span class="glyphicon glyphicon-remove-circle"></span></div><div class="dz-error-message">' +
            '<span data-dz-errormessage>Error: Your file could not be uploaded.</span></div></div>',
        });


        $('#ShareButton').click(function () {
            document.getElementById("ShareButton").style.cursor = "pointer";
            $('#shareWindowDropzone').stop().slideToggle();
            $('#glyph').toggleClass('glyphicon glyphicon-chevron-down');
            $('#glyph').toggleClass('glyphicon glyphicon-chevron-up');

        });

    },

    view: function (ctrl, args) {
        function headerTemplate() {
            return [m('h2.col-xs-4', 'Dashboard'), m('m-b-lg.col-xs-8.pull-right.drop-zone-disp',
                m('.pull-right', m('button.btn.btn-primary.m-t-md.f-w-xl #ShareButton',
                    m('span.glyphicon.glyphicon-chevron-down #glyph'), 'Upload Public Files'), m.component(AddProject, {
                    buttonTemplate: m('button.btn.btn-success.btn-success-high-contrast.m-t-md.f-w-xl.pull-right[data-toggle="modal"][data-target="#addProjectFromHome"]',
                        {
                            onclick: function () {
                                $osf.trackClick('quickSearch', 'add-project', 'open-add-project-modal');
                            }
                        }, 'Create new project'),
                    modalID: 'addProjectFromHome',
                    stayCallback: function _stayCallback_inPanel() {
                        document.location.reload(true);
                    },
                    trackingCategory: 'quickSearch',
                    trackingAction: 'add-project',
                    templatesFetcher: ctrl.templateNodes
                })))];
        }

        // Activate Public Files tooltip info
        $('[data-toggle="tooltip"]').tooltip();
        return m('.row-bottom-xs', m('.col-xs-12.m-b-sm', headerTemplate()),
            m('h4.text-center #LinkToShareFiles', 'View your ', m('a', {
                    href: '/share_window/', onclick: function () {
                    }
                }, 'Public Files Project '),
                m('i.fa.fa-question-circle.text-muted', {
                    'data-toggle': 'tooltip',
                    'title': 'The Public Files Project allows you to easily collaborate and share your files with anybody.',
                    'data-placement': 'bottom'
                }, '')),
            m('div.p-v-xs.drop-zone-format.drop-zone-invis .pointer .panel #shareWindowDropzone',
                m('button.close[aria-label="Close"]', {
                    onclick: function () {
                        $('#shareWindowDropzone').hide();
                        $('div.dz-preview').remove();
                        $('#glyph').toggleClass('glyphicon glyphicon-chevron-up');
                        $('#glyph').toggleClass('glyphicon glyphicon-chevron-down');
                        $('.drop-zone-format').css({'padding-bottom': '175px'});
                    }
                }, m('.drop-zone-close', '×')),
                m('.dz-p.text-center.top#shareWindowDropzone', m('h1.drop-zone-bold', 'Drop files to upload'),
                    'Click the box to upload files. Files are automatically uploaded to your ',
                    m('a', {
                        href: '/share_window/', onclick: function (e) {
                            e.stopImmediatePropagation();
                        }
                    }, 'Public Files'))));
    }
};

module.exports = ShareWindowDropzone;
