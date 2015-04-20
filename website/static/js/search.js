'use strict';

require('css/search.css');

var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
require('bootstrap.growl');
var History = require('exports?History!history');

var iconmap = require('js/iconmap');
var $osf = require('js/osfHelpers');
// Enable knockout punches
ko.punches.enableAll();

// Disable IE Caching of JSON
$.ajaxSetup({
    cache: false
});

//https://stackoverflow.com/questions/7731778/jquery-get-query-string-parameters

var Category = function(name, count, display, opts) {
    var self = this;

    self.name = name;
    self.count = count;
    self.display = display;
    self.url = '';
    if (self.name !== 'total') {
        self.url = 'project/';
    }

    opts = opts || {};
    if(opts.parent) {
        self.parent = opts.parent;
        self.iconClass = iconmap.componentIcons[name];
    }    
    self.children = $.map((opts.children || []), function(c) {         
        var childName = Object.keys(c)[0];
        return new Category(childName, c[childName], opts.aliases[childName], {parent: self});
    });
};

var Tag = function(tagInfo) {
    var self = this;
    self.name = tagInfo.key;
    self.count = tagInfo.doc_count;
};

var User = function(result) {
    var self = this;
    self.category = result.category;
    self.gravatarUrl = ko.observable('');
    self.social = result.social;
    self.job_title = result.job_title;
    self.job = result.job;
    self.degree = result.degree;
    self.school = result.school;
    self.url = result.url;
    self.wikiUrl = result.url + 'wiki/';
    self.filesUrl = result.url + 'files/';
    self.user = result.user;

    $.ajax('/api/v1' + result.url).success(function(data) {
        if (typeof data.profile !== 'undefined') {
            self.gravatarUrl(data.profile.gravatar_url);
        }
    });
};

var ViewModel = function(params) {
    var self = this;
    self.params = params || {};
    self.queryUrl = self.params.url;
    self.appURL = self.params.appURL;

    self.tag = ko.observable('');
    self.tags = ko.observableArray([]);
    self.tagMaxCount = ko.observable(1);

    self.stateJustPushed = true;

    self.query = ko.observable('');
    self.type = ko.observable('');
    self.category = ko.observable({});

    self.currentPage = ko.observable(1);
    self.totalResults = ko.observable(0);
    self.results = ko.observableArray([]);
    self.searching = ko.observable(false);
    self.resultsPerPage = ko.observable(10);
    self.categories = ko.observableArray([]);
    self.searchStarted = ko.observable(false);
    self.showSearch = true;
    self.showClose = false;
    self.searchCSS = ko.observable('active');
    self.onSearchPage = true;

    // Pagination
    self.pagePrev = self.paginate.bind(self, -1);
    self.pageNext = self.paginate.bind(self, 1);

    // Maintain compatibility with hiding search bar elsewhere on the site
    self.toggleSearch = function() {};

    self.totalCount = ko.pureComputed(function() {
        if (self.categories().length === 0 || self.categories()[0] === undefined) {
            return 0;
        }

        return self.categories()[0].count;
    });

    self.totalPages = ko.pureComputed(function() {
        var resultsCount = Math.max(self.resultsPerPage(), 1); // No Divide by Zero
        var countOfPages = Math.ceil(self.totalResults() / resultsCount);
        return countOfPages;
    });

    self.nextPageExists = ko.pureComputed(function() {
        return ((self.totalPages() > 1) && (self.currentPage() < self.totalPages()));
    });

    self.prevPageExists = ko.pureComputed(function() {
        return self.totalPages() > 1 && self.currentPage() > 1;
    });

    self.currentIndex = ko.pureComputed(function() {
        return Math.max(self.resultsPerPage() * (self.currentPage() - 1), 0);
    });

    self.navLocation = ko.pureComputed(function() {
        return 'Page ' + self.currentPage() + ' of ' + self.totalPages();
    });

    self.filters = ko.pureComputed(function() {
        return self.type() ? {
            term: {
                descriptor: self.type()
            }
        } : {
            match_all: {}
        };
    });

    self.queryObject = ko.pureComputed(function() {
        return {
            query_string: {
                default_field: '_all',
                query: self.query(),
                analyze_wildcard: true,
                lenient: true
            }
        };
    });
    self.fullQuery = ko.pureComputed(function() {
        return {
            filtered: {
                query: self.queryObject(),
                filter: self.filters()
            }
        };
    });
};

