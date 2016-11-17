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
