'use strict';

var clipboard = require('js/clipboard');
var m = require('mithril');


function dropzoneResolveIcon(file) {
    return m('div.file-extension', {'class': '_' + file.name.split('.').pop().toLowerCase()});
}

function dropzonePreviewTemplate() {
    return [
            m('div.table.col-lg-12.dz-preview.p-xs',

            m('.col-sm-6.dz-center.p-xs',
                m('col-sm-6.p-xs',
                    m('a[data-dz-name].dz-filename', {href : '/public_files'})
                ),
                m('span', ' - '),
                m('div[data-dz-size].col-sm-3.p-xs')
            ),


            m('div.col-sm-6.p-xs.text-center', m('span.p-md', 'Generating Share Link...'),
                m('div.dz-progress',
                    m('span[data-dz-uploadprogress].dz-upload')
                )
            ),

            m('.dz-logo-spin',
                m('span.logo-spin.m-r-sm.logo-sm')
            ),
            m('.dz-success-mark',
                m('span.fa.fa-check-circle-o.p-xs')
            ),
            m('span.button.close.p-r-sm[data-dz-remove]', '×'),


            m('.dz-error-mark.col-sm-1',
                m('span.glyphicon.glyphicon-remove-circle')
            )
        )
    ]
        ;
}

module.exports = {
    dropzonePreviewTemplate: dropzonePreviewTemplate,
    resolveIcon: dropzoneResolveIcon,
};