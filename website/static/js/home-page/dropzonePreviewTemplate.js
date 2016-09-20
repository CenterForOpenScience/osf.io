'use strict';

var m = require('mithril');
var $osf = require('js/osfHelpers');
var $ = require('jquery');

var cb = require('js/clipboard');

function dropzonePreviewTemplate() {
    return [
            m('div.table.col-lg-12.dz-preview.p-xs',
                m('.col-sm-5.dz-center.p-xs',
                    m('.file-extension'),
                    m('.p-xs',
                        m('a[data-dz-name].dz-filename', {href : '/public_files'})
                    ),
                    m('span', ' - '),
                    m('div[data-dz-size].p-xs')
                ),
                m('div.col-sm-7.p-xs.text-center',
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
                m('.dz-error-mark.col-sm-1',
                    m('span.glyphicon.glyphicon-remove-circle')
                )
            )
    ];
}

function generateGUIDButton(file,container) {

    return m('button.btn.pull-right', {onclick : function(){
        $(this).hide();
        var loadingLabel = document.createElement('span');
        loadingLabel.innerHTML = 'Generating Share Link';
        $(container).append(loadingLabel);
        $(loadingLabel).effect('pulsate', { times:100 }, 300000);

        $osf.ajaxJSON(
            'GET',
            $osf.apiV2Url('files' + JSON.parse(file.xhr.response).path + '/',{ query : {'create_guid': 1 }}),
            {
                isCors: true
            }
        ).done(function(response) {
            var guid = response.data.attributes.guid;
            var link = location.protocol+ '//' + location.host + '/' + guid;
            m.render(container, cb.generateClipboard(link));
            $(file.previewElement).find('.dz-filename').attr('href', guid);
            $(loadingLabel).remove();

        });
        }
        }, 'Generate Share Link');


}

module.exports = {
    dropzonePreviewTemplate: dropzonePreviewTemplate,
    generateGUIDButton: generateGUIDButton,
};