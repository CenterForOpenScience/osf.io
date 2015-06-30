<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Registrations</%def>

<ul id="registrationsTabs" class="nav nav-tabs" role="tablist">
  <li role="presentation" class="active">
    <a id="registrationsControl" aria-controls="registrations" href="#registrations">Registrations</a>
  </li>
  <li role="presentation">
    <a id="draftsControl" aria-controls="drafts" href="#drafts">Draft Registrations</a>
  </li>
  <li role="presentation">
    <a id="editDraftsControl" class="disabled" aria-controls="editDrafts" href="#editDrafts">Edit Draft</a>
  </li>   
</ul>
<div class="tab-content registrations-view">
  <div role="tabpanel" class="tab-pane active" id="registrations">
    <div class="row" style="min-height: 150px">
      <h2> Registrations </h2>
      <div class="col-md-9">
        % if node["registration_count"]:
        <div mod-meta='{
            "tpl": "util/render_nodes.mako",
            "uri": "${node["api_url"]}get_registrations/",
            "replace": true,
            "kwargs": {"sortable": false, "pluralized_node_type": "registrations"}
            }'></div>
    ## Uncomment to disable registering Components
    ##% elif node['node_type'] != 'project':
    ##      %if user['is_admin_parent']:
    ##          To register this component, you must <a href="${parent_node['url']}registrations"><b>register its parent project</b></a> (<a href="${parent_node['url']}">${parent_node['title']}</a>).
    ##      %else:
    ##          There have been no registrations of the parent project (<a href="${parent_node['url']}">${parent_node['title']}</a>).
    ##      %endif
        % else:
        There have been no registrations of this ${node['node_type']}.
        For a list of the most viewed and most recent public registrations on the
        Open Science Framework, click <a href="/explore/activity/#newPublicRegistrations">here</a>.
        % endif
        %if parent_node['exists'] and user['is_admin_parent']:
        <br />
        <br />
        To register the entire project "${parent_node['title']}" instead, click <a href="${parent_node['registrations_url']}">here.</a>
        %endif         
      </div>
    </div>
  </div>
  <div role="tabpanel" class="tab-pane" id="drafts">
    <div id="draftRegistrationScope" class="row" style="min-height: 150px">
      <h2> Draft Registrations </h2>
      <div class="col-md-9">
      <div>
        % if 'admin' in user['permissions'] and not disk_saving_mode:
        <a data-bind="css: {disabled: loading}" id="registerNode" class="btn btn-default" type="button">
          <i class="fa fa-plus"></i>
          New Registration
        </a>
        % endif
      </div>    
      <br />
      <div class="scripted" data-bind="foreach: drafts">
        <li class="project list-group-item list-group-item-node">
          <h4 class="list-group-item-heading">          
            <div class="progress progress-bar-md">
              <div class="progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100"
               data-bind="attr.aria-completion: completion,
                          style: {width: completion + '%'}">
                <span class="sr-only"></span>
              </div>
            </div>
            <p data-bind="text: registration_schema.schema.title"></p>
            <p>initiated by <span data-bind="text: initiator.fullname"></span>
            <p>started about <span data-bind="text: $root.formattedDate(initiated)"></span></p>
            <p>last updated about <span data-bind="text: $root.formattedDate(updated)"></span></p>
            <p>
              <button class="btn btn-success"
                      data-bind="click: $root.editDraft"><i class="fa fa-pencil"></i>Edit</button>
              <button class="btn btn-danger"
                      data-bind="click: $root.deleteDraft"><i class="fa fa-times"></i>Delete</button>
            </p>
          </h4>
        </li>
      </div>
    </div>
    </div>
  </div>  
  <div role="tabpanel" class="tab-pane" id="editDrafts">
    <div class="row">
      <h2> Edit Draft Registration </h2>
      <div class="col-md-12">
        <%include file="project/registration_editor.mako"/>
      </div>
    </div>
  </div>
</div>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}

<script src=${"/static/public/js/project-registrations-page.js" | webpack_asset}> </script>
</%def>
<script type="text/html" id="preRegisterMessageTemplate">
  <div
  <!-- if not a top-level Node -->
  <div data-bind="if: parentUrl">
    You are about to register the 
    <span data-bind="text: category"></span>  
    <b data-bind="text: title"></b> 
    including all components and data within it. This will <b>not</b> register its parent, 
    <b data-bind="text: parentTitle"></b>. If you want to register the parent, please go 
    <a data-bind="attr.href: parentUrl">here.</a>
    After selecting OK, you will next select a registration form.
  </div>
  <!-- if root Node -->
  <div data-bind="ifnot: parentUrl">
    You are about to register <b data-bind="text: title"></b>
    including all components and data within it. Registration creates a permanent, 
    time-stamped, uneditable version of the project. If you would prefer to register 
    only one particular component, please navigate to that component and then initiate registration. 
  </div>
  <br />
  <div class="form-group">
    <label>Please select a registration schema to continue:</label>
    <br />
    <select class="form-control" data-bind="options: schemas,
                                            optionsText: function(metaschema) {return metaschema.schema.title;},
                                            value: selectedSchema">
    </select>
  </div>
  <div class="form-group" style="text-align: right">
    <button class="btn btn-default" data-bind="click: cancel">Cancel</button>
    <button class="btn btn-success" data-bind="click: launchEditor.bind($root, null), css: {disabled: !selectedSchema}">Continue</button>
  </div>
</script>
