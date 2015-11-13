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
                    <p>
                        <strong data-bind="attr.id: question.id, text: question.title"></strong>:
                        <!-- ko if: value -->
                        <span data-bind="text: question.value"></span>
                        <!-- /ko -->
                    </p>
                </div>
            </div>
        </div>
    </div>
    <div class="row-md-12">
        <a type="button" class="btn btn-default pull-left" href="${draft['urls']['edit']}">Continue editing</a>
        <button id="register-submit" type="button" class="btn btn-success pull-right" 
                data-bind="visible: draft.requiresApproval, click: draft.submitForReview">
          Submit for review
        </button>

        <span data-bind="if: draft.metaSchema.name === 'Prereg Challenge'">
          <button id="register-submit" type="button" class="btn btn-primary pull-right" data-toggle="tooltip" data-placement="top" title="Not eligible for the Pre-Registration Challenge" data-bind="click: draft.registerWithoutReview">Register without review</button>
        </span>       

        <button id="register-submit" type="button" class="btn btn-success pull-right" 
                data-bind="visible: !draft.requiresApproval, click: draft.beforeRegister.bind(draft, null)">
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

<script id="preRegistrationConsent" type="text/html">
  <span data-bind="html: message"></span>
  <div class="row">
    <div class="col-lg-10 col-lg-offset-1">
      <div class="checkbox checkbox-box">
        <label class="">
          <input type="checkbox" data-bind="checked: consent, value: consent">
          I agree to the terms and conditions.
        </label>
      </div>
      <button type="submit" class="btn btn-primary pull-right"
              data-bind="click: submit, css: {disabled: !consent()}">Continue</button>

      <button type="submit" class="btn btn-default pull-right"
              data-bind="click: cancel">Cancel</button>
    </div>
  </div>
</script>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}

    <script type="text/javascript">
    window.contextVars = window.contextVars || {};
    window.contextVars.draft = ${draft | sjson, n};
  </script>
  <script src=${"/static/public/js/register-page.js" | webpack_asset}></script>
</%def>
