var $ = require("jquery");
var ko = require("knockout");
var $osf = require("js/osfHelpers");

var FullContributors = function (params) {
  var self = this;
  self.user = $osf.currentUser();
  self.apiUrl = params.apiUrl;
  self.contributors = ko.observableArray([]);

  // Fetch the data from the server
  self.currentPage = ko.observable(0);
  self.pageSize = 50;
  self.isLoading = ko.observable(false);
  self.hasMoreData = ko.observable(true);

  self.loadAllContributors = function () {
    if (self.isLoading()) return;

    function loadNextBatch() {
      if (!self.hasMoreData()) {
        console.log("All data loaded");
        return;
      }
      self.isLoading(true);

      var url =
        self.apiUrl +
        "get_contributors/?slim&limit=" +
        self.pageSize +
        "&offset=" +
        self.currentPage() * self.pageSize;
      $.getJSON(url, function (data) {
        var contributors = data.contributors.map(function (contributor) {
          contributor.is_condensed = contributor.fullname.length >= 50;
          contributor.condensedFullname = ko.computed(function () {
            var fullname = contributor.fullname;
            if (fullname.length >= 50) {
              return fullname.slice(0, 23) + "..." + fullname.slice(-23);
            }
            return fullname;
          });
          return contributor;
        });

        self.currentPage(self.currentPage() + 1);
        ko.utils.arrayPushAll(self.contributors, contributors);
        self.isLoading(false);

        if (data.more === 0) {
          self.hasMoreData(false);
        } else {
          loadNextBatch();
        }
      });
    }
    loadNextBatch();
  };

  self.loadAllContributors();

  // Function to condense full names if too long
  self.condenseFullname = function (contributor) {
    var fullname = contributor.user_fullname;
    if (fullname.length >= 50) {
      self.is_condensed(true);
      return fullname.slice(0, 23) + "..." + fullname.slice(-23);
    }
    return fullname;
  };

  self.afterRender = function (elements, data) {
    window.dispatchEvent(new Event("resize"));
  };
};

var Contributors = function (params) {
  var self = this;
  self.nodeUrl = ko.observable(params.nodeUrl);
  self.contributors = ko.observableArray(params.contributors);
  self.others_count = ko.observable(params.others_count);
};

function ContributorsControl(options, selector) {
  var self = this;
  self.selector = selector;
  self.viewModel = new FullContributors(options);
  self.init();
}

ContributorsControl.prototype.init = function () {
  var self = this;
  $osf.applyBindings(self.viewModel, this.selector);
};

module.exports = {
  Contributors,
  ContributorsControl,
};
