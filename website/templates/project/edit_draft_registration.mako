<%inherit file="project/project_base.mako" />
<%def name="title()">Edit ${node['title']} registration</%def>

<div id="draftRegistrationScope" class="scripted">
    <div class="row">
        <div class="col-md-9">
          <h3>Register</h3>
        </div>
    </div>
    <hr />
    <div class="row">
      <div class="col-md-12">
        <div id="registrationEditorScope">
          <div class="container">
            <div class="row">
              <div class="span8 col-md-2 columns eight large-8">
                <ul class="nav nav-stacked list-group" data-bind="foreach: {data: pages, as: 'page'}, visible: pages().length > 1">
                  <li class="re-navbar">
                    <a class="registration-editor-page" id="top-nav" style="text-align: left; font-weight:bold;" data-bind="text: title, click: $root.selectPage">
                      <i class="fa fa-caret-right"></i>
                    </a>
                  </li>
                </ul>
                  <!-- /ko -->
              </div>
              <div class="span8 col-md-9 columns eight large-8">
                <br />
                <br />
                <span data-bind="with: draft">
                    <div class="progress progress-bar-md">
                        <div data-bind="progress: completion"></div>
                        <div class="progress-bar progress-bar-success" role="progressbar" aria-valuemin="0" aria-valuemax="100"
                             data-bind="attr.aria-completion: completion,
                                        style: {width: completion() + '%'}">
                            <!-- <span class="sr-only"></span> -->
                        </div>
                    </div>
                </span>

                <!-- EDITOR -->
                <div data-bind="if: currentPage">
                   <div data-bind="foreach: {data: currentPage().questions, as: 'question'}">
                       <div data-bind="template: {data: question, name: 'editor'}"></div>
                   </div>
                </div>
                <p>Last saved: <span data-bind="text: $root.lastSaved"></span>
                </p>
                <button data-bind="click: saveForLater" type="button" class="btn btn-primary">Save as Draft
                </button>
                    <!-- ko if: onLastPage -->
                    <a data-bind="css: {'disabled': !canRegister()},
                                click: $root.check,
                                tooltip: {
                                   title: canRegister() ? 'Register' : 'This draft requires approval before it can be registered'
                                 }" type="button" class="pull-right btn btn-success">Preview for submission
                    </a>
                    <!-- /ko -->
                    <!-- ko ifnot: onLastPage -->
                      <a data-bind="click: nextPage" class="btn btn-primary pull-right">Next Page</a>
                    <!-- /ko -->
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
