var m = require('mithril');
var $osf = require('js/osfHelpers');
var waterbutler =  require('js/waterbutler');

require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');

var Dropzone = require('dropzone');

// Don't show dropped content if user drags outside dropzone
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };


var xhrconfig = function(xhr) {
    xhr.withCredentials = true;

};

var ShareWindowDropzone = {

  controller: function() {

    Dropzone.options.shareWindowDropzone = {
            clickable: '#shareWindowDropzone',

            accept: function(file, done) {
                this.options.url = waterbutler.buildUploadUrl(false,'osfstorage',window.contextVars['currentUser']['id'], file,{});
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
                               previewTemplate: '<div class="text-center dz-filename"><span data-dz-name></span> has been uploaded to your Share Window</div>'
                               });

  },
  view: function(ctrl, args) {
          return m('div.p-v-xl.text-center .pointer .panel #shareWindowDropzone',
            m('p',
            m('h1',  'Drag and drop files here'), 'Having trouble? Click anywhere in this box to manually upload a file.'),
            m('a',  {href: "share_window"}, "Share"));
  }
};

module.exports = ShareWindowDropzone;
