/**
* Mithril components for social sharing.
*/
'use strict';
var $ = require('jquery');
var m = require('mithril');

var utils = require('js/components/utils');
var required = utils.required;

var ShareButtons = {
    view: function(ctrl, options) {
        var file_name = encodeURIComponent(required(options, 'file_name'));
        var share_url = encodeURIComponent(required(options, 'share_url'));
        return m('div.share-buttons', {}, [
            m('a', {href: 'https://twitter.com/intent/tweet?url=' + share_url + '&text=' + file_name + '&via=OSFramework', target: '_blank'},
                m('i.fa.fa-twitter-square[aria-hidden=true]')),
            m('a', {href: 'https://www.facebook.com/sharer/sharer.php?u=' + share_url, target: '_blank'},
                m('i.fa.fa-facebook-square[aria-hidden=true]')),
            m('a', {href: 'https://www.linkedin.com/cws/share?url=' + share_url + '&title=' + file_name, target: '_blank'},
                m('i.fa.fa-linkedin-square[aria-hidden=true]')),
            m('a', {href: 'mailto:?subject=' + file_name + '&amp;body=' + share_url, target: '_blank'},
                m('i.fa.fa-envelope-square[aria-hidden=true]')),
        ])
    }
}

var ShareDropdown = {
    view: function(ctrl, options) {
        return [
            m('a.btn.btn-default[data-toggle=dropdown]', 'Share'),
            m('ul.dropdown-menu.pull-right[role=menu]#shareDropdownMenu', {}, [
                m('li', {}, [
                    m.component(ShareButtons, {file_name: options.file_name, share_url: options.share_url})
                ])
            ])
        ]
    }
}

module.exports = {
    ShareButtons: ShareButtons,
    ShareDropdown: ShareDropdown,
};
