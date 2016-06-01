var m = require('mithril');
var $osf = require('js/osfHelpers');
var waterbutler =  require('js/waterbutler');

require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');
var Dropzone = require('dropzone');

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

             accept: function(file, done) {
                this.options.url = waterbutler.buildUploadUrl(false,'osfstorage',shareWindowId, file,{});
                done();
            }
    };

    $('#shareWindowDropzone').dropzone({
                               withCredentials: true,
                               url:'placeholder',
                               method:'put',
                               previewTemplate: '<div class="text-center dz-filename"><span data-dz-name></span> is uploaded to to Share Window</div>'

                               });

  },
  view: function(ctrl, args) {
          return  m('.m-v-xs.node-styling',  m('.row', m('div',
                  [
                      m('.m-v-xl', m('#shareWindowDropzone',  m('h1.text-center',  'Dropzone'))),
                  ]
              )));
  }
};

module.exports = ShareWindowDropzone;
