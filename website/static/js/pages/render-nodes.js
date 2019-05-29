'use strict';

var $osf = require('js/osfHelpers');
var $ = require('jquery');
var ko = require('knockout');
var NodesDelete = require('js/nodesDelete.js');

var selector = '.render-nodes-list';
if ($(selector).length) {
    new NodesDelete.DeleteManager(selector);
}
