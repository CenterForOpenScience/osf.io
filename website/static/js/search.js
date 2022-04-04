'use strict';

var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
require('bootstrap.growl');

var siteLicenses = require('js/licenses');
var licenses = siteLicenses.list;
var DEFAULT_LICENSE = siteLicenses.DEFAULT_LICENSE;

var $osf = require('js/osfHelpers');


// Disable IE Caching of JSON
$.ajaxSetup({ cache: false });

var eqInsensitive = function(str1, str2) {
    return str1.toUpperCase() === str2.toUpperCase();
};

var Category = function(name, count, display){
    var self = this;

    self.name = name;
    self.count = count;
    self.display = display;

    self.url = ko.computed(function() {
        if (self.name === 'total') {
            return '';
        }
        return self.name + '/';
    });
};

var Tag = function(tagInfo){
    var self = this;
    self.name = tagInfo.key;
    self.count = tagInfo.doc_count;
};

var License = function(name, id, count) {

    this.name = name;
    this.id = id;
    this.count = ko.observable(count);

    this.active = ko.observable(false);
};
License.prototype.toggleActive = function() {
    this.active(!this.active());
};

var User = function(result){
    var self = this;
    self.category = result.category;
    self.profileImageUrl = ko.observable('');
    self.social = result.social;
    self.job_title = result.job_title;
    self.job = result.job;
    self.degree = result.degree;
    self.school = result.school;
    self.url = result.url;
    self.user = result.user;

    $.ajax('/api/v1'+ result.url).done(function(data){
        if (typeof data.profile !== 'undefined') {
            self.profileImageUrl(data.profile.profile_image_url);
        }
    });
};

