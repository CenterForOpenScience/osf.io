/**
* Mithril components for social sharing.
*/
'use strict';
var $ = require('jquery');
var m = require('mithril');

var utils = require('js/components/utils');
var required = utils.required;

var ShareButtons = {
    openLinkInPopup: function(href) {
        window.open(href, '', 'menubar=no,toolbar=no,resizable=yes,scrollbars=yes,width=600,height=400');
        return false;
    },
    view: function(ctrl, options) {
        var file_name = encodeURIComponent(required(options, 'file_name'));
        var share_url = encodeURIComponent(required(options, 'share_url'));
        var twitterHref = 'https://twitter.com/intent/tweet?url=' + share_url + '&text=' + file_name + '&via=OSFramework';
        var facebookHref = 'https://www.facebook.com/sharer/sharer.php?u=' + share_url;
        var linkedinHref = 'https://www.linkedin.com/cws/share?url=' + share_url + '&title=' + file_name;
        var emailHref = 'mailto:?subject=' + file_name + '&body=' + share_url;
        return m('div.share-buttons', {}, [
            m('a', {href: twitterHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, twitterHref)},
                m('i.fa.fa-twitter-square[aria-hidden=true]')),
            m('a', {href: facebookHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, facebookHref)},
                m('i.fa.fa-facebook-square[aria-hidden=true]')),
            m('a', {href: linkedinHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, linkedinHref)},
                m('i.fa.fa-linkedin-square[aria-hidden=true]')),
            m('a', {href: emailHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, emailHref)},
                m('i.fa.fa-envelope-square[aria-hidden=true]')),
        ]);
    }
};

var ShareDropdown = {
    view: function(ctrl, options) {
        return [
            m('a.btn.btn-default[data-toggle=dropdown]', 'Share'),
            m('ul.dropdown-menu.pull-right[role=menu]#shareDropdownMenu', {}, [
                m('li', {}, [
                    m.component(ShareButtons, {file_name: options.file_name, share_url: options.share_url})
                ])
            ])
        ];
    }
};

module.exports = {
    ShareButtons: ShareButtons,
    ShareDropdown: ShareDropdown,
};
