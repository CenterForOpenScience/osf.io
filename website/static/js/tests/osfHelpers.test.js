/*global describe, it, expect, example, beforeEach, mocha, sinon*/
'use strict';

var assert = require('chai').assert;
var $ = require('jquery');

var $osf = require('../osfHelpers.js');

describe('growl', function() {
    it('calls $.growl with correct arguments', function() {
        var spy = new sinon.spy($, 'growl');
        $osf.growl('The one', 'the only', 'danger');
        sinon.assert.calledOnce(spy);

        sinon.assert.calledWith(spy,
            {title: '<strong>The one<strong><br />', message: 'the only'});
    });
});
