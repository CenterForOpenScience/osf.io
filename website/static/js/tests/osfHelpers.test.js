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
    describe('getAllNodeChildrenFromNodeList', () => {
         var getItem = function(parent, id){
             if (parent) {
                 return {
                     'relationships': {
                         'parent': {
                             'links': {
                                 'related': {
                                     'href': '/v2/nodes/' + parent + '/',
                                 }
                             }
                         }
                     },
                     'id': id,
                 };
             }
             else {
                 return {
                     'relationships': {},
                     'id': id,
                 };
             }
         };
         var nodeList = {};
         var a0 = getItem(null, 'a0');
         var a1 = getItem('a0', 'a1');
         var a2 = getItem('a1', 'a2');
         var a3 = getItem('a2', 'a3');
         var b = getItem('a0', 'b');
         nodeList.a0 = a0;
         nodeList.a1 = a1;
         nodeList.a2 = a2;
         nodeList.a3 = a3;
         nodeList.b = b;

         it('returns no children when there are no children', () => {
             var a3List = $osf.getAllNodeChildrenFromNodeList('a3', nodeList);
             assert.equal(a3List.a0, undefined);
             assert.equal(a3List.a1, undefined);
             assert.equal(a3List.a2, undefined);
             assert.equal(a3List.a3, undefined);
             assert.equal(a3List.b, undefined);
             var bList = $osf.getAllNodeChildrenFromNodeList('b', nodeList);
             assert.equal(bList.a0, undefined);
             assert.equal(bList.a1, undefined);
             assert.equal(bList.a2, undefined);
             assert.equal(bList.a3, undefined);
             assert.equal(bList.b, undefined);
         });

         it('returns one child when there is only one child', () => {
             var a2List = $osf.getAllNodeChildrenFromNodeList('a2', nodeList);
             assert.equal(a2List.a0, undefined);
             assert.equal(a2List.a1, undefined);
             assert.equal(a2List.a2, undefined);
             assert.equal(a2List.a3.id, 'a3');
             assert.equal(a2List.b, undefined);
         });

         it('returns two children when child has a child', () => {
             var a1List = $osf.getAllNodeChildrenFromNodeList('a1', nodeList);
             assert.equal(a1List.a0, undefined);
             assert.equal(a1List.a1, undefined);
             assert.equal(a1List.a2.id, 'a2');
             assert.equal(a1List.a3.id, 'a3');
             assert.equal(a1List.b, undefined);
         });

         it('returns all children except the root', () => {
             var a0List = $osf.getAllNodeChildrenFromNodeList('a0', nodeList);
             assert.equal(a0List.a0, undefined);
             assert.equal(a0List.a1.id, 'a1');
             assert.equal(a0List.a2.id, 'a2');
             assert.equal(a0List.a3.id, 'a3');
             assert.equal(a0List.b.id, 'b');
         });
     });

    
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
            },
            status: 400
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

    describe('handleEditableError', () => {

        var ravenStub;
        beforeEach(() => {
            ravenStub = new sinon.stub(Raven, 'captureMessage');
        });

        afterEach(() => {
            ravenStub.restore();
        });
        var response = {
            responseJSON: {
                message_short: 'Oh no!',
                message_long: 'Something went wrong'
            }
        };
        it('uses the response text if available', () => {
            assert.equal('Error: ' + response.responseJSON.message_long, $osf.handleEditableError(response));
        });

        it('logs error with Raven', () => {
            $osf.handleEditableError(response);
            assert.called(ravenStub);
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

    describe('decodeText', () => {
        it('returns properly decoded text', () => {
            var text = '&amp;';
            var ret = $osf.decodeText(text);
            assert.equal(ret, '&');
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

        describe('ajaxJSON', () => {
            it('calls $.ajax as GET request, not crossorigin by default', () => {
                var url = '/foo';
                $osf.ajaxJSON('GET', url);
                assert.calledOnce(stub);
                assert.calledWith(stub, {
                    url: url,
                    type: 'GET',
                    contentType: 'application/json',
                    dataType: 'json'
                });
            });
            it('calls $.ajax as POST request, and isCors flags sends credentials by default', () => {
                var url = '/foo';
                var payload = {'bar': 42};

                $osf.ajaxJSON('POST', url,
                    {data: payload, isCors: true}
                );
                assert.calledOnce(stub);
                assert.calledWith(stub, {
                    url: url,
                    type: 'POST',
                    data: JSON.stringify(payload),
                    contentType: 'application/json',
                    dataType: 'json',
                    crossOrigin: true,
                    xhrFields:
                        {withCredentials: true}
                });
            });
            it('calls $.ajax as crossorigin PATCH request, omitting credentials when specified', () => {
                var url = '/foo';
                var payload = {'bar': 42};

                $osf.ajaxJSON('PATCH', url,
                    {data: payload, isCors: true,
                     fields: {xhrFields: {withCredentials: false}}
                    });
                assert.calledOnce(stub);
                assert.calledWith(stub, {
                    url: url,
                    type: 'PATCH',
                    data: JSON.stringify(payload),
                    contentType: 'application/json',
                    dataType: 'json',
                    crossOrigin: true,
                    xhrFields:
                        {withCredentials: false}
                });
            });
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
            var year = 2014;
            var month = 11;
            var day = 15;
            var hour = 10;
            var minute = 33;
            var second = 17;
            var millisecond = 123;

            var dateString = [year, month, day].join('-');
            var dateTimeString = dateString + 'T' + [hour, minute, second].join(':') + '.' + millisecond.toString();

            var assertDateEqual = function(date, year, month, day) {
                assert.equal(date.getUTCFullYear(), year);
                assert.equal(date.getUTCMonth(), month - 1); // Javascript months count from 0
                assert.equal(date.getUTCDate(), day);
            };

            var assertDateTimeEqual = function(date, year, month, day, hour, minute, second, millisecond) {
                assert.equal(date.getUTCFullYear(), year);
                assert.equal(date.getUTCMonth(), month - 1); // Javascript months count from 0
                assert.equal(date.getUTCDate(), day);
                assert.equal(date.getUTCHours(), hour);
                assert.equal(date.getUTCMinutes(), minute);
                assert.equal(date.getUTCSeconds(), second);
                assert.equal(date.getUTCMilliseconds(), millisecond);
            };


        it('should have local and utc time', () => {
            var date = new Date();
            var fd = new $osf.FormattableDate(date);
            var expectedLocal = moment(date).format('YYYY-MM-DD hh:mm A');
            assert.equal(fd.local, expectedLocal);
            var expectedUTC = moment.utc(date).format('YYYY-MM-DD HH:mm UTC');
            assert.equal(fd.utc, expectedUTC);
        });
        it('should parse date strings', () => {
            var parsedDate = new $osf.FormattableDate(dateString).date;
            assertDateEqual(parsedDate, year, month, day);
        });
        it('should parse datetime strings', () => {
            var parsedDateTime = new $osf.FormattableDate(dateTimeString).date;
            assertDateTimeEqual(parsedDateTime, year, month, day, hour, minute, second, millisecond);
        });
        it('should allow datetimes with UTC offsets', () => {
            var parsedDateTime = null;
            var UTCOffsets = ['+00', '-00', '+00:00', '-00:00', '+0000', '-0000', 'Z'];

            UTCOffsets.forEach(function(offset) {
                parsedDateTime = new $osf.FormattableDate(dateTimeString + offset).date;
                assertDateTimeEqual(parsedDateTime, year, month, day, hour, minute, second, millisecond);
            });
        });
        it('should allow datetimes with positive offsets', () => {
            var parsedDateTime = null;
            var positiveOffset = '+02:00';

            parsedDateTime = new $osf.FormattableDate(dateTimeString + positiveOffset).date;
            assertDateTimeEqual(parsedDateTime, year, month, day, hour - 2, minute, second, millisecond);

        });
        it('should allow datetimes with negative offsets', () => {
            var parsedDateTime = null;
            var negativeOffset = '-02:00';

            parsedDateTime = new $osf.FormattableDate(dateTimeString + negativeOffset).date;
            assertDateTimeEqual(parsedDateTime, year, month, day, hour + 2, minute, second, millisecond);
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

    describe('iterObject', () => {
        var get = function(obj, key) {
            return obj[key];
        };

        it('maps an object to an array {key: KEY, value: VALUE} pairs', () => {
            var obj = {
                foo: 'bar',
                cat: 'dog'
            };
            var keys = Object.keys(obj);
            var values = keys.map(get.bind(null, obj));
            var iterable = $osf.iterObject(obj);
            for(var i = 0; i < iterable.length; i++) {
                var item = iterable[i];
                assert.include(keys, item.key);
                assert.include(values, item.value);
                assert.equal(item.value, get(obj, keys[i]));
            }
        });
    });

    describe('indexOf', () => {
        it('returns a positive integer index if it finds a matching item', () => {
            var list = [];
            for(var i = 0; i < 5; i++){
                list.push({
                    foo: 'bar' + i
                });
            }
            var idx = Math.floor(Math.random() * 5);
            var search = function(item) {
                return item.foo === 'bar' + idx;
            };
            var found = $osf.indexOf(list, search);
            assert.equal(idx, found);
        });
        it('returns -1 if no item is matched', () => {
            var list = [];
            for(var i = 0; i < 5; i++){
                list.push({
                    foo: 'bar' + i
                });
            }
            var search = function(item) {
                return item.foo === 42;
            };
            var found = $osf.indexOf(list, search);
            assert.equal(-1, found);
        });
    });

    describe('any', () => {
        it('returns true if any of the values in an array are truthy', () => {
            var TRUTHY = [true, {}, [], 42, 'foo', new Date()];
            $.each(TRUTHY, function(_, item) {
                assert.isTrue(
                    $osf.any([false, item, false])
                );
            });
        });
        it('returns false if none of the values in an array are truthy', () => {
            assert.isFalse(
                $osf.any([false, null, undefined, 0, NaN, ''])
            );
        });
        it('returns false if the array is empty', () => {
            assert.isFalse(
                $osf.any([])
            );
        });
    });

    describe('getDomain', () => {
        it('uses http for localhost domains', () => {
            var location = {hostname: 'localhost', port: '5000'};
            assert.equal($osf.getDomain(location), 'http://localhost:5000');
        });

        it('uses https for non-localhost domains', () => {
            var location = {hostname: 'osf.test', port: '5000'};
            assert.equal($osf.getDomain(location), 'https://osf.test:5000');
        });

        it('uses window.location if object not passed', () => {
            assert.include($osf.getDomain(), 'http');
        });
    });

    describe('logTextParser', () => {
        describe('Convert to relative urls', () => {
            var testData = {
                externalAbsoluteUrlHttp: 'http://externaldomin.com/some/external/path/',
                externalAbsoluteUrlHttpWithSearch: 'http://externaldomin.com/some/external/path/?q=random',
                externalAbsoluteUrlHttpWithHash: 'http://externaldomin.com/some/external/path/#hashhash',
                externalAbsoluteUrlHttpWithSearchAndHash: 'http://externaldomin.com/some/external/path/?q=random#hashhash',
                externalAbsoluteUrlProtocol: 'https://externaldomin.com/some/external/path/?q=random#hashhash',
                externalAbsoluteUrlProtocolWithSearch: 'https://externaldomin.com/some/external/path/?q=random#hashhash',
                externalAbsoluteUrlProtocolWithHash: 'https://externaldomin.com/some/external/path/?q=random#hashhash',
                externalAbsoluteUrlProtocolWithSearchAndHash: 'https://externaldomin.com/some/external/path/?q=random#hashhash',
                internalAbsoluteUrlHttp: window.location.origin + '/mst3k/files/',
                internalAbsoluteUrlHttpWithSearch: window.location.origin + '/mst3k/files/?q=random',
                internalAbsoluteUrlHttpWithHash: window.location.origin + '/mst3k/files/#hashhash',
                internalAbsoluteUrlHttpWithSearchAndHash: window.location.origin + '/mst3k/files/?q=random#hashhash',
                internalAbsoluteUrlProtocol: 'https://rdm.nii.ac.jp/mst3k/files/',
                internalAbsoluteUrlProtocolWithSearch: 'https://rdm.nii.ac.jp/mst3k/files/?q=random',
                internalAbsoluteUrlProtocolWithHash: 'https://rdm.nii.ac.jp/mst3k/files/#hashhash',
                internalAbsoluteUrlProtocolWithSearchAndHash: 'https://rdm.nii.ac.jp/mst3k/files/?q=random#hashhash',
                internalRelativeUrl: '/mst3k/files/',
                internalRelativeUrlWithSearch: '/mst3k/files/?q=random',
                internalRelativeUrlWithHash: '/mst3k/files/#hashhash',
                internalRelativeUrlWithSearchAndHash: '/mst3k/files/?q=random#hashhash'
            };
    
            describe('Does not affect external URLs with Http as protocol', () => {
                it('URLs that does not contain search or hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.externalAbsoluteUrlHttp, window),
                        testData.externalAbsoluteUrlHttp
                    );
                });
    
                it('URLs that contain search, not hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.externalAbsoluteUrlHttpWithSearch, window),
                        testData.externalAbsoluteUrlHttpWithSearch
                    );
                });
    
                it('URLs that contain hash, not search', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.externalAbsoluteUrlHttpWithHash, window),
                        testData.externalAbsoluteUrlHttpWithHash
                    );
                });
    
                it('URLs that contain both search and hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.externalAbsoluteUrlHttpWithSearchAndHash, window),
                        testData.externalAbsoluteUrlHttpWithSearchAndHash
                    );
                });
            });
    
            describe('Does not affect external URLs with other protocol', () => {
                it('URLs that does not contain search or hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.externalAbsoluteUrlProtocol, window),
                        testData.externalAbsoluteUrlProtocol
                    );
                });
    
                it('URLs that contain search, not hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.externalAbsoluteUrlProtocolWithSearch, window),
                        testData.externalAbsoluteUrlProtocolWithSearch
                    );
                });
    
                it('URLs that contain hash, not search', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.externalAbsoluteUrlProtocolWithHash, window),
                        testData.externalAbsoluteUrlProtocolWithHash
                    );
                });
    
                it('URLs that contain both search and hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.externalAbsoluteUrlProtocolWithSearchAndHash, window),
                        testData.externalAbsoluteUrlProtocolWithSearchAndHash
                    );
                });
            });
    
            describe('Does not affect relative URLs', () => {
                it('URLs that does not contain search or hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.internalRelativeUrl, window),
                        testData.internalRelativeUrl
                    );
                });
    
                it('URLs that contain search, not hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.internalRelativeUrlWithSearch, window),
                        testData.internalRelativeUrlWithSearch
                    );
                });
    
                it('URLs that contain hash, not search', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.internalRelativeUrlWithHash, window),
                        testData.internalRelativeUrlWithHash
                    );
                });
    
                it('URLs that contain both search and hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.internalRelativeUrlWithSearchAndHash, window),
                        testData.internalRelativeUrlWithSearchAndHash
                    );
                });
            });
    
            describe('works for internal absolute URLs with Http as protocol', () => {
                it('URLs that does not contain search or hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.internalAbsoluteUrlHttp, window),
                        testData.internalRelativeUrl
                    );
                });
    
                it('URLs that contain search, not hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.internalAbsoluteUrlHttpWithSearch, window),
                        testData.internalRelativeUrlWithSearch
                    );
                });
    
                it('URLs that contain hash, not search', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.internalAbsoluteUrlHttpWithHash, window),
                        testData.internalRelativeUrlWithHash
                    );
                });
    
                it('URLs that contain both search and hash', () => {
                    assert.equal(
                        $osf.toRelativeUrl(testData.internalAbsoluteUrlHttpWithSearchAndHash, window),
                        testData.internalRelativeUrlWithSearchAndHash
                    );
                });
            });
    
            describe('works for internal absolute URLs with different protocol', () => {
                var customWindow = {
                    location:{
                        hostname: 'osf.io',
                        protocol: 'https:'
                    }
                };
    
                (function(window){
                    it('URLs that does not contain search or hash', () => {
                        assert.equal(
                            $osf.toRelativeUrl(testData.internalAbsoluteUrlProtocol, window),
                            testData.internalRelativeUrl
                        );
                    });
    
                    it('URLs that contain search, not hash', () => {
                        assert.equal(
                            $osf.toRelativeUrl(testData.internalAbsoluteUrlProtocolWithSearch, window),
                            testData.internalRelativeUrlWithSearch
                        );
                    });
    
                    it('URLs that contain hash, not search', () => {
                        assert.equal(
                            $osf.toRelativeUrl(testData.internalAbsoluteUrlProtocolWithHash, window),
                            testData.internalRelativeUrlWithHash
                        );
                    });
    
                    it('URLs that contain both search and hash', () => {
                        assert.equal(
                            $osf.toRelativeUrl(testData.internalAbsoluteUrlProtocolWithSearchAndHash, window),
                            testData.internalRelativeUrlWithSearchAndHash
                        );
                    });
                })(customWindow);
            });
        });
    });
});
