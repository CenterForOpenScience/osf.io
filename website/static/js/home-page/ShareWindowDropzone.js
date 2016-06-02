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
    var shareWindowId;
    var url = $osf.apiV2Url('users/me/nodes/', { query : { 'filter[category]' : 'share window'}});
    var promise = m.request({method: 'GET', url : url, config : xhrconfig, background: true});
    promise.then(function(result) {
        shareWindowId = result.data[0].id;
    });

    Dropzone.options.shareWindowDropzone = {
            clickable: '#shareWindowDropzone',

            accept: function(file, done) {
                this.options.url = waterbutler.buildUploadUrl(false,'osfstorage',shareWindowId, file,{});
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
<<<<<<< HEAD
          return m('h1.p-v-xl.text-center .panel #shareWindowDropzone',  'Drag and drop files to upload them')
=======
              return m('.node-styling', m('.row', m('div',
                  [
                      m('.m-v-xl', m('#shareWindowDropzone', m('h1.text-center', 'Drag and drop files to upload'),
/*
                          m('p.text-center.f-w-lg', m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                event.preventDefault();
                                var input = $(document.createElement('input'));
                                input.attr("type", "file");
                                input.trigger('click');
                            },
                        }, 'Manual Upload'))))
*/
/*
                          m('p.text-center.f-w-lg', ['Having trouble? Use the ', m('a', {
                              href: '', onclick: function (event) {
                                  event.preventDefault();
                                  var input = $(document.createElement('input'));
                                  input.attr("type", "file");
                                  input.trigger('click');
                                  return false;
                                  //Fangorn.ButtonEvents._uploadEvent.call(tb, event, item);
                          }
                          }, 'manual uploader'), ' instead. '])))
                      */

                      m('p.text-center.f-w-lg', ['Having trouble? Click anywhere in this box to manually upload a file.'])))
                  ]
              )));
>>>>>>> f1bf633895e3e49ba54ade7c5d319fd24f48e468
  }
};

module.exports = ShareWindowDropzone;
