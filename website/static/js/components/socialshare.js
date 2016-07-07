/**
* Mithril components for social sharing.
*/
'use strict';
var $ = require('jquery');
var m = require('mithril');

var utils = require('js/components/utils');
var required = utils.required;

require('css/pages/share-buttons.css');

var ShareButtons = {
    openLinkInPopup: function(href) {
        window.open(href, '', 'menubar=no,toolbar=no,resizable=yes,scrollbars=yes,width=600,height=400');
        return false;
    },
    view: function(ctrl, options) {
        var title = encodeURIComponent(required(options, 'title'));
        var url = encodeURIComponent(required(options, 'url'));
        var twitterHref = 'https://twitter.com/intent/tweet?url=' + url + '&text=' + title + '&via=OSFramework';
        var facebookHref = 'https://www.facebook.com/sharer/sharer.php?u=' + url;
        var linkedinHref = 'https://www.linkedin.com/cws/share?url=' + url + '&title=' + title;
        var emailHref = 'mailto:?subject=' + title + '&body=' + url;
        return m('div.share-buttons', {}, [
            m('a', {href: twitterHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, twitterHref)},
                m('i.fa.fa-twitter[aria-hidden=true]')),
            m('a', {href: facebookHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, facebookHref)},
                m('i.fa.fa-facebook[aria-hidden=true]')),
            m('a', {href: linkedinHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, linkedinHref)},
                m('i.fa.fa-linkedin[aria-hidden=true]')),
            m('a', {href: emailHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, emailHref)},
                m('i.fa.fa-envelope[aria-hidden=true]')),
        ]);
    }
};

var ShareDropdown = {
    view: function(ctrl, options) {
        return [
            m('a.btn.btn-default[data-toggle=dropdown]', 'Share'),
            m('ul.dropdown-menu.pull-right[role=menu]', {}, [
                m('li', {}, [
                    m.component(ShareButtons, {title: options.title, url: options.url})
                ])
            ])
        ];
    }
};

module.exports = {
    ShareButtons: ShareButtons,
    ShareDropdown: ShareDropdown,
};
