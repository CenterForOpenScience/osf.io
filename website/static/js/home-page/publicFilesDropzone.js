var m = require('mithril');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');
var AddProject = require('js/addProjectPlugin');

require('css/dropzone-plugin.css');
require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');
var Dropzone = require('dropzone');

var ZeroClipboard = require('zeroclipboard');
var fileURL = "";
var fileURLArray = [];
var clip = "";

// Don't show dropped content if user drags outside dropzone
window.ondragover = function (e) {
    e.preventDefault();
};
window.ondrop = function (e) {
    e.preventDefault();
};


var publicFilesDropzone = {
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
                if (this.files.length <= 1) {
                    this.options.url = waterbutler.buildUploadUrl(false, 'osfstorage', window.contextVars.publicFilesId, file, {});
                    this.processFile(file);
                }
                else {
                    dangerCount = document.getElementsByClassName('alert-danger').length;
                    if (dangerCount === 0)
                        $osf.growl("Error", "You can only upload a maximum of " + this.options.maxFiles + " files at once. " +
                            "<br> To upload more files, refresh the page or click X on the top right. " +
                            "<br> Want to share more files? Create a new project.", "danger", 10000);

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
                var fileJson = JSON.parse((file.xhr.response));
                filePath = fileJson.path
                var url=(window.location.host+'/'+window.contextVars.publicFilesId+'/files/osfstorage'+ filePath);
                fileURL = url;
                fileURLArray.push(url);
                clip = new ZeroClipboard( document.getElementsByClassName('copy') );

                this.processQueue();
                file.previewElement.classList.add("dz-success");
                file.previewElement.classList.add("dz-preview-background-success");
                if (this.getQueuedFiles().length === 0 && this.getUploadingFiles().length === 0) {
                    if (this.files.length === 1)
                        $osf.growl("Success", this.files.length + " file was successfully uploaded to your public files project.", "success", 10000);
                    else
                        $osf.growl("Success", this.files.length + " files were successfully uploaded to your public files project.", "success", 10000);

                }
            },


            error: function (file, message) {
                this.files.length--;
                file.previewElement.classList.add("dz-error");
                file.previewElement.classList.add("dz-preview-background-error");
                // Need the padding change twice because the padding doesn't resize when there is an error
                $('.drop-zone-format').css({'padding-bottom': '10px'});
                // get file size in MB, rounded to 1 decimal place
                var fileSizeMB = Math.round(file.size / (1000 * 1000) * 10) / 10;
                if (fileSizeMB > this.options.maxFilesize) {
                    $osf.growl("Error", file.name + " could not be uploaded. <br> The file is " + fileSizeMB + " MB," +
                        " which exceeds the max file size of " + this.options.maxFilesize + " MB", "danger", 5000);
                }
            },

        };


        var shareLink = "";
        $("#publicFilesDropzone").on("click", "div.dz-share", function(e){
            var el = document.getElementsByClassName('dz-preview');
                for (var i = 0; i < el.length; i++) {
                    if($(".dz-share").index(this) == i){
                        shareLink = fileURLArray[i];
                    }
                }
           clip.setData("text/plain" , shareLink);
           $(e.target).parent().siblings('.alertbubble').finish().show().delay(1000).fadeOut("slow");
        });


        var template = m('div.dz-preview.dz-processing.dz-file-preview',
                            m('div.dz-details',
                                m('div.dz-filename',
                                    m('span[data-dz-name]')
                                ),
                                m('div[data-dz-size].dz-size'),
                                m('img[data-dz-thumbnail]')
                            ),
                            m('div.dz-progress',
                                m('span[data-dz-uploadprogress].dz-upload')
                            ),
                            m(".dz-share", [" ",m("i.fa.fa-share-alt.copy[aria-hidden='true'][data-clipboard-text='"+shareLink+"']")," "])," ",m("span.alertbubble.alertbubblepos", [m("i.fa.fa-clipboard[aria-hidden='true']")," Copied"]),

                            m('div.dz-success-mark',
                                m('span.glyphicon.glyphicon-ok-circle')
                            ),
                            m('div.dz-error-mark',
                                m('span.glyphicon.glyphicon-remove-circle')
                            ),
                            m('div.dz-error-message',
                                m('span[data-dz-errormessage]', 'Error: Your file could not be uploaded')
                            )
                        );

        $('#publicFilesDropzone').dropzone({
           url: 'placeholder',
            previewTemplate: $osf.mithrilToStr(template)
        });
        // cache the selector to avoid duplicate selector warning
        var $glyph = $('#glyph');
        $('#ShareButton').click(function () {
                document.getElementById("ShareButton").style.cursor = "pointer";
                $('#shareWindowDropzone').stop().slideToggle();
                $glyph.toggleClass('glyphicon glyphicon-chevron-down');
                $glyph.toggleClass('glyphicon glyphicon-chevron-up');
            }
        );

    },

    view: function (ctrl, args) {
        function headerTemplate() {
            return [
                m('h2.col-xs-6', 'Dashboard'), m('m-b-lg.pull-right',
                    m('button.btn.btn-primary.m-t-md.f-w-xl #ShareButton',
                        m('span.glyphicon.glyphicon-chevron-down #glyph'), ' Upload Public Files'), m.component(AddProject, {
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

        return m('.row-bottom-xs', m('.col-xs-12.m-b-sm', headerTemplate()),
            m('h4.text-center #LinkToShareFiles', 'View your ', m('a', {
                    href: '/share_window/', onclick: function () {
                    }
                }, 'Public Files Project '),
                m('i.fa.fa-question-circle.text-muted', {
                    'data-toggle': 'tooltip',
                    'title': 'The Public Files Project allows you to easily collaborate and share your files with anybody.',
                    'data-placement': 'bottom'
                }, '')
            ),
            m('div.p-v-xs.drop-zone-format.drop-zone-invis .pointer .panel #publicFilesDropzone',
                m('button.close[aria-label="Close"]', {
                        onclick: function () {
                            $('#publicFilesDropzone').hide();
                            $('div.dz-preview').remove();
                            $glyph.toggleClass('glyphicon glyphicon-chevron-up');
                            $glyph.toggleClass('glyphicon glyphicon-chevron-down');
                            $('.drop-zone-format').css({'padding-bottom': '175px'});
                        }
                    }, m('.drop-zone-close', '×')
                ),
                m('h1.dz-p.text-center #shareWindowDropzone', 'Drop files to upload',
                    m('h5','Click the box to upload files. Files are automatically uploaded to your ',
                    m('a', {
                        href: '/public_files/', onclick: function (e) {
                            // Prevent clicking of link from opening file uploader
                            e.stopImmediatePropagation();
                        }
                    }, 'Public Files')
                )
            )
            )
        );
    }
};

module.exports = publicFilesDropzone;
