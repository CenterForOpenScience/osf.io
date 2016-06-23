'use strict';

var clipboard = require('js/clipboard');
var m = require('mithril');

function shareButton(link) {
    var cb = function (elem) {
        clipboard.makeClipboardClient(elem);
    };

    return m('div.input-group',

        m('span.dz-share.input-group-btn',
            m('button.btn.btn-default.btn-sm.copy[type="button"][data-clipboard-text="' + link + '"]', {config: cb},
                m('span', 'Copy Share Link')
            )
        ),
        m('input[value="' + link + '"][readonly="readonly"][style="height: 30px;color:#333333;min-width:175px;"]')
    );
}

function dropzoneResolveIcon(file) {
    return m('div.file-extension', {'class': '_' + file.name.split('.').pop().toLowerCase()});
}

function dropzonePreviewTemplate() {
    return [
            m('div.table.col-lg-12.dz-preview.p-xs',

            m('.col-sm-6.dz-center.p-xs',
                m('div.dz-filename.col-sm-9.p-xs',
                    m('span[data-dz-name]')
                ),
                m('span', ' - '),
                m('div[data-dz-size].col-sm-3.p-xs')
            ),


            m('div.col-sm-6.p-xs', m('span.p-md', 'Generating Share Link'),
                m('div.dz-progress',
                    m('span[data-dz-uploadprogress].dz-upload')
                )
            ),

            m('.dz-logo-spin',
                m('span.logo-spin.m-r-md.logo-sm')
            ),
            m('.dz-success-mark',
                m('span.fa.fa-check-circle-o.p-xs')
            ),
            m('span.button.close.pull-right.p-r-md[data-dz-remove]', '×'),


            m('.dz-error-mark.col-sm-1',
                m('span.glyphicon.glyphicon-remove-circle')
            )
        )
    ]
        ;
}

module.exports = {
    dropzonePreviewTemplate: dropzonePreviewTemplate,
    shareButton: shareButton,
    resolveIcon: dropzoneResolveIcon,
};