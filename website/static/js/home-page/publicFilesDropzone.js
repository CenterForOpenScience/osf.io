var m = require('mithril');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');
var AddProject = require('js/addProjectPlugin');
var dropzonePreviewTemplate = require('js/home-page/dropzonePreviewTemplate');

require('css/dropzone-plugin.css');
require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');

var Dropzone = require('dropzone');

var ZeroClipboard = require('zeroclipboard');
var fileURL = '';
var fileURLArray = [];
var clip = '';

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
            // in MB; lower to test errors. Default is 256 MB.
            maxFilesize: 1,
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
                }
                else {
                    dangerCount = document.getElementsByClassName('alert-danger').length;
                    if (dangerCount === 0)
                        $osf.growl('Error', 'You can upload a maximum of ' + this.options.maxFiles + ' files at once. ' +
                            '<br> To upload more files, refresh the page or click X on the top right. ' +
                            '<br> Want to share more files? Create a new project.', 'danger', 5000);

                    return this.emit('error', file);
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
                buttonContainer = document.createElement('div');
                file.previewElement.appendChild(buttonContainer);

                var fileJson = JSON.parse((file.xhr.response));
                var link = waterbutler.buildDownloadUrl(fileJson.path, 'osfstorage', window.contextVars.publicFilesId, file.name, {});
                m.render(buttonContainer, dropzonePreviewTemplate.shareButton(link));

                this.processQueue();
                file.previewElement.classList.add('dz-success');
                file.previewElement.classList.add('dz-preview-background-success');
                if (this.getQueuedFiles().length === 0 && this.getUploadingFiles().length === 0) {
                    if (this.files.length === 1)
                        $osf.growl('Upload Successful', this.files.length + ' file was successfully uploaded to your public files project.', 'success', 5000);
                    else
                        $osf.growl('Upload Successful', this.files.length + ' files were successfully uploaded to your public files project.', 'success', 5000);

                }
            },


            error: function (file, message) {
                this.files.length--;
                // Keeping the old behavior in case we want to revert it some time
                file.previewElement.classList.add('dz-error');
                file.previewElement.classList.add('dz-preview-background-error');
                file.previewElement.remove(); // Doesn't show the preview
                // Need the padding change twice because the padding doesn't resize when there is an error
                // get file size in MB, rounded to 1 decimal place
                var fileSizeMB = Math.round(file.size / (1000 * 1000) * 10) / 10;
                if (fileSizeMB > this.options.maxFilesize) {
                    $osf.growl('Upload Failed', file.name + ' could not be uploaded. <br> The file is ' + fileSizeMB + ' MB,' +
                        ' which exceeds the max file size of ' + this.options.maxFilesize + ' MB', 'danger', 5000);
                }
            },

        };

        $('#publicFilesDropzone').on('click', 'div.dz-share', function (e) {
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
                        from: 'top',
                        align: 'center'
                    },
                    animate: {
                        enter: 'animated fadeInDown',
                        exit: 'animated fadeOut'
                    }
                });
            }
        });


        $('#publicFilesDropzone').dropzone({
           url: 'placeholder',
           previewTemplate: $osf.mithrilToStr(dropzonePreviewTemplate.dropzonePreviewTemplate())
        });

        var isSliderOpen = false;
        $('#ShareButton').click(function () {
                $('#publicFilesDropzone').stop().slideToggle();
                $('#publicFilesDropzone').css('display', 'flex');
                if(isSliderOpen){
                    $('.drop-zone-close').hide().slideUp( 300 ).fadeOut( 'slow' );
                    isSliderOpen = false;
                }else{
                    $('.drop-zone-close').show('fast');
                    //$( ".drop-zone-close" ).slideDown( "slow" );
                    isSliderOpen = true;
                }

                $('#glyphchevron').toggleClass('glyphicon glyphicon-chevron-down glyphicon glyphicon-chevron-up');
            }
        );
    },

    view: function (ctrl, args) {
        function headerTemplate() {
            return [
                m('h2.col-xs-6', 'Dashboard'), m('m-b-lg.pull-right',
                    m('button.btn.btn-primary.m-t-md.f-w-xl #ShareButton',
                        m('span.glyphicon.glyphicon-chevron-down #glyphchevron'), ' Upload Public Files'), m.component(AddProject, {
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

        // Activate Public Files tooltip info
        $('[data-toggle="tooltip"]').tooltip();

        // unexplainable large margin between dashboard and quick search projects
        return m('.row', m('.col-xs-12.m-b-sm', headerTemplate()),
            m('div.p-v-xs.drop-zone-format.drop-zone-invis .pointer .panel #publicFilesDropzone',
                m('button.close[aria-label="Close"]', {
                        onclick: function () {
                            $('#publicFilesDropzone').hide();
                            $('div.dz-preview').remove();
                            $('#glyphchevron').toggleClass('glyphicon glyphicon-chevron-up glyphicon glyphicon-chevron-down');
                            $('.drop-zone-format').css({'padding-bottom': '175px'});
                        }
                    }, m('.drop-zone-close', '×')
                ),
                m('h1.dz-p.text-center #publicFilesDropzone', 'Drop files to upload',
                    m('h5', 'Click the box to upload files. Files are automatically uploaded to your ',
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
                )
            )
        );
    }
};


module.exports = PublicFilesDropzone;