ViewModel.prototype.help = function() {
    bootbox.dialog({
        title: 'Search help',
        message: '<h4>Queries</h4>' +
            '<p>Search uses the <a href="http://extensions.xwiki.org/xwiki/bin/view/Extension/Search+Application+Query+Syntax">Lucene search syntax</a>. ' +
            'This gives you many options, but can be very simple as well. ' +
            'Examples of valid searches include:' +
            '<ul><li><a href="/search/?q=repro*">repro*</a></li>' +
            '<li><a href="/search/?q=brian+AND+title%3Amany">brian AND title:many</a></li>' +
            '<li><a href="/search/?q=tags%3A%28psychology%29">tags:(psychology)</a></li></ul>' +
            '</p>'
    });
};

ViewModel.prototype.filter = function(alias) {
    var self = this;
    self.searchStarted(false);
    self.currentPage(1);
    self.category(alias);
    if (alias.parent) {
        self.type(alias.name);
    }
    else {
        self.type('');
    }

    if (alias.name === 'SHARE') {
        document.location = '/share/?' + $.param({
            q: self.query()
        });
    } else {
        self.search();
    }
};

ViewModel.prototype.addTag = function(name) {
    var self = this;
    // To handle passing from template vs. in main html
    var tag = name;

    if (typeof name.name !== 'undefined') {
        tag = name.name;
    }

    self.currentPage(1);
    var tagString = 'tags:("' + tag + '")';

    if (self.query().indexOf(tagString) === -1) {
        if (self.query() !== '') {
            self.query(self.query() + ' AND ');
        }
        self.query(self.query() + tagString);
        self.category(new Category('total', 0, 'Total'));
    }
    self.search();
};

ViewModel.prototype.submit = function() {
    var self = this;
    $('#searchPageFullBar').blur().focus();
    self.searchStarted(false);
    self.totalResults(0);
    self.currentPage(1);
    self.search();
};

ViewModel.prototype.sortCategories = function(a, b) {
    if(a.name === 'total') {
        return -1;
    } else if (b.name === 'total') {
        return 1;
    }
    return a.count >  b.count ? -1 : 1;
};

ViewModel.prototype.updateCategories = function(counts, typeAliases){
    var self = this;

    var categories = counts;
    //Load our categories
    $.each(categories, function(key, cat) {
        if (cat.value === null) {
            cat.value = 0;
        }
        self.categories.push(new Category(key, cat.value, typeAliases[key], {
            children: cat.subcategories, 
            aliases: typeAliases
        }));
    });

    self.categories(self.categories().sort(self.sortCategories));

    // If our category is named attempt to load its total else set it to the total total
    if (self.category().name !== undefined) {
        self.totalResults(counts[self.category().name].value || 0);
    } else {
        self.totalResults(self.categories()[0].value);
    }
};

ViewModel.prototype.updateTags = function(tags) {
    var self = this;

    // Load up our tags
    $.each(tags, function(key, value) {
        self.tags.push(new Tag(value));
        self.tagMaxCount(Math.max(self.tagMaxCount(), value.doc_count));
    });
};

ViewModel.prototype.updateFromSearch = function(noPush, validate, data) {
    var self = this;
    //Clear out our variables
    self.tags([]);
    self.tagMaxCount(1);
    self.results.removeAll();
    self.categories.removeAll();

    data.results.forEach(function(result) {
        if (result.category === 'user') {
            self.results.push(new User(result));
        } else {
            if (typeof result.url !== 'undefined') {
                result.wikiUrl = result.url + 'wiki/';
                result.filesUrl = result.url + 'files/';
            }
            self.results.push(result);
        }
    });

    self.updateCategories(data.counts, data.typeAliases);
    self.updateTags(data.tags);

    self.searchStarted(true);

    if (validate) {
        self.validateSearch();
    }

    if (!noPush) {
        self.pushState();
    }
};

ViewModel.prototype.updateShareCount = function(jsonData) {
    var self = this;
    return $osf.postJSON('/api/v1/share/search/?count', jsonData).success(function(data) {
        self.categories.push(new Category('SHARE', data.count, 'SHARE'));
    });    
};

