'use strict';

var clipboard = require('js/clipboard');
var m = require('mithril');

function shareButton(link){
    var cb = function(elem) {
        clipboard.makeClipboardClient(elem);
    };

    return m('div.dz-share.input-group[style="width: 180px"]',
                       [
                           m('span.input-group-btn',
                               m('button.btn.btn-default.btn-sm.copy[type="button"][data-clipboard-text="'+link+ '"]', {config: cb},
                                   m('.fa.fa-clipboard')
                               )
                           ),
                           m('input[value="'+link+'"][readonly="readonly"][style="height: 30px;color:#333333;background-color:#ddf0e2;border: 1px solid  #acacac;"]')
                       ]
           );

}

function dropzonePreviewTemplate(){
    return [
        m('div.dz-preview.dz-processing.dz-file-preview',
            m('div.dz-details',
                m('div.dz-filename',
                    m('i.fa.fa-file-text.fileicon'),
                    m('span[data-dz-name]')
                ),
                m('span[data-dz-size].dz-size')
                //m('img[data-dz-thumbnail]')
            ),
            m('div.dz-progress.dz-progress-upload',
                m('span[data-dz-uploadprogress].dz-upload')
            ),
            m('div.dz-success-mark',
                m('span.glyphicon.glyphicon-ok-circle')
            ),
            m('div.dz-error-mark',
                m('span.glyphicon.glyphicon-remove-circle')
            ),
            m('div.dz-error-message',
                m('span[data-dz-errormessage]', 'Error: Your file could not be uploaded')
            )
        )
    ];
}

module.exports = {
    dropzonePreviewTemplate: dropzonePreviewTemplate,
    shareButton: shareButton,
};