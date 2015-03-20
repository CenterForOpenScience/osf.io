/**
 * Created by bryan on 3/20/15.
 */
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var comment = require('../comment');

sinon.assert.expose(assert, {prefix: ''});

describe('comment', () => {
    describe('ViewModels', () = > {

        describe('CommentModel', () = > {
            var vm;

            beforeEach(() = > {
                vm = new comment.ViewModel();
            });

            it('comment good', (done) = > {
                assert.isTrue(true);
            });
        });
    });
});