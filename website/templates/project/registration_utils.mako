<script id="preRegistrationConsent" type="text/html">
  <span data-bind="html: message"></span>
  <div class="row">
    <div class="col-lg-10 col-lg-offset-1">
      <div class="checkbox checkbox-box">
        <label class="">
          <input type="checkbox" data-bind="checked: consent, value: consent">
          <span data-bind="if: mustAgree">
            I agree
          </span>
          <span data-bind="ifnot: mustAgree">
            I have read these terms
          </span>
        </label>
      </div>
      <button type="submit" class="btn btn-primary pull-right"
              data-bind="click: submit, css: {disabled: !consent()}">Continue</button>

      <button type="submit" class="btn btn-default pull-right"
              style="margin-right: 5px"
              data-bind="click: cancel">Cancel</button>
    </div>
  </div>
</script>

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
