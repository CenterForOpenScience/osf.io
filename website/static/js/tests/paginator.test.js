'use strict';

var $ = require('jquery');
var ko = require('knockout');

var osfHelpers = require('osfHelpers');
var Paginator = require('js/paginator');
var oop = require('js/oop');

describe('paginator', () => {

    var returnTrue = function() {
        return true;
    };

    var returnFalse = function() {
        return false;
    };

    var parentIsFolder = function(){
        return {
            data: {
                node_id: 'normalFolder'
            }
        };
    };

    var parentIsNotFolder = function(){
        return {
            data: {
                node_id: 'noParent'
            }
        };
    };
    var parent = {
        name: 'Parent',
        isAncestor: returnTrue
    };

    var child = {
        name: 'Child',
        isAncestor: returnFalse
    };