'use strict';

var clipboard = require('js/clipboard');
var m = require('mithril');

function shareButton(link){
    var cb = function(elem) {
        clipboard.makeClipboardClient(elem);
    };

    return m('div.dz-share',
        m('i.fa.fa-share-alt.copy[data-clipboard-text="'+link+'"][type="button"]', {config: cb, style : {'background-color' : 'inherit'}})
    );

}

function dropzonePreviewTemplate(){
    return [
        m('div.dz-preview.dz-processing.dz-file-preview',
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