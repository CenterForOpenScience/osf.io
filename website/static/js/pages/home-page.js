/**
 * Initialization code for the home page.
 */

'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var quickSearchProject = require('js/quickProjectSearchPlugin');
var m = require('mithril');

$(document).ready(function(){
    m.mount(m.component(quickSearchProject, {}))

});