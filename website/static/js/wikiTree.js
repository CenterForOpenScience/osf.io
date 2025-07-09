'use strict';
var ko = require('knockout');
require('knockout-sortable');
var $osf = require('js/osfHelpers');

require('../css/fangorn.css');

var isSortCancelled = false;

function fixData(data) {
    var koArray = ko.observableArray();
    var koChildArray = ko.observableArray();
    var totalCtn = 0;
    for (var i = 0; i < data.length; i++) {
        var name = data[i].page ? data[i].page.name : data[i].name;
        var id = data[i].page ? data[i].page.id : data[i].id;
        var sort_order = data[i].page ? data[i].page.sort_order : data[i].sort_order;
        if (id === 'None') {
            continue;
        }
        totalCtn++;
        if (data[i].children !== undefined && data[i].children.length > 0) {
            var koChildArrayData = fixData(data[i].children);
            koChildArray = fixData(data[i].children)[0];

            var childCount = koChildArrayData[1];
            totalCtn += childCount;
            koArray.push(new wikiItem({name: name, id: id, sortOrder:sort_order, children: koChildArray}));
        } else {
            koArray.push(new wikiItem({name: name, id: id, sortOrder: sort_order, children: ko.observableArray()}));
        }
    }
    return [koArray, totalCtn];
}

function wikiItem(item) {
    var self = this;
    self.name = ko.observable(item.name);
    self.id = ko.observable(item.id);
    self.sortOrder = ko.observable(item.sortOrder)
    self.children = item.children;
    self.fold = ko.observable(false);

    self.expandOrCollapse = function() {
        if (isSortCancelled) {
            isSortCancelled = false;
            return
        }
        var parentId = self.id();
        var $display = $('.' + parentId)
        var $angle =　$('#' + parentId).find('.angle');
        if ($display.css('display') === 'list-item') {
            $display.css('display', 'none');
            $angle.attr('class', 'fa fa-angle-right angle');
        } else {
            $display.css('display', '');
            $angle.attr('class', 'fa fa-angle-down angle');
        }
        self.fold(!self.fold());
    };

  };

function assignSortOrderNumber(jsonData) {
    for (var i=0 ; i < jsonData.length ; i++) {
        jsonData[i].sortOrder = i+1;
        if (jsonData[i].children.length > 0) {
            jsonData[i].children = assignSortOrderNumber(jsonData[i].children);
        }
    }
    return jsonData;
  }

  function checkTotalCtn(data, originalCount) {
    var totalCount = 0;
    function countItems(data) {
        for (var i = 0; i < data.length; i++) {
            totalCount++;
            if (totalCount > originalCount) {
                return false;
            }
            if (data[i].children && data[i].children().length > 0) {
                if (!countItems(data[i].children())) {
                    return false;
                }
            }
        }
        return true;
    };
    return countItems(data) && totalCount === originalCount;
};

function ViewModel(data, totalCtn){
    var self = this;
    self.url = window.contextVars.wiki.urls.base;
    self.data = data;
    self.beforeMove = function(obj) {
        var pageName = obj.item.name();
        if (pageName === 'Home') {
            obj.cancelDrop = true;
            isSortCancelled = true;
            return;
        }
    };
    self.afterMove = function(obj) {
        var $SaveBtn = $('#treeSave');
        if (!checkTotalCtn(self.data(), totalCtn)) {
            $SaveBtn.prop('disabled', true);
            $SaveBtn.attr('id', 'treeSaveDisabled');
            alert('sort error! Please reload.');
            return;
        }
        $SaveBtn.prop('disabled', false);
        var parentId = obj.item.id();
        var fold = obj.item.fold();
        var $display = $('.' + parentId);
        var $angle = $('#' + parentId + ' i');
        if (fold) {
            $display.css('display', 'none');
            $angle.attr('fa fa-angle-right');
        }

    };
    self.submit = function() {
        var jsonData = JSON.parse(ko.toJSON(self.data));
        var sortedJsonData = assignSortOrderNumber(jsonData);
        $osf.postJSON(
            window.contextVars.wiki.urls.sort,
            {sortedData: sortedJsonData}
        ).done(function(response) {
            const reloadUrl = (location.href).replace(location.search, '')
            window.location.assign(reloadUrl);
        }).fail(function(xhr) {
            alert('error')
        });
    };
};

var WikiTree = function(selector, data) {
    var self = this;
    var arrays = fixData(data[0].children);
    var currentArray = arrays[0];
    var totalCtn = arrays[1]
    this.viewModel = new ViewModel(currentArray, totalCtn);
    $osf.applyBindings(self.viewModel, selector);
};

module.exports = WikiTree;