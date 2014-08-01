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

    self.createProject = function() {
      //TODO create project here
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


    function fetchSuccess(ret) {
      self.templates(ko.utils.arrayMap(ret.projects, function(item) {
        return {
          title: item.title,
          id: item.id
        };
      }));
    }

    function fetchFailed() {
    
    }

    $.ajax({
        type: 'GET',
        url: '/api/v1/search/',
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

