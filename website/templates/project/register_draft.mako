<%inherit file="project/project_base.mako"/>

<%def name="title()">Register ${node['title']}</%def>

<%def name="content()">
<div class="col-md-6 col-md-offset-3" id="draftRegistrationScope">        
      <div id="embargo-addon" data-bind="with: $root.embargoAddon">
        <hr />
        
        <p class="help-block">${language.REGISTRATION_EMBARGO_INFO}</p>
        <div class="form-group">
          <label class="control-label">Registration Choice</label>
          <select class="form-control" data-bind="options: registrationOptions,
                                                  value: registrationChoice,
                                                  optionsText: 'message',
                                                  optionsValue: 'value',
                                                  event: {change: checkShowEmbargoDatePicker}"></select>
        </div>
        <span data-bind="visible: showEmbargoDatePicker">
          <div class="form-group">
            <label class="control-label">Embargo End Date</label>
            <input type="text" 
                   data-bind="hasFocus: $root.focusOnPicker"
                   id="endDatePicker" class="form-control">
          </div>
        </span>
      </div>
      
      <div id="register-show-submit">

        <hr />
        
        <p class="help-block">${language.BEFORE_REGISTRATION_INFO}</p>
        
        <div class="form-group">
          <label>
            Type "register" if you are sure you want to continue
          </label>
          <div class="controls">
            <input class="form-control" data-bind="value: $root.continueText, valueUpdate: 'afterkeydown'" />
          </div>
        </div>
      </div>
      
      <button id="register-submit" class="btn btn-primary" data-bind="click: registerDraft,
                                                                      visible: canSubmit">
        Register Now
      </button>     
</div><!-- end #registration_template -->
</%def>

<%def name="javascript_bottom()">

  <% import json %>
  <script type="text/javascript">
    window.contextVars = window.contextVars || {};
    window.contextVars.draft = ${json.dumps(draft)};
  </script>
  <script src=${"/static/public/js/register-page.js" | webpack_asset}></script>
</%def>
