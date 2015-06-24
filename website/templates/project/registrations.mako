<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Registrations</%def>

<div class="page-header  visible-xs">

  <h2 class="text-300">Registrations</h2>
</div>

<div class="row">
  <div class="col-sm-9">
    % if node['is_draft_registration']:
    <%include file="project/registration_editor.mako"/>
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

<%def name="javascript_bottom()">
${parent.javascript_bottom()}

<script src=${"/static/public/js/project-registrations-page.js" | webpack_asset}> </script>
</%def>
