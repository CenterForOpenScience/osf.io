<%inherit file="project/project_base.mako"/>

<%def name="title()">Register ${node['title']}</%def>

<div id="draftRegistrationScope">
    <div class="row">
        <div class="col-md-12">
            <h3>Register</h3>
        </div>
    </div>
    <hr>
    <div class="row">
      <div class="col-lg-12 large-12" style="padding-left: 30px">
         <div data-bind="foreach: {data: draft.pages, as: 'page'}">
             <h3 data-bind="attr.id: page.id, text: page.title"></h3>
             <div data-bind="foreach: {data: page.questions, as: 'question'}">
                 <!-- <span data-bind="with: $root.editor.context(question, $root.editor)"> -->
                     <p>
                         <strong data-bind="attr.id: $data.id, text: $data.title"></strong>:
                         <span data-bind="previewQuestion: $root.editor.context(question, $root.editor)"></span>
                     </p>
             </div>
             <!-- <div data-bind="foreach: {data: page.questions, as: 'question'}">
                  <span data-bind="with: question">
                  <span data-bind="with: $root.editor.context(question, $root.editor)">
                  <p>
                  <strong data-bind="attr.id: question.id, text: question.title"></strong>:
                  <span data-bind="previewQuestion: question"></span>
                  </p>
                  </span>
                  </span>
                  </div> -->
            </div>
        </div>
    </div>
    <div class="row-md-12 scripted">
        <a type="button" class="btn btn-default pull-left" href="${draft['urls']['edit']}">Continue editing</a>
        <button id="register-submit" type="button" class="btn btn-success pull-right"
                data-bind="visible: draft.requiresApproval, click: draft.submitForReview">
          Submit for review
        </button>

        <span data-bind="if: draft.metaSchema.name === 'Prereg Challenge'">
          <button id="register-submit" type="button" class="btn btn-primary pull-right" data-toggle="tooltip" data-placement="top" title="Not eligible for the Pre-Registration Challenge" data-bind="click: draft.registerWithoutReview">Register without review</button>
        </span>

        <button id="register-submit" type="button" class="btn btn-success pull-right"
                data-bind="visible: !draft.requiresApproval(), click: draft.beforeRegister.bind(draft, null)">
          Register
        </button>
    </div>
</div>

<script type="text/html" id="preRegistrationTemplate">
  <ul data-bind="foreach: preRegisterPrompts">
    <li data-bind="html: $data"></li>
  </ul>
  <div class="form-group">
    <label class="control-label">Registration Choice</label>
    <select class="form-control" data-bind="options: registrationOptions,
                                            value: registrationChoice,
                                            optionsText: 'message',
                                            optionsValue: 'value',
                                            event: {change: checkShowEmbargoDatePicker}" ></select>
  </div>
  <span data-bind="visible: showEmbargoDatePicker">
    <div class="form-group">
      <label class="control-label">
        Embargo End Date
      </label>
      <input type="text" class="form-control" data-bind="datePicker: {value: $root.pikaday, valid: isEmbargoEndDateValid}">
    </div>
  </span>
  <em class="text-danger" data-bind="validationMessage: $root.pikaday"></em>
  <div class="modal-footer">
    <button class="btn btn-default" data-bind="click: close">Cancel</button>
    <button class="btn btn-success" data-bind="click: register, enable: canRegister">
      Continue
    </button>
  </div>
</script>

<%include file="project/registration_utils.mako" />
<%include file="project/registration_editor_extensions.mako" />

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}

    <script type="text/javascript">
    window.contextVars = window.contextVars || {};
    window.contextVars.draft = ${draft | sjson, n};
  </script>
  <script src=${"/static/public/js/register-page.js" | webpack_asset}></script>
</%def>
