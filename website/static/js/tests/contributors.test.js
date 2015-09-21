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
    contributors: [API_BASE, 'get_contributors', ''].join('/')
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
       var endpoints = [
           {url: URLs.contributors, response: getContributorsResult}
       ];
       var server;
       before(() => {
           server = utils.createServer(sinon, endpoints)
       });
       after(() => {
           server.restore();
       });

       it('urls are correct', () => {
           assert.equal(URLs.contributors, '/api/v1/project/12345/get_contributors/');
       });


       describe('ViewModel', () => {
           var vm;
           var hardReset = () => {
               vm = new addContributors('Fake title', '12345', 'parent', 'Parent title');
           };
           before(hardReset);

           describe('getContributors', () => {
               it('vm is what it says', () => {
                   assert.instanceOf(vm, addContributors);
               });

               //var alreadyContributors = vm.getContributors;
               var shouldBe = ['a1234', 'b1234', 'c1234'];

               it('should be a list of ids', () => {
                   vm.viewModel.getContributors();
                   assert.equal(vm.viewModel.contributors(), shouldBe);
               });
           });
       });

       describe('addAllVisible', () => {
           //addContributors.ContribAdder.addAllVisible()
       });


    });
});


