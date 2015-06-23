<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Registrations</%def>

<div class="page-header  visible-xs">

  <h2 class="text-300">Registrations</h2>
</div>

<div class="row">
  <div class="col-sm-9">
    % if node['is_draft_registration']:
    <div id="registrationEditorScope">
        <select class="form-control" id="registrationSchemaSelect"
                data-bind="options: schemas,
                           optionsText: 'title',
                           optionsValue: 'id',
                           value: selectedSchemaId">
        </select>                
        <div class='container'>
          <div class='row'>
            <div class='span8 col-md-12 columns eight large-8'>
              <h2 id="schemaTitle">Select an option above</h2>
              <p>                
              <ul class="nav navbar-nav"
                  data-bind="foreach: schema().pages">
                <li>
                  <a data-bind="text: title,
                                click: $root.selectPage"></a>
                </li>
              </ul>                
              </p>
              <br />
              <div id="registrationEditor"></div>
              <button data-bind="css: {disabled: disableSave},                                 
                                 click: save" type="button" class="btn btn-success">Save</button>                                 
            </div>
          </div>
        </div>
    </div>
    % else:
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
  <div class="col-sm-3">
    <div>
        % if 'admin' in user['permissions'] and not disk_saving_mode:
          <form id="registerNodeForm" method="post"></form>
          <a id="registerNode" href="${node['url']}register" class="btn btn-default" type="button">New Registration</a>
        % endif
    </div>
    % endif
  </div>
</div>
