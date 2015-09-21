/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var  utils = require('tests/utils');
var $ = require('jquery');
var faker = require('faker');
var ko = require('knockout');
var $osf = require('js/osfHelpers');

var addContributors = require('js/contribAdder.js');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

TestSubclassVM = oop.extend(addContributors.ContribAdder, {
    constructor: function(title, parentId, parentTitle) {
        this.super.constructor.call(this, title, parentId, parentTitle);

    }
});

describe('addContributors', () => {
   describe('viewModel', () => {

       var contributorURLs = {
           contributors: '/api/v1/12345/get_contributors'
       };

       var contributors = [
           {
               name: faker.name.findName(),
               id: 'a1234'
           },
           {
               name: faker.name.findName(),
               id: 'b1234'
           },
           {
               name: faker.name.findName(),
               id: 'c1234'
           }
       ];
       var endpoints = [
           {url: contributorURLs.contributors, response: contributors}
       ];

       var server;
       before(() => {
           server = utils.createServer(sinon, endpoints)
       });
       after(() => {
           server.restore();
       });

       describe('ViewModel', () => {
           var vm;
           var hardReset = () => {
               vm = new TestSubclassVM('Fake title', '12345', 'Parent title');
           };
           before(hardReset);

           describe('get_contributors', () => {
               var alreadyContributors = vm.getContributors();
               var shouldBe = ['a1234', 'b1234', 'c1234'];

               it('should be a list of ids', () => {
                   assert.equal(alreadyContributors, shouldBe);
               });
           });
       });

       describe('addAllVisible', () => {
           addContributors.ContribAdder.addAllVisible()
       });


    });
});


