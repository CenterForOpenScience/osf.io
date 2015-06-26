<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Registrations</%def>

<div class="page-header  visible-xs">
  <h2 class="text-300">Draft Registrations</h2>
</div>
<div id="draftRegistrationScope" class="row" style="min-height: 150px">
  <h3> Draft Registrations       
  </h3>
  <div>
    % if 'admin' in user['permissions'] and not disk_saving_mode:
    <a id="registerNode" class="btn btn-default" type="button">
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
               data-bind="attr.aria-valuenow: completion,
                          style:  {width: completion + '%'}">
            <span class="sr-only"></span>
          </div>
        </div>
        <p data-bind="text: registration_schema.schema.title"></p>
        <p>initiated by <span data-bind="text: initiator.fullname"></span>
        <p>started about <span data-bind="text: $root.formatDate(initiated)"></span></p>
        <p>last updated about <span data-bind="text: $root.formatDate(updated)"></span></p>
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
<br />
<br />
<div class="page-header  visible-xs">
  <h2 class="text-300">Registrations</h2>
</div>
<div class="row" style="min-height: 150px">
  <div class="col-sm-9">
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

<%def name="javascript_bottom()">
${parent.javascript_bottom()}

<script src=${"/static/public/js/project-registrations-page.js" | webpack_asset}> </script>
</%def>

<script type="text/html" id="registrationEditorTemplate">
  <%include file="project/registration_editor.mako"/>
</script>
