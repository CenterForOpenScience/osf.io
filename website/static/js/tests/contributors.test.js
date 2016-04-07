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

var API_BASE = '/api/v1/project/12345';
var URLs = {
    contributors: [API_BASE, 'get_contributors', ''].join('/'),
    fetchUsers: '/api/v1/user/search'
};

describe('addContributors', () => {
   describe('viewModel', () => {
       var getContributorsResult = {
           contributors: [
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
       ]};
       var getEditableChildrenResults = [
           {
               id: '23456',
               indent: 0
           },
           {
               id: '23457',
               indent: 1
           },
           {
               id: '23458',
               indent: 2
           }
       ];
       var fetchResults = {
           page: 0,
           pages: 1,
           total: 3,
           users: [
               {
                   name: faker.name.findName(),
                   id: 'a1234',
                   n_projects_in_common: -1
               },
               {
                   name: faker.name.findName(),
                   id: 'b1234',
                   n_projects_in_common: 0
               },
               {
                   name: faker.name.findName(),
                   id: 'c1234',
                   n_projects_in_common: 2
               }
           ]
       };
       var endpoints = [
           {url: URLs.contributors, response: getContributorsResult},
           {url: URLs.editableChildren, response: getEditableChildrenResults},
           {url: URLs.fetchUsers, response: fetchResults}
       ];
       var server;
       before(() => {
           server = utils.createServer(sinon, endpoints);
       });
       after(() => {
           server.restore();
       });

       describe('ViewModel', () => {
           var vm;
           beforeEach(() => {
               sinon.stub(ko, 'applyBindings');
               var addContribs = new addContributors('nothing', 'Fake title', '12345', 'parent', 'Parent title');
               vm = addContribs.viewModel;
               ko.applyBindings.restore();
           });
           describe('getContributors', () => {
               var shouldBe = ['a1234', 'b1234', 'c1234'];

               it('should be a list of ids', () => {
                   vm.getContributors()
                       .always(() => {
                           assert.equal(vm.contributors(), shouldBe);
                       });
               });
           });

           describe('Visible', () => {
               describe('addAllVisible', () => {
                   it('should return false with no results addable', () => {
                       vm.contributors([
                           'a1234'
                       ]);
                       vm.results([
                           {
                               id: 'a1234'
                           },
                           {
                               id: 'b1234'
                           },
                           {
                               id: 'c1234'
                           }
                       ]);
                       vm.selection([
                           {
                               id: 'b1234'
                           },
                           {
                               id: 'c1234'
                           }
                       ]);
                       assert.isFalse(vm.addAllVisible());
                   });

                   it('should return true with one result addable', (done) => {
                       vm.results([
                           {
                               id: 'c1234'
                           }
                       ]);
                       vm.selection([
                           {
                               id: 'b1234'
                           }
                       ]);
                       assert.isTrue(vm.addAllVisible());
                       done();
                   });
               });

               describe('removeAllVisible', () => {
                   it('should return true with one user in selection list', () => {
                       vm.selection([
                           {
                               id: 'b1234'
                           }
                       ]);
                       assert.isTrue(vm.removeAllVisible());
                   });
                   it('should return false with no users in selection', () => {
                       vm.selection([]);
                       assert.isFalse(vm.removeAllVisible());
                   });
               });
           });
       });
   });
});
