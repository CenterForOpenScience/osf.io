<div id="registrationEditorScope">
    <div class="container">
        <div class="row">
            <div class="span8 col-md-2 columns eight large-8">
                <ul class="nav nav-stacked list-group" data-bind="foreach: {data: currentPages, as: 'page'}">
                    <li class="re-navbar">
                        <a class="registration-editor-page" style="text-align: left; font-weight:bold;" data-bind="text: title, click: $root.selectPage">
                            <i class="fa fa-caret-right"></i>
                        </a>
                        <span class="btn-group-vertical" role="group">
                  <ul class="list-group" data-bind="foreach: {data: Object.keys(page.questions), as: 'qid'}">
                    <span data-bind="with: page.questions[qid]">
                      <li data-bind="css: {
                                       list-group-item-success: isComplete,
                                       list-group-item-warning: !isComplete(),
                                       registration-editor-question-current: $root.currentQuestion().id === $data.id
                                     },
                                     click: $root.currentQuestion.bind($root, $data),
                                     text: nav"
                          class="registration-editor-question list-group-item">
                    </li>
                    </span>
                  </ul>
                </span>
                    </li>
                </ul>
            </div>
            <div class="span8 col-md-9 columns eight large-8">
                <a data-bind="click: previousPage" style="padding-left: 5px;">
                    <i style="display:inline-block; padding-left: 5px; padding-right: 5px;" class="fa fa-arrow-left"></i>Previous
                </a>
                <a data-bind="click: nextPage" style="float:right; padding-right:5px;">Next
                    <i style="display:inline-block; padding-right: 5px; padding-left: 5px;" class="fa fa-arrow-right"></i>
                </a>
                <!-- EDITOR -->
                <div data-bind="if: currentQuestion">
                  <div id="registrationEditor" data-bind="template: {data: currentQuestion, name: 'editor'}">
                  </div>
                </div>
                <p>Last saved: <span data-bind="text: $root.lastSaved()"></span>
                </p>
                <button data-bind="click: save" type="button" class="btn btn-success">Save
                </button>
                </div>                               
            </div>
        </div>
    </div>
</div>

<%include file="registration_editor_templates.mako" />
