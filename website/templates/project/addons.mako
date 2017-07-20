<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Addons</%def>


        % if 'write' in user['permissions']:  ## Begin Select Addons

            % if not node['is_registration']:

                <div class="panel panel-default" id="addonsList">
                    <span id="selectAddonsAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <div class="row">
                            <div class="col-md-12">
                                <h3 class="panel-title">Select Add-ons</h3>
                                <hr>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-4">
                                Categories
                            </div>
                            <div class="col-md-2">
                                Add-ons
                            </div>
                            <div class="col-md-6">
                                <input type="text" id="filter-addons" class="form-control" placeholder='Search...' style='margin-top: -8px;'>
                            </div>
                        </div>
                    </div>
                    <div class="panel-body">
                        <ul class="nav nav-pills nav-stacked col-md-4">
                            <li data-toggle="tab" name="All"  class="addon-categories active">
                                <a href="#All" name="All">All
                                    <span class="fa fa-arrow-right pull-right"></span>
                                </a>
                            </li>
                            % for category in addon_categories:
                                <li data-toggle="tab" name="${category}" class="addon-categories">
                                    <a href="#${category}" name="${category}">${category.capitalize()}
                                        <span class="fa fa-arrow-right pull-right"></span>
                                    </a>
                                </li>
                            % endfor
                        </ul>
                        <div class="tab-content col-md-8">
                            % for addon in addon_settings:
                                 <div name="${addon['full_name']}" categories="${' '.join(addon['categories'])}" class="addon-container">
                                     % if addon.get('node_settings_template'):
                                         ${render_node_settings(addon)}
                                     % endif
                                     % if not loop.last:
                                         <hr />
                                     % endif
                                 </div>
                            % endfor
                        </div>
                        <div class="addon-settings-message text-success" style="padding-top: 10px;"></div>
                    </div>
                </div>
            % endif
        % endif  ## End Select Addons



<%def name="stylesheets()">
    ${parent.stylesheets()}

    <link rel="stylesheet" href="/static/css/pages/project-page.css">
</%def>

<%def name="render_node_settings(data)">
    <%
       template_name = data['node_settings_template']
       tpl = data['template_lookup'].get_template(template_name).render(**data)
    %>
    ${ tpl | n }
</%def>

% for name, capabilities in addon_capabilities.iteritems():
    <script id="capabilities-${name}" type="text/html">${ capabilities | n }</script>
% endfor

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script>


    </script>
    <script type="text/javascript" src=${"/static/public/js/project-addons-page.js" | webpack_asset}></script>

    % for js_asset in addon_js:
        <script src="${js_asset | webpack_asset}"></script>
    % endfor

</%def>
