var m = require('mithril');
var $osf = require('js/osfHelpers');
var waterbutler =  require('js/waterbutler');
var AddProject = require('js/addProjectPlugin');


require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');
require('css/dropzone-plugin.css');

var Dropzone = require('dropzone');

// Don't show dropped content if user drags outside dropzone
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };


var xhrconfig = function(xhr) {
    xhr.withCredentials = true;

};

var ShareWindowDropzone = {

  controller: function() {
    var shareWindowId;
    var url = $osf.apiV2Url('users/me/nodes/', { query : { 'filter[category]' : 'share window'}});
    var promise = m.request({method: 'GET', url : url, config : xhrconfig, background: true});
    promise.then(function(result) {
       shareWindowId = result.data[0].id;
    });

    Dropzone.options.shareWindowDropzone = {
        clickable: '#shareWindowDropzone',
          thumbnailWidth: 80,
  thumbnailHeight: 80,
        //previewsContainer: "#dropzone-preview",

        accept: function(file, done) {
                this.options.url = waterbutler.buildUploadUrl(false,'osfstorage',shareWindowId, file,{});
            //this.on('dragend', function(event) { event.getElementById('shareWindowDropzone').style.border = 'solid #333';});
                done();
            },

            sending: function(file, xhr) {
             //Hack to remove webkitheaders
             var _send = xhr.send;
             xhr.send = function() {
                 _send.call(xhr, file);
             };
         }

    };

    $('#shareWindowDropzone').dropzone({
        withCredentials: true,
        url:'placeholder',
        method:'put',
        addRemoveLinks: true,
        uploadMultiple: true,
        border: '2px dashed #ccc',
        //previewTemplate: '<div class="text-center dz-filename"><span data-dz-name></span> has been uploaded to your Share Window </div>'
        previewTemplate: '<div class="dz-preview dz-file-preview" style="display: inline-block;width:50%"><div class="dz-details"><div class="dz-filename"><span data-dz-name></span></div>' +
        '<div class="dz-size" data-dz-size></div><img data-dz-thumbnail /></div><div class="dz-progress"><span class="dz-upload" data-dz-uploadprogress></span></div>' +
        '<div class="dz-success-mark"></div><div class="dz-error-mark"></div><div class="dz-error-message"><span data-dz-errormessage></span></div></div>'
    });


      $('#ShareButton').click(function() {
          $('#shareWindowDropzone').slideToggle();
          $('#LinkToShareFiles').slideToggle();
          $(this).toggleClass('btn-primary');
      });

  },

  view: function(ctrl, args) {
              function headerTemplate ( ){
            return [ m('h2.col-xs-7', 'Dashboard'), m('m-b-lg.col-xs-3.drop-zone-disp', m('button.btn.btn-primary.m-t-md.f-w-xl #ShareButton', {onclick: function() {

            }}, 'Upload Public Files'), m('.pull-right', m.component(AddProject, {
                buttonTemplate : m('button.btn.btn-success.btn-success-high-contrast.m-t-md.f-w-xl[data-toggle="modal"][data-target="#addProjectFromHome"]', {onclick: function() {
                    $osf.trackClick('quickSearch', 'add-project', 'open-add-project-modal');
                }}, 'Create new project'),
                modalID : 'addProjectFromHome',
                stayCallback : function _stayCallback_inPanel() {
                                document.location.reload(true);
                },
                trackingCategory: 'quickSearch',
                trackingAction: 'add-project',
                templatesFetcher: ctrl.templateNodes
            })))];
        }
          return m('.row', m('.col-xs-12', headerTemplate()), m('div.p-v-xl.text-center.drop-zone-format.drop-zone-invis .pointer .panel #shareWindowDropzone',
              m('p#shareWindowDropzone', m('h1',  'Drop files to upload'), 'Having trouble? Click anywhere in this box to manually upload a file.')),
              m('.h4.text-center.drop-zone-invis #LinkToShareFiles', 'Or go to your ', m('a', {href: '/share_window/', onclick: function() {}}, 'Public Files Project')));
  }
};

module.exports = ShareWindowDropzone;
