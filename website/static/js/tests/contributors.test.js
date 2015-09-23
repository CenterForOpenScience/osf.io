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
    editableChildren: [API_BASE, 'get_editable_children', ''].join('/'),
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
           console.log(server);
           console.log('Create server.');
       });
       after(() => {
           server.restore();
           console.log('server restored');
       });

       describe('ViewModel', () => {
           var vm;
           var hardReset = () => {
               var addContribs = new addContributors('nothing', 'Fake title', '12345', 'parent', 'Parent title');
               vm = addContribs.viewModel;
           };
           before(() => {
               hardReset();
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

           describe('getEditableChildren', () => {
               var shouldBe = [
                   {
                       id: '23456',
                       indent: 0,
                       margin: '25px'
                   },
                   {
                       id: '23457',
                       indent: 1,
                       margin: '50px'
                   },
                   {
                       id: '23458',
                       indent: 2,
                       margin: '75px'
                   }
               ];

               it('should be a list of indented nodes (25px offset)', () => {
                   vm.getEditableChildren()
                       .always(() => {
                           assert.equal(vm.nodes(), shouldBe);
                       });
               });
           });

           describe('fetchResults', () => {
               it('should be a list of users', () => {
                   var added = ['a1234'];
                   vm.contributors(added);
                   vm.query('*');
                   vm.fetchResults()
                       .always(() => {
                           console.log(vm.results());
                       });
               });
           });
       });

       describe('addAllVisible', () => {
           //addContributors.ContribAdder.addAllVisible()
       });


    });
});


