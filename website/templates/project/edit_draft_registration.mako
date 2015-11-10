<%inherit file="project/project_base.mako" />
<%def name="title()">Edit ${node['title']} registration</%def>

<div id="draftRegistrationScope" class="scripted">
  <div class="row">
    <h3>
      <div class="row">
        <div class="col-md-9">
          Edit draft registration
        </div>
        <div class="col-md-3" data-bind="with: draft">
          <span class="btn-group" data-bind="if: requiresApproval">
            <a data-bind="click: $root.submitForReview,
                          css: {
                          'disable': isPendingReview
                          },
                          tooltip: {
                          position: 'top',
                          title: isPendingReview ? 'Request for review already sent' : 'Submit for review'
                          }" class="btn btn-default" type="button">
              <i class="fa fa"></i> Submit for review
            </a>
          </span>
        </div>
      </div>
    </h3>
    <hr />
    <div class="row">
      <div class="col-md-12">
        <div id="registrationEditorScope">
          <div class="container">
            <div class="row">
              <div class="span8 col-md-2 columns eight large-8">
                <ul class="nav nav-stacked list-group" data-bind="foreach: {data: currentPages, as: 'page'}">
                  <li class="re-navbar">
                    <a class="registration-editor-page" id="top-nav" style="text-align: left; font-weight:bold;" data-bind="text: title, click: $root.selectPage">
                      <i class="fa fa-caret-right"></i>
                    </a>
                    <span class="btn-group-vertical" role="group">
                      <ul class="list-group" data-bind="foreach: {data: Object.keys(page.questions), as: 'qid'}">
                        <span data-bind="with: page.questions[qid]">
                          <li data-bind="css: {
                                           list-item-warning: !$data.value.isValid(),
                                           registration-editor-question-current: $root.currentQuestion().id === $data.id,
                                           list-group-item-danger: $root.showValidation() && $data.validationStatus()
                                         },
                                         click: $root.currentQuestion.bind($root, $data)"
                              class="registration-editor-question list-group-item">
                            <a data-bind="attr.href: '#' + id, text: nav"></a>
                          </li>
                        </span>
                      </ul>
                    </span>
                  </li>
                </ul>
              </div>
              <div class="span8 col-md-9 columns eight large-8">
                <a id="editorPreviousQuestion"
                   data-bind="click: previousQuestion,
                              onKeyPress: {
                                keyCode: 37,
                                listener: previousQuestion.bind($data)
                              }" style="padding-left: 5px;">
                  <i style="display:inline-block; padding-left: 5px; padding-right: 5px;" class="fa fa-arrow-left"></i>Previous
                </a>
                <a id="editorNextQuestion"
                   data-bind="click: nextQuestion,
                              onKeyPress: {
                                keyCode: 39,
                                listener: nextQuestion.bind($data)
                              }" style="float:right; padding-right:5px;">Next
                  <i style="display:inline-block; padding-right: 5px; padding-left: 5px;" class="fa fa-arrow-right"></i>
                </a>
                <br />
                <br />
                <!-- EDITOR -->
                <div data-bind="if: currentQuestion">
                  <div id="registrationEditor" data-bind="template: {data: currentQuestion, name: 'editor'}">
                  </div>
                </div>
                <p>Last saved: <span data-bind="text: $root.lastSaved"></span>
                </p>
                <button data-bind="click: save" type="button" class="btn btn-primary">Save
                </button>
                <span data-bind="tooltip: {
                                   title: canRegister() ? 'Register' : 'This draft requires approval before it can be registered'
                                 }">
                  <a data-bind="css: {'disabled': !canRegister()},
                                click: $root.check" type="button" class="pull-right btn btn-success">Register
                  </a>
                </span>
                
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<%def name="javascript_bottom()">
  ${parent.javascript_bottom()}

  <script>
   window.contextVars = $.extend(true, {}, window.contextVars, {
     draft: ${draft | sjson, n}
   });

  </script>
  <script src=${ "/static/public/js/registration-edit-page.js" | webpack_asset}>
  </script>

</%def>

<%include file="project/registration_editor_templates.mako" />
