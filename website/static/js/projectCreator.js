;(function (global, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['knockout', 'osfutils'], factory);
  } else {
    global.ProjectCreator = factory(ko);
  }
}(this, function(ko) {
  'use strict';

  function ProjectCreatorViewModel(url) {
    var self = this;
    self.url = url;
    self.title = ko.observable();
    self.description = ko.observable();
    self.selectedTemplate = ko.observable();
    self.templates = ko.observableArray([]);
    self.otherTemplates = ko.observableArray([]);

    self.createProject = function() {
      $.osf.postJSON(self.createUrl, self.serialize(), self.createSuccess, self.createFailure);
    };

    self.createSuccess = function(data) {
      window.location = data.projectUrl;
    };

    self.createFailure = function() {
    };

    self.serialize = function() {
      return {
        title: self.title(),
        description: self.description(),
        template: self.selectedTemplate()
      };
    };

    self.ownProjects = function(q) {
      var results = [];
      if (q==='') {
        results = self.templates();
      } else {
        results =  self.templates().filter(function(item) {
          return q === '' || item.text.toLowerCase().indexOf(q.toLowerCase()) !== -1;
        });
      }

      return results;
    };

    self.query = function(query) {
      if (query.term.length > 2) {
        self.fetchNodes(query.term, query.callback);
        return;
      }
      query.callback({results: [{text: 'Your Projects', children: self.ownProjects(query.term)}]});
    };

    self.fetchNodes = function(q, cb) {
      $.osf.postJSON('/api/v1/search/node/', { includePublic: true, query: q},
        function(data) {
          var local = self.ownProjects(q);

          var fetched =  ko.utils.arrayMap(data.nodes,
            function(node) {
              return {
                'id': node.id,
                'text': node.title
              };
            });

          fetched = fetched.filter(function(element) {
            for (var i=0; i < local.length; i++) {
              if (element.id === local[i].id) {
                return false;
              }
            }
            return true;
          });

          var more = (fetched.length + local.length === 0);

          if (fetched.length > 0) {
            var results = [
              {text: 'Your Projects', children: local},
              {text: 'Other Projects', children: fetched}
            ];
          } else {
            var results = [
              {text: 'Your Projects', children: local},
            ];
          }
          cb({more: more, results: results});
        }
      );
    };

    function fetchSuccess(ret) {
      self.templates(ko.utils.arrayMap(ret.nodes, function(item) {
         return {
           text: item.title,
           id: item.id
         };
       }));

       $('#templates').select2({
         allowClear: true,
         placeholder: 'Select a Project to Use as a Template',
         query: self.query
        });
    }

    function fetchFailed() {

    }

    $.ajax({
        type: 'GET',
        url: '/api/v1/dashboard/get_nodes/',
        dataType: 'json',
        success: fetchSuccess,
        error: fetchFailed
    });

  }

  function ProjectCreator(selector, url) {
    window.viewModel = new ProjectCreatorViewModel(url);
    $.osf.applyBindings(window.viewModel, selector);
  }

  return ProjectCreator;
}));

