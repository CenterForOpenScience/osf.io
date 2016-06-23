var m = require('mithril');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');
var AddProject = require('js/addProjectPlugin');
var dropzonePreviewTemplate = require('js/home-page/dropzonePreviewTemplate');

require('css/dropzone-plugin.css');
require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');

var Dropzone = require('dropzone');
var Fangorn = require('js/fangorn');

// Don't show dropped content if user drags outside dropzone
window.ondragover = function (e) {
    e.preventDefault();
};
window.ondrop = function (e) {
    e.preventDefault();
};


var PublicFilesDropzone = {
    controller: function () {
        var dangerCount = 0;
        Dropzone.options.publicFilesDropzone = {
            // Dropzone is setup to upload multiple files in one request this configuration forces it to do upload file-by-
            //file, one request at a time.
            clickable: '#publicFilesDropzone',
            // number of files to process in parallel
            parallelUploads: 1,
            // prevents default uploading; call processQueue() to upload
            autoProcessQueue: false,
            withCredentials: true,
            method: 'put',
            filesizeBase: 1024,
            // in MB; lower to test errors. Default is 256 MB.
            //maxFilesize: 1,
            maxFiles: 1,
            // checks if file is valid; if so, then adds to queue
            init: function () {
                // When user clicks close button on top right, reset the number of files
                var _this = this;
                $('button.close').on('click', function () {
                    _this.files.length = 0;
                });
            },

            accept: function (file, done) {
                if (this.files.length <= this.options.maxFiles) {
                    this.options.url = waterbutler.buildUploadUrl(false, 'osfstorage', window.contextVars.publicFilesId, file, {});
                    this.processFile(file);
                    $('div.h2.text-center.m-t-lg').hide();
                }
                else {
                    dangerCount = document.getElementsByClassName('alert-danger').length;
                    dangerCount === 0 ?
                        $osf.growl("Upload Failed", "You can upload a maximum of " + this.options.maxFiles + " files at once. " +
                            "<br> To upload more files, refresh the page or click X on the top right. " +
                            "<br> Want to share more files? Create a new project.", "danger", 5000) : '';
                    this.removeFile(file);
                }
            },

            sending: function (file, xhr) {
                //Hack to remove webkitheaders
                var _send = xhr.send;
                xhr.send = function () {
                    _send.call(xhr, file);
                };
                $('.panel-body').append(file.previewElement);
                var iconSpan = document.createElement('span');
                $('div.dz-center').prepend(iconSpan);
                m.render(iconSpan, dropzonePreviewTemplate.resolveIcon(file));
            },

            success: function (file, xhr) {
                var buttonContainer = document.createElement('div');
                $('div.col-sm-6').append(buttonContainer);
                var fileJson = JSON.parse((file.xhr.response));
                var link = waterbutler.buildDownloadUrl(fileJson.path, 'osfstorage', window.contextVars.publicFilesId, {});
                m.render(buttonContainer, dropzonePreviewTemplate.shareButton(link));
                this.processQueue();

                $('.logo-spin').remove();
                $('span.p-md').remove();
                $('span.button.close').css('visibility', 'hidden');
                file.previewElement.classList.add('dz-success');
                file.previewElement.classList.add('dz-preview-background-success');
                $('div.dz-progress').remove();

                if (this.getQueuedFiles().length === 0 && this.getUploadingFiles().length === 0) {
                    if (this.files.length === 1)
                        $osf.growl("Upload Successful", this.files[0].name + " has been successfully uploaded to your public files project.", "success", 5000);
                    else
                        $osf.growl("Upload Successful", this.files.length + " files were successfully uploaded to your public files project.", "success", 5000);

                }
                // allow for multiple uploads of one file at a time
                this.files.length--;
            },


            error: function (file, message) {
                this.files.length--;
                // Keeping the old behavior in case we want to revert it some time
                file.previewElement.classList.add('dz-error');
                file.previewElement.classList.add('dz-preview-background-error');
                file.previewElement.remove(); // Doesn't show the preview
                // Need the padding change twice because the padding doesn't resize when there is an error
                // get file size in MB, rounded to 1 decimal place
                var fileSizeMB = Math.round(file.size / (this.options.filesizeBase * this.options.filesizeBase) * 10) / 10;
                if (fileSizeMB > this.options.maxFilesize) {
                    $osf.growl("Upload Failed", file.name + " could not be uploaded. <br> The file is " + fileSizeMB + " MB," +
                        " which exceeds the max file size of " + this.options.maxFilesize + " MB", "danger", 5000);
                }
            },

        };

        var $publicFiles = $('#publicFilesDropzone');

        $('.container', '.quickSearch', 'row', '.panel-body', '.dz-body-height', '#publicFilesDropzone').bind({
            dragenter: function () {
                $('#dz-dragmessage').show();
            },
            dragleave: function () {
                $('#dz-dragmessage').hide();
            }
        });

        $publicFiles.on("click", ".dz-share", function (e) {
            var infoCount = document.getElementsByClassName('alert-info').length;
            if (infoCount === 0) {
                $.growl({
                    icon: 'fa fa-clipboard',
                    message: ' Link copied to clipboard'
                }, {
                    type: 'info',
                    allow_dismiss: false,
                    mouse_over: 'pause',
                    placement: {
                        from: "top",
                        align: "center"
                    },
                    animate: {
                        enter: 'animated fadeInDown',
                        exit: 'animated fadeOut'
                    }
                });
            }
        });

        $publicFiles.dropzone({
            url: 'placeholder',
            previewTemplate: $osf.mithrilToStr(dropzonePreviewTemplate.dropzonePreviewTemplate())
        });

        $('#ShareButton').click(function () {
                $publicFiles.stop().slideToggle();
                $publicFiles.css('display', 'inline-block');
                $('#glyphchevron').toggleClass('fa fa-chevron-down fa fa-chevron-up');
                if ($('div.dz-preview').length === 0)
                    $('div.h2.text-center.m-t-lg').show();

            }
        );

    },

    view: function (ctrl, args) {
        function headerTemplate() {
            return [
                m('h2.col-xs-6', 'Dashboard'), m('m-b-lg.pull-right',
                    m('button.btn.btn-primary.m-t-md.m-r-sm.f-w-xl #ShareButton',
                        'Upload Public Files ', m('span.fa.fa-chevron-down #glyphchevron')), m.component(AddProject, {
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
                        }
                    )
                )
            ];
        }

        function closeButton() {
            return [
                m('button.close.fa.fa-times.dz-font[aria-label="Close"].pull-right', {
                        onclick: function () {
                            $('#publicFilesDropzone').hide();
                            $('div.dz-preview').remove();
                            $('#glyphchevron').toggleClass('fa fa-chevron-up fa fa-chevron-down');
                        }
                    }
                )
            ]
        }

        function publicFilesHelpButton() {
            return [
                m('button.btn.fa.fa-info.close.dz-font[aria-label="Drag-and-Drop Help"][data-toggle="modal"][data-target="#dropZoneHelpModal"]'),
                m('.modal.fade.dz-cursor-default #dropZoneHelpModal',
                    m('.modal-dialog',
                        m('.modal-content',
                            m('.modal-header',
                                m('button.close[data-dismiss="modal"]', '×'),
                                m('h4.modal-title', 'Public Files Drag-and-Drop Help')),
                            m('.modal-body', m('p', 'Files uploaded here will be automatically added to your public files. Additionally: '),
                                m('ul',
                                    m('li', 'You may upload one file at a time.'),
                                    m('li', 'File uploads may be up to 256 MB.'),
                                    m('li', 'To upload more files, refresh the page or click ', m('span.i.fa.fa-times')),
                                    m('li', 'To show and hide your uploads, toggle the ', m('strong', 'Upload Public Files'), ' button.'),
                                    m('li', 'Click ', m('span.i.fa.fa-share-alt'), ' to copy a download link for that file to your clipboard. Share this link with others!'))
                            ),
                            m('.modal-footer', m('button.btn.btn-default[data-dismiss="modal"]', 'Close'))
                        )
                    )
                )
            ]
        }

        function publicFilesHeader() {
            return [
                m('h1.dz-p.text-center.f-w-lg', 'Upload ', m('a', {
                    href: '/public_files/', onclick: function (e) {
                    }
                }, 'Public Files'))
            ]
        }

        // Activate Public Files tooltip info
        $('[data-toggle="tooltip"]').tooltip();
        return m('.row',
            m('.col-xs-12', headerTemplate()
            ),
            m('div.drop-zone-format.panel .panel-default #publicFilesDropzone',
                m('.panel-heading', closeButton(),
                    publicFilesHelpButton(), publicFilesHeader()
                ),
                m('.panel-body.dz-body-height', m('div.h2.text-center.m-t-lg.dz-bold', 'Drop files to upload'),
                    m('span#dz-dragmessage.fa.fa-plus-square-o.fa-5x.dz-dragmessage','')
                ),
                m('.panel-footer.dz-cursor-default.clearfix',
                    m('.pull-left',
                        m('h5', 'Files are uploaded to your ',
                            m('a', {
                                href: '/public_files/', onclick: function (e) {
                                    // Prevent clicking of link from opening file uploader
                                    e.stopImmediatePropagation();
                                }
                            }, 'Public Files'), ' ', m('i.fa.fa-question-circle.text-muted', {
                                'data-toggle': 'tooltip',
                                'title': 'The Public Files Project allows you to easily collaborate and share your files with anybody.',
                                'data-placement': 'bottom'
                            }, '')
                        )
                    ),
                    m('.pull-right',
                        m('button.btn.btn-success.m-r-sm #publicFilesDropzone', 'Choose a file'),
                        m('button.btn.btn-default', {
                            onclick: function () {
                                $('#publicFilesDropzone').hide();
                                $('div.dz-preview').remove();
                                $('#glyphchevron').toggleClass('fa fa-chevron-up fa fa-chevron-down');
                            }
                        }, 'Done')
                    )
                )
            )
        );
    }
};


module.exports = PublicFilesDropzone;
