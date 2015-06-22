/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var moment = require('moment');
var Raven = require('raven-js');
var bootbox = require('bootbox');

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


    describe('apiV2Url', () => {
        it('returns correctly formatted URLs for described inputs', () => {
            var fullUrl = $osf.apiV2Url('/nodes/abcd3/contributors/',
                {prefix: 'http://localhost:8000/v2/'});
            assert.equal(fullUrl, 'http://localhost:8000/v2/nodes/abcd3/contributors/');

            // No double slashes when apiPrefix and pathString have adjoining slashes
            fullUrl = $osf.apiV2Url('nodes/abcd3/contributors/',
                {prefix: 'http://localhost:8000/v2/'});
            assert.equal(fullUrl, 'http://localhost:8000/v2/nodes/abcd3/contributors/');

            // User is still responsible for the trailing slash. If they omit it, it doesn't appear at end of URL
            fullUrl = $osf.apiV2Url('/nodes/abcd3/contributors',
                {prefix: 'http://localhost:8000/v2/'});
            assert.notEqual(fullUrl, 'http://localhost:8000/v2/nodes/abcd3/contributors/');

            // Correctly handles- and encodes- URLs with parameters
            fullUrl = $osf.apiV2Url('/nodes/abcd3/contributors/',
                {query:
                    {'filter[fullname]': 'bob', 'page_size':10},
                prefix: 'https://staging2.osf.io/api/v2/'});
            assert.equal(fullUrl, 'https://staging2.osf.io/api/v2/nodes/abcd3/contributors/?filter%5Bfullname%5D=bob&page_size=10');

            // Given a blank string, should return the base path (domain + port + prefix) with no extra cruft at end
            fullUrl = $osf.apiV2Url('',
                {prefix: 'http://localhost:8000/v2/'});
            assert.equal(fullUrl, 'http://localhost:8000/v2/');
        });
    });


    describe('handleJSONError', () => {

        var growlStub;
        var ravenStub;
        beforeEach(() => {
            growlStub = new sinon.stub($osf, 'growl');
            ravenStub = new sinon.stub(Raven, 'captureMessage');
        });

        afterEach(() => {
            growlStub.restore();
            ravenStub.restore();
        });
        var response = {
            responseJSON: {
                message_short: 'Oh no!',
                message_long: 'Something went wrong'
            }
        };
        it('uses the response body if available', () => {
            $osf.handleJSONError(response);
            assert.called(growlStub);
            assert.calledWith(growlStub,
                              response.responseJSON.message_short,
                              response.responseJSON.message_long);
        });

        it('logs error with Raven', () => {
            $osf.handleJSONError(response);
            assert.called(growlStub);
            assert.called(ravenStub);
        });
    });

    describe('block', () => {
        it('calls $.blockUI with correct arguments', () => {
            var stub = new sinon.stub($, 'blockUI');
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

    describe('htmlDecode', () => {
        it('should decode html entities', () => {
            assert.equal($osf.htmlDecode('safe'), 'safe');
            assert.equal($osf.htmlDecode('b&gt;a&amp;'), 'b>a&');
            assert.equal($osf.htmlDecode('&lt;script&gt;alert("lol")&lt;/script&gt;'), '<script>alert("lol")</script>');
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
        it('should parse date and datetime strings', () => {
            var year = 2014;
            var month = 11;
            var day = 15;
            var hour = 10;
            var minute = 33;
            var second = 17;
            var millisecond = 123;

            var dateString = [year, month, day].join('-');
            var dateTimeString = dateString + 'T' + [hour, minute, second].join(':') + '.' + millisecond.toString();

            var parsedDate = new $osf.FormattableDate(dateString).date;
            var parsedDateTime = new $osf.FormattableDate(dateTimeString).date;

            assert.equal(parsedDate.getUTCFullYear(), year);
            assert.equal(parsedDate.getUTCMonth(), month - 1); // Javascript months count from 0
            assert.equal(parsedDate.getUTCDate(), day);
            assert.equal(parsedDate.getUTCHours(), 0);
            assert.equal(parsedDate.getUTCMinutes(), 0);
            assert.equal(parsedDate.getUTCSeconds(), 0);
            assert.equal(parsedDate.getUTCMinutes(), 0);

            assert.equal(parsedDateTime.getUTCFullYear(), year);
            assert.equal(parsedDateTime.getUTCMonth(), month - 1); // Javascript months count from 0
            assert.equal(parsedDateTime.getUTCDate(), day);
            assert.equal(parsedDateTime.getUTCHours(), hour);
            assert.equal(parsedDateTime.getUTCMinutes(), minute);
            assert.equal(parsedDateTime.getUTCSeconds(), second);
            assert.equal(parsedDateTime.getUTCMilliseconds(), millisecond);
        });
    });

    describe('confirmDangerousAction', () => {
        var bootboxStub, callbackStub;
        beforeEach(() => {
            bootboxStub = new sinon.stub(bootbox, 'dialog');
            callbackStub = new sinon.spy();
        });
        afterEach(() => {
            bootboxStub.restore();
        });
        it('should trigger bootbox', () => {
            $osf.confirmDangerousAction({callback: callbackStub});
            assert.calledOnce(bootboxStub);
        });
    });
});
