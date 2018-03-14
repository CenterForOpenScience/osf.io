'use strict';
var $osf = require('js/osfHelpers');


var buildFilteringCSS = function(filter, currentSort, ascending) {
    /**
    * Returns the css classes to help style a particular filter button on the meetings submissions pageß
    *
    * @param {string} filter: particular filter name, title or author, for example
    * @param {string} currentSort: query param, how the data is currently sorted
    * @param {boolean} ascending: whether particular filter is sorting in the ascending direction
    * @returns {string} css classes for particular filter button
    **/
    var directionCSS = ascending ? 'fa-chevron-up asc-button m-r-xs ' : 'fa-chevron-down desc-button ';
    var filterCSS = currentSort === filter ? 'fg-file-links' : 'tb-sort-inactive';
    return directionCSS + filterCSS;
}

var buildFilters = function(filterName, q, currentSort) {
    /**
    * Builds a dictionary for a particular filter button
    *
    * @param {string} filterName: particular filter name, title or author, for example
    * @param {string} q: query param
    * @param {string} currentSort: query param, how the data is currently sorted
    * @returns {dictionary} dictionary with href (filter link) and css for formatting filter button
    **/
    var filters = [];
    var filterNames = [filterName, '-' + filterName];
    for (var i = 0; i <= 1; i++) {
        filters.push({
            href: "?page=1" + "&q=" + q + "&sort=" + filterNames[i],
            filterCSS: buildFilteringCSS(filterNames[i], currentSort, !i)
        });
    }
    return filters;
}

var FilteringViewModel = function(q, currentSort) {
    /**
    * Builds buttons for filtering meeting submissions.
    *
    * @param {string} q: query param
    * @param {string} currentSort: query param, how the data is currently sorted
    * @returns { } dictionaries for all the meetings page submissions filters, containing
    * link and css classes
    **/
    var self = this;
    self.titleFilters = buildFilters('title', q, currentSort);
    self.authorFilters = buildFilters('author', q, currentSort);
    self.categoryFilters = buildFilters('category', q, currentSort);
    self.createdFilters = buildFilters('created', q, currentSort);
    self.downloadsFilters = buildFilters('downloads', q, currentSort);
}

var Filtering = function(selector, q, sort) {
    this.viewModel = new FilteringViewModel(q, sort);
    $osf.applyBindings(this.viewModel, selector);
}

module.exports = Filtering;
