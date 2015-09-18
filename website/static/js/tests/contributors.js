/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var faker = require('faker');

var utils = require('./utils');
var addContributors = require('../contribAdder.js');

describe('addContributors', () => {
   describe('viewModel', () => {

       var contributorURLs = {
           contributors: faker.internet.ip()
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
       ]

       before(() => {
           {}
       });
    });
});


