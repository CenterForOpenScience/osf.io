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
        return m('div.share-buttons ', {
                config: function(el, isInitialized) {
                    $('div.share-buttons [data-toggle="tooltip"]').tooltip();
                }
            }, [
            m('a', {href: twitterHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, twitterHref)},
                m('i.fa.fa-twitter[aria-hidden=true]')),
            m('a', {href: facebookHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, facebookHref)},
                m('i.fa.fa-facebook[aria-hidden=true]')),
            m('a', {href: linkedinHref, target: '_blank',
                    'data-toggle': 'tooltip', 'data-placement': 'bottom',
                    'data-original-title': 'Disable adblock for full sharing functionality',
                    onclick: this.openLinkInPopup.bind(this, linkedinHref)},
                m('i.fa.fa-linkedin[aria-hidden=true]')),
            m('a', {href: emailHref, target: '_blank', onclick: this.openLinkInPopup.bind(this, emailHref)},
                m('i.fa.fa-envelope[aria-hidden=true]')),
        ]);
    }
};

var ShareButtonsPopover = {
    controller: function() {
        this.showOnClick = true;
        this.popupShowing = false;
    },
    view: function(ctrl, options) {
        var selector;
        if (options.type === 'link') {
            selector = 'a#sharePopoverBtn[text=Share]';
        } else {
            selector = 'a#sharePopoverBtn.btn.btn-default.glyphicon.glyphicon-share';
        }
        return [
            m(selector + '[href=#][data-toggle=popover]', {
                onmousedown: function() {
                    ctrl.showOnClick = !ctrl.popupShowing;
                },
                onclick: function() {
                    if (ctrl.showOnClick && !ctrl.popupShowing) {
                        $('#sharePopoverBtn').focus();
                    } else if (!ctrl.showOnClick && ctrl.popupShowing){
                        $('#sharePopoverBtn').blur();
                    }
                },
                onfocus: function() {
                    $('#sharePopoverBtn').popover('show');
                    m.render(document.getElementById('shareButtonsPopoverContent'),
                             ShareButtons.view(ctrl, {title: options.title, url: options.url}));
                    ctrl.popupShowing = true;
                },
                onblur: function() {
                    $('#sharePopoverBtn').popover('hide');
                    ctrl.popupShowing = false;
                },
                config: function(el, isInitialized) {
                    if (!isInitialized) {
                        $('#sharePopoverBtn').popover({
                            html: true,
                            container: 'body',
                            placement: 'bottom',
                            content: '<div id="shareButtonsPopoverContent" class="shareButtonsPopoverContent"></div>',
                            trigger: 'manual'
                        });
                    }
                }
            }),
        ];
    },
};

module.exports = {
    ShareButtons: ShareButtons,
    ShareButtonsPopover: ShareButtonsPopover,
};
