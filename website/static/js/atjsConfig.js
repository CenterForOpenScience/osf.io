/**
 * At.js config.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');

require('Caret.js');
require('At.js');

// preventing unexpected contenteditable behavior

// prevent pasting HTML
var onPaste = function(e) {
    e.preventDefault();
    var pasteText = e.originalEvent.clipboardData.getData('text/plain');
    document.execCommand('insertHTML', false, pasteText);
};

// prevent bold, italic, underline
var preventKeyboardShortcuts = function(e) {
    var k = e.keyCode;
    var c = e.ctrlKey || e.metaKey;

    // bold, italic, underline
    if ((k === 66 && c) || (k === 73 && c) || (k === 85 && c)){
        e.preventDefault();
    } else {
        return;
    }

};

// remove <br> if no text
var onlyElementBr = function() {
    if (this.innerText.trim() === '') {
        this.innerHTML = '';
    }
};

// ensure <br> is the lastChild of contenteditable so return works on first enter
var lastElementBr = function() {
    if (!this.lastChild || this.lastChild.nodeName.toLowerCase() !== 'br') {
        this.appendChild(document.createElement('br'));
    }
};

// ensure that return inserts a <br> in all browsers
var onReturn = function (e) {
    var docExec = false;
    var range;

    // Gecko
    try {
        docExec = document.execCommand('insertBrOnReturn', false, true);
    }
    catch (error) {
        // IE throws an error if it does not recognize the command...
    }

    if (docExec) {
        return true;
    }
    // Standard
    else if (window.getSelection) {
        e.preventDefault();

        var selection = window.getSelection(),
            br = document.createElement('br');
        range = selection.getRangeAt(0);

        range.deleteContents();
        range.insertNode(br);
        range.setStartAfter(br);
        range.setEndAfter(br);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);

        return false;
    }
    // IE (http://wadmiraal.net/lore/2012/06/14/contenteditable-ie-hack-the-new-line/)
    else if ($.browser.msie) {
        e.preventDefault();

        range = document.selection.createRange();

        range.pasteHTML('<BR>');

        // Move the caret after the BR
        range.moveStart('character', 1);

        return false;
    }
    return true;
};

// At.js
var callbacks = {
    beforeInsert: function(value, $li) {
        var data = $li.data('item-data');
        var model = ko.dataFor(this.$inputor[0]);
        this.query.el.attr('data-atwho-guid', '' + data.id);
        return value;
    },
    highlighter: function(li, query) {
    /* Override upstream to support names with spaces */
        var regexp;
        if (!query) {
            return li;
        }
        regexp = new RegExp('>\\s*([\\w\\s]*?)(' + query.replace('+', '\\+') +
            ')([\\w\\s]*)\\s*<', 'ig');
        return li.replace(regexp, function(str, $1, $2, $3) {
            return '> ' + $1 + '<strong>' + $2 + '</strong>' + $3 + ' <';
        });
    },
    matcher: function(flag, subtext, should_startWithSpace, acceptSpaceBar) {
    /* Override upstream to support names with spaces */
        acceptSpaceBar = true;
        var _a, _y, match, regexp, space;
        flag = flag.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, '\\$&');
        if (should_startWithSpace) {
            flag = '(?:^|\\s)' + flag;
        }
        _a = decodeURI('%C3%80');
        _y = decodeURI('%C3%BF');
        space = acceptSpaceBar ? '\ ' : '';
        regexp = new RegExp(flag + '([A-Za-z' + _a + '-' + _y + '0-9_' + space +
            '\'\.\+\-]*)$|' + flag + '([^\\x00-\\xff]*)$', 'gi');
        match = regexp.exec(subtext.replace(/\s/g, ' '));
        if (match) {
            return match[2] || match[1];
        } else {
            return null;
        }
    }
};

var headerTemplate = '<div class="atwho-header">Contributors<small>&nbsp;↑&nbsp;↓&nbsp;</small></div>';
var displayTemplate = '<li>${fullName}</li>';

var atConfig = {
    at: '@',
    headerTpl: headerTemplate,
    insertTpl: '@${fullName}',
    displayTpl: displayTemplate,
    searchKey: 'fullName',
    limit: 6,
    callbacks: callbacks
};

var plusConfig = $.extend({}, atConfig, {
    at: '+',
    displayTemplate: '+${fullName}'
});

module.exports = {
    atConfig: atConfig,
    plusConfig: plusConfig,
    onPaste: onPaste,
    lastElementBr: lastElementBr,
    onlyElementBr: onlyElementBr,
    onReturn: onReturn,
    preventKeyboardShortcuts: preventKeyboardShortcuts
};
