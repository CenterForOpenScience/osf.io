/**
 * Initialization code for the home page.
 */

'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var quickSearchProject = require('js/quickProjectSearchPlugin');
var newAndNoteworthy = require('js/newAndNoteworthyPlugin');
var m = require('mithril');

$(document).ready(function(){
    m.mount(document.getElementById('addQuickProjectSearchWrap'), m.component(quickSearchProject, {}));
    m.mount(document.getElementById('newAndNoteworthyWrap'), m.component(newAndNoteworthy, {}))
});