<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Registrations</%def>

<div class="page-header">
  <div class="pull-right">
      % if 'admin' in user['permissions'] and node['node_type'] == 'project' and not disk_saving_mode:
      <a href="${node['url']}register" class="btn btn-default" type="button">New Registration</a>
    % endif
  </div>
  <h2>Registrations</h2>
</div>

% if node["registration_count"]:
    <div mod-meta='{
        "tpl": "util/render_nodes.mako",
        "uri": "${node["api_url"]}get_registrations/",
        "replace": true
        }'></div>
% elif node['node_type'] != 'project':
    To register this component, you must <a href="${parent_node['url']}registrations"><b>register its parent project</b></a> (<a href="${parent_node['url']}">${parent_node['title']}</a>).
% else:
    There have been no registrations of this ${node['node_type']}.
    For a list of the most viewed and most recent public registrations on the
    Open Science Framework, click <a href="/explore/activity/">here</a>.

% endif
