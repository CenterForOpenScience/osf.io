var m = require('mithril');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');
var cb = require('js/clipboard');
var AddProject = require('js/addProjectPlugin');
var dzPreviewTemplate = require('js/home-page/dropzonePreviewTemplate');

require('css/dropzone-plugin.css');

var Dropzone = require('dropzone');
var Fangorn = require('js/fangorn');


// Don't show dropped content if user drags outside dropzone
window.ondragover = function (e) {e.preventDefault();};
window.ondrop = function (e) {e.preventDefault();};

var PublicFilesDropzone = {
    controller: function () {
        $('[data-toggle="tooltip"]').tooltip();
        Dropzone.options.publicFilesDropzone = {
            clickable: '#publicFilesDropzoneUploadBtn',
            autoProcessQueue: false,
            withCredentials: true,
            method: 'put',
            maxFiles: 1,
            maxFilesize: 500,
            accept: function (file, done) {
                this.options.url = waterbutler.buildUploadUrl(false, 'osfstorage', window.contextVars.publicFilesId, file, {});

                if (this.files.length <= this.options.maxFiles) {
                    $('div.h2.text-center.m-t-lg').hide();
                    this.processFile(file);
                }
                else {
                    if(!$('.alert-warning').length){

                        $osf.softGrowl('This feature is for sharing files, if you would like to store a many files for ' +
                        'a collaborative work or large presentation consider creating a project, this will give you access' +
                        ' to a large array of features and services.', 'warning', 30000);
                    }
                    $('#createNewProjectBtn' ).effect('highlight', {}, 3000);
                    this.removeFile(file);
                }
            },
            sending: function (file, xhr) {
                this.options.url = waterbutler.buildUploadUrl(false, 'osfstorage', window.contextVars.publicFilesId, file, {});
                //Hack to remove webkitheaders
                var _send = xhr.send;
                xhr.send = function () {
                    _send.call(xhr, file);
                };
                $('h2.splash-text').remove();
                $(file.previewElement).find('.file-extension').addClass('_' + file.name.split('.').pop().toLowerCase());
                $('.panel-body').append(file.previewElement);
            },
            success: function (file, xhr) {
                $('div.dz-progress').remove();
                $('.logo-spin').remove();
                $('#publicFilesDropzoneUploadBtn').html('Upload another file');
                var buttonContainer = document.createElement('div');
                $(file.previewElement).find('.col-sm-7.p-xs').append(buttonContainer);
                file.previewElement.classList.add('dz-success');
                file.previewElement.classList.add('dz-preview-background-success');
                $(file.previewElement).find('.generating-share-link').effect("pulsate", { times:100 }, 300000);

                $osf.ajaxJSON(
                    'GET',
                    $osf.apiV2Url('files' + JSON.parse(file.xhr.response).path + '/',{ query : {'giveGuid': 1 }}),
                    {
                        isCors: true
                    }
                ).done(function(response) {
                    var guid = response.data.attributes.guid;
                    var link = location.protocol+ '//' + location.host + '/' + guid;
                    m.render(buttonContainer, cb.generateClipboard(link));
                    $(file.previewElement).find('.dz-filename').attr('href', guid);
                    $('.generating-share-link').remove();
                })

                this.files.pop();
                this.processQueue();
            },
            error: function (file, message) {
                $osf.softGrowl(message + ' For larger files create a project.','danger');
                $('.dz-preview').remove();
                this.files.pop();
            }
        };

        $('#publicFilesDropzone').dropzone({
            url: 'placeholder',
            previewTemplate: $osf.mithrilToStr(dzPreviewTemplate.dropzonePreviewTemplate())
        });

        $('#glyphchevron').click(function () {
                $('#publicFilesDropzone').stop().slideToggle();
                $('#glyphchevron').toggleClass('glyphicon-menu-down glyphicon-menu-up');
        });
    },
    view: function (ctrl, args) {
        function headerTemplate() {
            return [
                m('h2.col-xs-6', 'Dashboard'),
                m('m-b-lg.pull-right',
                    m('.btn-group.m-t-md.m-r-sm.f-w-xl',
                        m('a.btn.btn-primary', {href: '/public_files'}, 'My Public Files '),
                        m('button.btn.btn-primary.glyphicon.glyphicon-menu-down #glyphchevron', {style : {top : '0px'}})
                    ),
                    m.component(AddProject, {
                        buttonTemplate: m('button.btn.btn-success.btn-success-high-contrast.m-t-md.f-w-xl.pull-right[data-toggle="modal"][data-target="#addProjectFromHome"] #createNewProjectBtn',
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
                    })
                )
            ];
        }
        function publicFilesHelpModal() {
            return [
                m('button.btn.fa.fa-info.close.dz-font[aria-label="Drag-and-Drop Help"][data-toggle="modal"][data-target="#dropZoneHelpModal"]'),
                m('.modal.fade #dropZoneHelpModal',
                    m('.modal-dialog',
                        m('.modal-content',
                            m('.modal-header',
                                m('button.close[data-dismiss="modal"]', '×'),
                                m('h4.modal-title', 'Public Files Drag-and-Drop Help')),
                            m('.modal-body', m('p', 'Files uploaded here will be automatically added to your public files. Additionally: '),
                                m('ul',
                                    m('li', 'File uploads may be up to 500 MB.'),
                                    m('li', 'To upload more files, refresh the page or click ', m('span.i.fa.fa-times')),
                                    m('li', 'To show and hide your uploads, toggle the ', m('strong', 'Upload Public Files'), ' button.'),
                                    m('li', 'Click ', m('span.i.fa.fa-share-alt'), ' to copy a link for that file to your clipboard.'))
                            ),
                            m('.modal-footer', m('button.btn.btn-default[data-dismiss="modal"]', 'Close'))
                        )
                    )
                )
            ];
        }
        function publicFilesHeader() {
            return [
                m('a.btn.btn-primary.btn-success-high-contrasts.f-w-xl',
                    {href: '/public_files/'},
                 'Your Public Files')
            ];
        }
        return m('.col-xs-12', headerTemplate(),
            m('div.drop-zone-format.panel .panel-default #publicFilesDropzone', {style: {display : 'none'}},
                m('.panel-heading',
                    publicFilesHelpModal(), publicFilesHeader()
                ),
                m('.panel-body.m-lg.text-center',
                    m('h2.splash-text', 'Drop a file to upload')
                ),
                m('.panel-footer.clearfix',
                    m('.pull-left',
                        m('h5', 'Files are uploaded to your ',
                            m('a', { href: '/public_files/' },
                             'Public Files'), ' ', m('i.fa.fa-question-circle.text-muted', {
                                'data-toggle': 'tooltip',
                                'title': 'The Public Files Project allows you to easily collaborate and share your files with anybody.',
                                'data-placement': 'bottom'
                            }, '')
                        )
                    ),
                    m('.pull-right',
                        m('button.btn.btn-success.m-r-sm #publicFilesDropzoneUploadBtn', 'Choose a file'),
                        m('button.btn.btn-default', {
                            onclick: function () {
                                $('#publicFilesDropzone').hide();
                                $('div.dz-preview').remove();
                                $('#glyphchevron').toggleClass('glyphicon glyphicon-menu-up glyphicon glyphicon-menu-down');
                            }
                        }, 'Done')
                    )
                )
            )
        );
    }
};

module.exports = PublicFilesDropzone;