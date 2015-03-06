/*global describe, it, expect, example, beforeEach, afterEach, mocha, sinon*/
'use strict';

var assert = require('chai').assert;
var $ = require('jquery');

var $osf = require('../osfHelpers.js');

describe('growl', () => {
    it('calls $.growl with correct arguments', () => {
        var spy = new sinon.spy($, 'growl');
        $osf.growl('The one', 'the only', 'danger');
        sinon.assert.calledOnce(spy);

        sinon.assert.calledWith(spy,
            {title: '<strong>The one<strong><br />', message: 'the only'});
    });
});

describe('ajax helpers', () => {
    var spy;
    beforeEach(() => {
        spy = new sinon.spy($, 'ajax');
    });
    afterEach(function() { spy.restore(); });

    describe('postJSON', () => {
        it('calls $.ajax with correct args', () => {
            var url = '/foo';
            var payload = {'bar': 42};
            $osf.postJSON(url, payload);

            sinon.assert.calledOnce(spy);
            sinon.assert.calledWith(spy, {
                url: url,
                type: 'post',
                data: JSON.stringify(payload),
                contentType: 'application/json',
                dataType: 'json'
            });
        });
    });

    describe('putJSON', () => {
        it('calls $.ajax with correct args', () => {
            var url = '/foo';
            var payload = {'bar': 42};
            $osf.putJSON(url, payload);

            sinon.assert.calledOnce(spy);
            sinon.assert.calledWith(spy, {
                url: url,
                type: 'put',
                data: JSON.stringify(payload),
                contentType: 'application/json',
                dataType: 'json'
            });
        });
    });
});