ViewModel.prototype.search = function(noPush, validate) {
    var self = this;

    var jsonData = {
        query: self.fullQuery(), 
        from: self.currentIndex(),
        size: self.resultsPerPage()
    };
    var url = self.queryUrl + self.category().url;

    $osf.postJSON(url, jsonData)
        .done([
            self.updateFromSearch.bind(self, noPush, validate),
            self.updateShareCount.bind(self, jsonData)
        ])
        .fail(function(response){
            self.totalResults(0);
            self.currentPage(0);
            self.results([]);
            self.tags([]);
            self.categories([]);
            self.searchStarted(false);
            $osf.handleJSONError(response);
        });
};

ViewModel.prototype.paginate = function(val) {
    var self = this;
    window.scrollTo(0, 0);
    self.currentPage(self.currentPage() + val);
    self.search();
};

//History JS callback
ViewModel.prototype.pageChange = function() {
    var self = this;
    if (self.stateJustPushed) {
        self.stateJustPushed = false;
        return;
    }

    self.loadState();

    self.search(true);
};

//Ensure that the first url displays properly
ViewModel.prototype.validateSearch = function() {
    var self = this;
    var possibleCategories;
    if (self.category().name !== undefined) {
        possibleCategories = $.map(self.categories().filter(function(category) {
            return category.count > 0;
        }), function(category) {
            return category.name;
        });

        if (possibleCategories.indexOf(self.category().name) === -1 && possibleCategories.length !== 0) {
            self.filter(self.categories()[0]);
            return self.search(true);
        }
    }
    if (self.currentPage() > self.totalPages() && self.currentPage() !== 1) {
        self.currentPage(self.totalPages());
        return self.search(true);
    }
};

//Load state from History JS
ViewModel.prototype.loadState = function() {
    var self = this;
    var state = History.getState().data;
    self.currentPage(state.page || 1);
    self.setCategory(state.filter);
    self.query(state.query || '');
    self.type(state.filter || '');
};

//Push a new state to History
ViewModel.prototype.pushState = function() {
    var self = this;
    var state = {
        filter: '',
        category: '',
        query: self.query(),
        page: self.currentPage(),
        scrollTop: $(window).scrollTop()
    };

    var url = '?q=' + self.query();

    if (self.category().name !== undefined && self.category().url !== '') {
        state.filter = self.category().name;
        if (['project', 'registration', 'SHARE'].indexOf(self.category().name) >= 0){
            state.category = self.category().name;
        }
        else {
            state.category = 'component';
        }
        url += ('&filter=' + self.category().name);
    }

    url += ('&page=' + self.currentPage());

    //Indicate that we've just pushed a state so the
    //Call back does not process this push as a state change
    self.stateJustPushed = true;
    History.pushState(state, 'OSF | Search', url);
};

ViewModel.prototype.setCategory = function(cat) {
    var self = this;
    if (cat !== undefined && cat !== null && cat !== '') {
        if (!['project', 'registration', 'SHARE'].indexOf(cat)){
            cat = 'component';
        }
        self.category(new Category(cat, 0, cat.charAt(0).toUpperCase() + cat.slice(1) + 's', []));
    } else {
        self.category(new Category('total', 0, 'Total', []));
    }
};

ViewModel.prototype.nodeShowMore = function(info) {
    bootbox.dialog({
        title: info.name,
        message: 
    });
};

ViewModel.prototype.nodeLoadMore = function(node) {
    var self = this;
    var url = ['/api/v1/project', node.url, 'info/'].join('');
    $.getJSON(url)
        .done(self.nodeShowMore)
        .fail(function(xhr, status, error) {

        });
};

function Search(selector, url, appURL) {
    // Initialization code
    var self = this;

    self.viewModel = new ViewModel({
        'url': url,
        'appURL': appURL
    });
    History.Adapter.bind(window, 'statechange', self.viewModel.pageChange.bind(self.viewModel));

    var data = {
        query: $osf.urlParams().q,
        page: Number($osf.urlParams().page),
        scrollTop: 0,
        filter: $osf.urlParams().filter,
        category: $osf.urlParams().category
    };
    //Ensure our state keeps its URL paramaters
    History.replaceState(data, 'OSF | Search', window.location.search);
    //Set out observables from the newly replaced state
    self.viewModel.loadState();
    //Preform search from url params
    self.viewModel.search(true, true);

    $osf.applyBindings(self.viewModel, selector);
}

module.exports = Search;
