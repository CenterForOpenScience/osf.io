/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var moment = require('moment');
var Raven = require('raven-js');

var $osf = require('../osfHelpers');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('osfHelpers', () => {
    describe('growl', () => {
        it('calls $.growl with correct arguments', () => {
            var stub = new sinon.stub($, 'growl');
            $osf.growl('The one', 'the only', 'danger');
            assert.calledOnce(stub);

            assert.calledWith(stub,
                {title: '<strong>The one<strong><br />', message: 'the only'});
            stub.restore();
        });
    });

    describe('handleJSONError', () => {
        var response = {
            message_short: 'Oh no!', 
            message_long: 'Something went wrong'
        };
        it('uses the response body if available', () => {
            var stub = new sinon.stub($osf, 'growl');
            $osf.handleJSONError(response);
            assert.called(stub);
            assert.calledWith(stub,
                              response.message_short,
                              response.message_long);
            stub.restore();
        });

        it('logs error with Raven', () => {
            var growlStub = new sinon.stub($osf, 'growl');
            var stub = new sinon.stub(Raven, 'captureMessage');
            $osf.handleJSONError(response);
            assert.called(stub);
            stub.restore();
            growlStub.restore();
        });
    });

    describe('block', () => {
        var stub;
        beforeEach(() => {
            stub = new sinon.stub($, 'blockUI');
        });
        afterEach(() => {
            $.blockUI.restore();
        });

        it('calls $.blockUI with correct arguments', () => {
            $osf.block();
            assert.calledOnce(stub);
            assert.calledWith(stub, {
                css: {
                    border: 'none',
                    padding: '15px',
                    backgroundColor: '#000',
                    '-webkit-border-radius': '10px',
                    '-moz-border-radius': '10px',
                    opacity: 0.5,
                    color: '#fff'
                },
                message: 'Please wait'
            });
        });
        it('calls $.blockUI with the passed message if provided', () => {
            var msg = 'Some custom message';
            $osf.block(msg);
            assert.calledOnce(stub);
            assert.calledWith(stub, {
                css: {
                    border: 'none',
                    padding: '15px',
                    backgroundColor: '#000',
                    '-webkit-border-radius': '10px',
                    '-moz-border-radius': '10px',
                    opacity: 0.5,
                    color: '#fff'
                },
                message: msg
            });
        });
    });

    describe('unblock', () => {
        it('calls unblockUI', () => {
            var stub = new sinon.stub($, 'unblockUI');
            $osf.unblock();
            assert.calledOnce(stub);
        });
    });

    describe('mapByProperty', () => {
        it('returns the given property for every item in a list of objects', () => {
            var fixture = [{foo: 42}, {foo: 24}, {foo: 424, bar:242}, {bar: 2424}];
            var ret = $osf.mapByProperty(fixture, 'foo');
            assert.deepEqual(ret, [42, 24, 424]);
        });
    });

    describe('isEmail', () => {
        it('returns true for valid emails', () => {
            var emails = [
                'niceandsimple@example.com',
                'NiCeAnDsImPlE@eXaMpLe.CoM',
                'very.common@example.com',
                'a.little.lengthy.but.fine@a.iana-servers.net',
                'disposable.style.email.with+symbol@example.com',
                '"very.unusual.@.unusual.com"@example.com',
                "!#$%&'*+-/=?^_`{}|~@example.org", // jshint ignore: line
            ];
            emails.forEach((email) => {
                assert.isTrue($osf.isEmail(email), email + ' not recognized as a valid email');
            });
        });

        it('returns false for invalid emails', () => {
            var invalids = [
                'a"b(c)d,e:f;g<h>i[j\\k]l@example.com',
                'just"not"right@example.com',
                'this is"not\allowed@example.com',
                'this\\ still\\"not\\\\allowed@example.com',
                '"very.(),:;<>[]\".VERY.\"very@\\ \"very\".unusual"@strange.example.com',
                'user@example',
                '@nouser.com',
                'example.com',
                'user',
                '',
                null,
                undefined
            ];
            invalids.forEach((invalid) => {
                assert.isFalse($osf.isEmail(invalid), invalid + ' not recognized as a invalid email');
            });
        });
    });

    describe('ajax helpers', () => {
        var stub, xhr;
        beforeEach(() => {
            stub = new sinon.stub($, 'ajax');
        });
        afterEach(function() {
            stub.restore();
        });

        describe('postJSON', () => {
            it('calls $.ajax with correct args', () => {
                var url = '/foo';
                var payload = {'bar': 42};
                $osf.postJSON(url, payload);

                assert.calledOnce(stub);
                assert.calledWith(stub, {
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

                assert.calledOnce(stub);
                assert.calledWith(stub, {
                    url: url,
                    type: 'put',
                    data: JSON.stringify(payload),
                    contentType: 'application/json',
                    dataType: 'json'
                });
            });
        });
    });

    describe('urlParams', () => {
        it('should parse query params', () => {
            assert.deepEqual($osf.urlParams('?foo=bar'), {foo: 'bar'});
            assert.deepEqual($osf.urlParams('?foo=bar'), {foo: 'bar'});
            assert.deepEqual($osf.urlParams('?foo=bar&baz=42'), {foo: 'bar', baz: '42'});
        });
    });

    describe('htmlEscape', () => {
        it('should escape html entities', () => {
            assert.equal($osf.htmlEscape('safe'), 'safe');
            assert.equal($osf.htmlEscape('<b>'), '&lt;b&gt;');
            assert.equal($osf.htmlEscape('<script>alert("lol")</script>'), '&lt;script&gt;alert("lol")&lt;/script&gt;');
        });
    });

    describe('FormattableDate', () => {
        it('should have local and utc time', () => {
            var date = new Date();
            var fd = new $osf.FormattableDate(date);
            var expectedLocal = moment(date).format('YYYY-MM-DD hh:mm A');
            assert.equal(fd.local, expectedLocal);
            var expectedUTC = moment.utc(date).format('YYYY-MM-DD HH:mm UTC');
            assert.equal(fd.utc, expectedUTC);
        });
    });
});
