'use strict';

var $ = require('jquery');
var faker = require('faker');

var makeFakeData = function(overrides) {
    var nodeHasAuth = faker.random.number() ? true : false;
    var userHasAuth = faker.random.number() ? true : false;
    var userIsOwner = faker.random.number() ? true : false;
    var ownerName = faker.name.findName();
    var folder = {
        name: faker.hacker.noun(),
        id: faker.finance.account(),
        path: faker.hacker.noun()
    };
    var urlPath = faker.internet.domainWord();
    var url = faker.internet.ip();
    var urls = {};
    urls[urlPath] = url;
    var data = {
        nodeHasAuth: nodeHasAuth,
        userHasAuth: userHasAuth,
        userIsOwner: userIsOwner,
        folder: folder,
        ownerName: ownerName,
        urls: urls
    };
    return $.extend({}, data, overrides);
};

module.exports = {
    makeFakeData: makeFakeData
};
