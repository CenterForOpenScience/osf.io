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
                    this.options.url = waterbutler.buildUploadUrl(false, 'osfstorage', window.contextVars['shareWindowId'], file, {});
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
                filePath = fileJson.path;
                var url = (window.location.host + '/' + window.contextVars['shareWindowId'] + '/files/osfstorage' + filePath);
                fileURL = url;
                fileURLArray.push(url);
                clip = new ZeroClipboard(document.getElementsByClassName('copy'));

                this.processQueue();
                file.previewElement.classList.add("dz-success");
                file.previewElement.classList.add("dz-preview-background-success");
                if (this.getQueuedFiles().length === 0 && this.getUploadingFiles().length === 0) {
                    if (this.files.length === 1)
                        $osf.growl("Upload Successful", this.files.length + " file was successfully uploaded to your public files project.", "success", 10000);
                    else
                        $osf.growl("Upload Successful", this.files.length + " files were successfully uploaded to your public files project.", "success", 10000);

                }
            },


            error: function (file, message) {
                this.files.length--;
                // Keeping the old behavior in case we want to revert it some time
                file.previewElement.classList.add("dz-error");
                file.previewElement.classList.add("dz-preview-background-error");
                file.previewElement.remove(); // Doesn't show the preview
                // Need the padding change twice because the padding doesn't resize when there is an error
                // get file size in MB, rounded to 1 decimal place
                var fileSizeMB = Math.round(file.size / (1000 * 1000) * 10) / 10;
                if (fileSizeMB > this.options.maxFilesize) {
                    $osf.growl("Upload Failed", file.name + " could not be uploaded. <br> The file is " + fileSizeMB + " MB," +
                        " which exceeds the max file size of " + this.options.maxFilesize + " MB", "danger", 5000);
                }
            },

        };


        $("#shareWindowDropzone").on("click", "div.dz-share", function (e) {
            var shareLink = "";
            var el = document.getElementsByClassName('dz-preview');
            for (var i = 0; i < el.length; i++) {
                // console.log(i +" > "+ fileURLArray[i]);
                //text(fileURLArray[i]);
                if ($(".dz-share").index(this) == i) {
                    shareLink = fileURLArray[i];
                }
            }
            clip.setData("text/plain", shareLink);
            console.log(clip.getData());

            $(e.target).parent().siblings('.alertbubble').finish().show().delay(1000).fadeOut("slow");
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
                }
            });
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
            m(".dz-share", [" ", m("i.fa.fa-share-alt"), " "]), " ",

            m('div.dz-success-mark',
                m('span.glyphicon.glyphicon-ok-circle')
            ),
            m('div.dz-error-mark',
                m('span.glyphicon.glyphicon-remove-circle')
            )
        );

        $('#shareWindowDropzone').dropzone({
            url: 'placeholder',
            previewTemplate: $osf.mithrilToStr(template)
        });
        // cache the selector to avoid duplicate selector warning
        var $chevron = $('#glyphchevron');

        $('#ShareButton').click(function () {
                document.getElementById("ShareButton").style.cursor = "pointer";
                $('#shareWindowDropzone').stop().slideToggle();
                $('#shareWindowDropzone').css('display', 'inline-block');
                $chevron.toggleClass('glyphicon glyphicon-chevron-down');
                $chevron.toggleClass('glyphicon glyphicon-chevron-up');
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
            m('div.p-v-xs.drop-zone-format.drop-zone-invis .pointer .panel #shareWindowDropzone',
                m('button.close[aria-label="Close"]', {
                        onclick: function () {
                            var $chevron = $('#glyphchevron');
                            $('#shareWindowDropzone').hide();
                            $('div.dz-preview').remove();
                            $chevron.toggleClass('glyphicon glyphicon-chevron-up');
                            $chevron.toggleClass('glyphicon glyphicon-chevron-down');
                            $('.drop-zone-format').css({'padding-bottom': '175px'});
                        }
                    }, m('.drop-zone-close', '×')
                ),
                m('h1.dz-p.text-center #shareWindowDropzone', 'Drop files to upload',
                    m('h5', 'Click the box to upload files. Files are automatically uploaded to your ',
                        m('a', {
                            href: '/share_window/', onclick: function (e) {
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

module.exports = ShareWindowDropzone;