var ViewModel = function(params) {
    var self = this;
    self.params = params || {};
    self.queryUrl = self.params.url;
    self.appURL = self.params.appURL;

    self.tag = ko.observable('');
    self.stateJustPushed = true;
    self.query = ko.observable('');
    self.category = ko.observable({});
    self.tags = ko.observableArray([]);
    self.tagMaxCount = ko.observable(1);
    self.currentPage = ko.observable(1);
    self.totalResults = ko.observable(0);
    self.results = ko.observableArray([]);
    self.urlLists = ko.observableArray([]);
    self.searching = ko.observable(false);
    self.resultsPerPage = ko.observable(10);
    self.categories = ko.observableArray([]);
    self.shareCategory = ko.observable('');
    self.searchStarted = ko.observable(false);
    self.showSearch = true;
    self.showClose = false;
    self.searchCSS = ko.observable('active');
    self.onSearchPage = true;

    self.licenses = ko.observable(
        $.map(licenses, function(license) {
            var l = new License(license.name, license.id, 0);
            l.active.subscribe(function() {
                self.currentPage(1);
                self.search();
            });
            return l;
        })
    );
    self.licenseNames = ko.computed(function() {
        var sortedLicenses = self.licenses() || [];
        sortedLicenses.sort(function(a, b) {
            if (a.count() > b.count()) {
                return -1;
            }
            else if (b.count() > a.count()) {
                return 1;
            }
            else {
                if (a.name > b.name) {
                    return 1;
                }
                else {
                    return -1;
                }
                return 0;
            }
        });
        return $.map(sortedLicenses, function(count, name) {
            return name;
        });
    });
    self.selectedLicenses = ko.pureComputed(function() {
        return (self.licenses() || []).filter(function(license) {
            return license.active();
        });
    });
    self.showLicenses = ko.computed(function() {
        return ['project', 'registration', 'component'].indexOf(self.category().name) >= 0;
    });
    self.category.subscribe(function(value) {
        if (['project', 'registration', 'component'].indexOf(value) < 0) {
            $.each(self.licenses(), function(i, license) {
                license.active(false);
            });
        }
    });

    // Maintain compatibility with hiding search bar elsewhere on the site
    self.toggleSearch = function() {
    };

    self.allCategories = ko.pureComputed(function(){
        if(self.shareCategory()){
            return self.categories().concat(self.shareCategory());
        }
        return self.categories();
    });

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
        return Math.max(self.resultsPerPage() * (self.currentPage()-1),0);
    });

    self.navLocation = ko.pureComputed(function() {
        return 'Page ' + self.currentPage() + ' of ' + self.totalPages();
    });

    self.queryObject = ko.pureComputed(function(){
        var TITLE_BOOST = '4';
        var DESCRIPTION_BOOST = '1.2';
        var JOB_SCHOOL_BOOST = '1';
        var ALL_JOB_SCHOOL_BOOST = '0.125';

        var fields = [
            '_all',
            'title^' + TITLE_BOOST,
            'description^' + DESCRIPTION_BOOST,
            'job^' + JOB_SCHOOL_BOOST,
            'school^' + JOB_SCHOOL_BOOST,
            'all_jobs^' + ALL_JOB_SCHOOL_BOOST,
            'all_schools^' + ALL_JOB_SCHOOL_BOOST
        ];
        return {
            'query_string': {
                'default_field': '_all',
                'fields': fields,
                'query': self.query(),
                'analyze_wildcard': true,
                'lenient': true
            }
        };
    });

    self.filters = function(){
        var selectedLicenses = self.selectedLicenses();
        if (selectedLicenses.length) {
            var filters = {
                terms: {
                    'license.id': $.map(selectedLicenses, function(l) {
                        return l.id;
                    })
                }
            };
            if (selectedLicenses.filter(function(l) {
                return eqInsensitive(l.id, DEFAULT_LICENSE.id);
            }).length) {
                filters = {
                    or: [
                        filters,
                        {
                            missing: {field: 'license'}
                        }
                    ]
                };
            }
            return filters;
        }
        return null;
    };

    self.fullQuery = function(filters) {
        var query = {
            filtered: {
                query: self.queryObject()
            }
        };
        if (filters) {
            query.filtered.filter = filters;
        }

        return query;
    };

    self.sortCategories = function(a, b) {
        if(a.name === 'Total') {
            return -1;
        } else if (b.name === 'Total') {
            return 1;
        }
        return a.count >  b.count ? -1 : 1;
    };

    self.help = function() {
        bootbox.dialog({
            title: 'Search help',
            message: '<h4>Queries</h4>'+
                '<p>Search uses the <a href="http://extensions.xwiki.org/xwiki/bin/view/Extension/Search+Application+Query+Syntax">Lucene search syntax</a>. ' +
                'This gives you many options, but can be very simple as well. ' +
                'Examples of valid searches include:' +
                '<ul><li><a href="/search/?q=repro*">repro*</a></li>' +
                '<li><a href="/search/?q=brian+AND+title%3Amany">brian AND title:many</a></li>' +
                '<li><a href="/search/?q=tags%3A%28psychology%29">tags:(psychology)</a></li></ul>' +
                '</p>'
        });
    };

    self.filter = function(alias) {
        self.searchStarted(false);
        self.currentPage(1);
        self.category(alias);
        var win = null;
        if (alias.name === 'SHARE') {
            win = window.open(window.contextVars.shareUrl + 'discover?' + $.param({q: self.query()}), '_blank');
            win.opener = null;
            win.focus();
        } else if (alias.name === 'preprint') {
            win = window.open(window.location.origin + '/preprints/discover?' + $.param({q: self.query()}), '_blank');
            win.opener = null;
            win.focus();
        } else if (alias.name === 'institution') {
            win = window.open(window.location.origin + '/institutions/', '_blank');
            win.opener = null;
            win.focus();
        } else {
            self.search();
        }
    };

    self._makeTagString = function(tagName) {
        return 'tags:("' + tagName.replace(/"/g, '\\\"') + '")';
    };
    self.addTag = function(tagName) {
        var tagString = self._makeTagString(tagName);
        var query = self.query();
        if (query.indexOf(tagString) === -1) {
            if (self.query() !== '') {
                query += ' AND ';
            }
            query += tagString;
            self.query(query);
            self.onUpdateTags();
        }
    };
    self.removeTag = function(tagName, _, e) {
        e.stopPropagation();
        var query = self.query();
        var tagRegExp = /(?:AND)?\s*tags\:\([\'\"](.+?)[\'\"]\)/g;
        var dirty = false;
        var match;
        while ((match = tagRegExp.exec(query))) {
            var block = match.shift();
            var tag = match.shift().trim();
            if (tag === tagName) {
                query = query.replace(block, '').trim();
                dirty = true;
            }
        }
        if (dirty) {
            self.query(query);
            self.onUpdateTags();
        }
    };
    self.onUpdateTags = function() {
        self.category(new Category('total', 0, 'Total'));
        self.currentPage(1);
        self.search();
    };

    self.submit = function() {
        $('#searchPageFullBar').blur().focus();
        self.searchStarted(false);
        self.totalResults(0);
        self.currentPage(1);
        self.search();
    };

    self.search = function(noPush, validate) {

        self.searching(true);

        // Check for NOTs and ANDs put spaces before the ones that don't have spaces
        var query = self.query().replace(/\s?NOT tags:/g, ' NOT tags:');
        query = query.replace(/\s?AND tags:/g, ' AND tags:');
        self.query(query);

        var jsonData = {
            query: self.fullQuery(self.filters()),
            from: self.currentIndex(),
            size: self.resultsPerPage()
        };
        var url = self.queryUrl + self.category().url();

        var shareQuery = {
            query: {
                query_string: {
                    query: self.query()
                }
            }
        };

        $osf.postJSON(url, jsonData).done(function(data) {

            //Clear out our variables
            self.tags([]);
            self.tagMaxCount(1);
            self.results.removeAll();
            self.urlLists.removeAll();
            self.categories.removeAll();
            self.shareCategory('');

            // Deep copy license list
            var licenseCounts = self.licenses().slice();
            var noneLicense;
            for(var i = 0; i < licenseCounts.length; i++) {
                var l = licenseCounts[i];
                l.count(0);
                if (eqInsensitive(l.id, DEFAULT_LICENSE.id)) {
                    noneLicense = l;
                }
            }
            noneLicense.count(0);
            var nullLicenseCount = data.aggs.total || 0;
            if ((data.aggs || {}).licenses)  {
                $.each(data.aggs.licenses, function(key, value) {
                    var licenseCount = licenseCounts.filter(function(l) {
                        return eqInsensitive(l.id, key);
                    })[0];
                    if (licenseCount) {
                        licenseCount.count(value);
                    }
                    nullLicenseCount -= value;
                });
            }
            noneLicense.count(noneLicense.count() + nullLicenseCount);
            self.licenses(licenseCounts);

            data.results.forEach(function(result){
                if (result.category === 'user') {
                    if ($.inArray(result.url, self.urlLists()) === -1) {
                        self.results.push(new User(result));
                        self.urlLists.push(result.url);
                    }
                }
                else {
                    if (typeof result.url !== 'undefined') {
                        result.wikiUrl = result.url+'wiki/';
                        result.filesUrl = result.url+'files/';
                    }
                    self.results.push(result);
                }
                if (result.category === 'registration') {
                    result.dateRegistered = new $osf.FormattableDate(result.date_registered);
                } else if (result.category === 'preprint') {
                    result.preprintUrl = result.preprint_url;
                }
            });

            //Load our categories
            var categories = data.counts;
            $.each(categories, function(key, value){
                if (value === null) {
                    value = 0;
                }
                self.categories.push(new Category(key, value, data.typeAliases[key]));
            });

            self.categories(self.categories().sort(self.sortCategories));

            // If our category is named attempt to load its total else set it to the total total
            var selectedLicenses = self.selectedLicenses();
            if (self.category().name !== undefined) {
                if (selectedLicenses.length) {
                    var total = 0;
                    $.each(selectedLicenses, function(i, license) {
                        total += license.count();
                    });
                    self.totalResults(total);
                }
                else {
                    self.totalResults(data.counts[self.category().name] || 0);
                }
            } else {
                self.totalResults(self.self.categories()[0].count);
            }

            // Load up our tags
            $.each(data.tags, function(key, value){
                self.tags.push(new Tag(value));
                self.tagMaxCount(Math.max(self.tagMaxCount(), value.doc_count));
            });

            self.searchStarted(true);

            if (validate) {
                self.validateSearch();
            }

            if (!noPush) {
                self.pushState();
            }

            $osf.postJSON(window.contextVars.shareUrl + 'api/v2/search/creativeworks/_count', shareQuery).done(function(data) {
                if(data.count > 0) {
                    self.shareCategory(new Category('SHARE', data.count, 'SHARE'));
                }
            });

            self.searching(false);

        }).fail(function(response){
            self.totalResults(0);
            self.currentPage(0);
            self.results([]);
            self.tags([]);
            self.categories([]);
            self.searchStarted(false);
            self.searching(false);
            $osf.handleJSONError(response);
        });

    };

    self.paginate = function(val) {
        window.scrollTo(0, 0);
        self.currentPage(self.currentPage() + val);
        self.search();
    };

    self.pagePrev = self.paginate.bind(self, -1);
    self.pageNext = self.paginate.bind(self, 1);

    //History JS callback
    self.pageChange = function() {
        self.loadState();

        self.search(true);
    };

    //Ensure that the first url displays properly
    self.validateSearch = function() {
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
    self.loadState = function() {
        var state = history.state;
        self.currentPage(state.page || 1);
        self.setCategory(state.filter);
        self.query(state.query || '');
    };

    //Push a new state to History
    self.pushState = function() {
        var state = {
            filter: '',
            query: self.query(),
            page: self.currentPage(),
            scrollTop: $(window).scrollTop()
        };

        var url = '?q=' + self.query();

        if (self.category().name !== undefined && self.category().url() !== '') {
            state.filter = self.category().name;
            url += ('&filter=' + self.category().name);
        }

        url += ('&page=' + self.currentPage());

        //Indicate that we've just pushed a state so the
        //Call back does not process this push as a state change
        self.stateJustPushed = true;
        history.pushState(state, 'OSF | Search', url);
    };

    self.setCategory = function(cat) {
        if (cat !== undefined && cat !== null && cat !== '') {
            self.category(new Category(cat, 0, cat.charAt(0).toUpperCase() + cat.slice(1) + 's'));
        } else {
            self.category(new Category('total', 0, 'Total'));
        }
    };

};

function Search(selector, url, appURL) {
    // Initialization code
    var self = this;

    self.viewModel = new ViewModel({'url': url, 'appURL': appURL});

    window.onpopstate = function(event){
        self.viewModel.pageChange(event.state); // will be our state data
    };

    var data = {
        query: $osf.urlParams().q,
        page: Number($osf.urlParams().page),
        scrollTop: 0,
        filter: $osf.urlParams().filter
    };
    //Ensure our state keeps its URL paramaters
    history.replaceState(data, 'OSF | Search', location.search);
    //Set out observables from the newly replaced state
    self.viewModel.loadState();
    //Preform search from url params
    self.viewModel.search(true, true);

    $osf.applyBindings(self.viewModel, selector);
}

module.exports = Search;
