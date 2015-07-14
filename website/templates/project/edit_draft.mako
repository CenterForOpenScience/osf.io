<%inherit file="project/project_base.mako"/>
<%def name="title()">Edit ${node['title']} registration</%def>

<div id="draftRegistrationScope"> 
  <div class="row">
    <h3>
      <div class="row">
        <div class="col-md-9">
          Edit draft registration
        </div>
        <div class="col-md-3" data-bind="with: draft">
          <span class="btn-group" data-bind="if: requiresApproval">
            <a data-bind="click: $root.submit,
                          css: {
                            'disable': isPendingReview
                          },
                          tooltip: {
                            position: 'top',
                            title: isPendingReview ? 'Request for review already sent' : 'Submit for review'
                          }" class="btn btn-default" type="button">
              <i class="fa fa-save"></i> Submit for review
            </a>
          </span>   
        </div>   
      </div>
    </h3>
    <hr />
    <div class="row">
      <div class="col-md-12">
        <%include file="project/registration_editor.mako"/>
      </div>
    </div>
  </div>
</div>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script>
  <% import json %>
  window.contextVars = $.extend(true, {}, window.contextVars, {
  draft: ${json.dumps(draft)},
  
  });
</script>
<script src=${"/static/public/js/registration-edit-page.js" | webpack_asset}> </script>
</%def>
