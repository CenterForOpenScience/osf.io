/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var LogText = require('js/logTextParser');
var faker = require('faker');

//In this case, we don't care if id's are all the same
var makeFakeContributor = function(active=true){
    return {
        name: faker.name.findName(),
        id: 'a1234',
        active: active,
        unregistered_name: faker.name.findName()
    };
};

describe('logTextParser', () => {
    describe('getContributorList', () => {
        var contributors = [];
        for (var i = 0; i<5; i++) {
            contributors.push(makeFakeContributor());
            contributors.push(makeFakeContributor(false));
        }
        it('displays all contributors if under maxShown limit', () => {
            var logText = LogText.getContributorList(contributors, 11);
            assert.equal(logText.length, 10);
            assert.equal(logText[9][1], ' ');
            assert.equal(logText[8][1], ', and ');

        });
        it('contribs equals maxShown limit', () => {
            var logText = LogText.getContributorList(contributors, 10);
            assert.equal(logText.length, 10);
            assert.equal(logText[9][1], ' ');
            assert.equal(logText[8][1], ', and ');

        });
        it('displays all contributors if only one over maxShown limit', () => {
            var logText = LogText.getContributorList(contributors, 9);
            assert.equal(logText.length, 10);
            assert.equal(logText[9][1], ' ');
            assert.equal(logText[8][1], ', and ');

        });
        it('displays only up to maxShown limit', () => {
            var logText = LogText.getContributorList(contributors, 3);
            assert.equal(logText.length, 4);
            assert.equal(logText[3][0], '7 others');
            assert.equal(logText[3][1], ' ');
            assert.equal(logText[2][1], ', and ');

        });
        it('displays no comma if only two contribs added', () => {
            var logText = LogText.getContributorList([makeFakeContributor(), makeFakeContributor()], 3);
            assert.equal(logText.length, 2);
            assert.equal(logText[1][1], ' ');
            assert.equal(logText[0][1], ' and ');

        });
    });
});
