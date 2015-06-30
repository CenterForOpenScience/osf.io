'use strict';
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
var jedit = require('json-editor');
var Dropzone = require('dropzone');

var MetaData = require('../metadata_1.js');
var ctx = window.contextVars;
/**
    * Unblock UI and display error modal
    */

