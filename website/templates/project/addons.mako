<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Add-ons</%def>

<div class="row project-page">
    <span id="selectAddonsAnchor" class="anchor"></span>

    <!-- Begin left column -->
    % if 'write' in user['permissions'] and any(addon['enabled'] for addon in addon_settings):
        <div class="col-sm-3 affix-parent scrollspy">


                <div class="panel panel-default osf-affix" data-spy="affix" data-offset-top="0" data-offset-bottom="263"><!-- Begin sidebar -->
                    <ul class="nav nav-stacked nav-pills">
                        <li><a href="#selectAddonsAnchor">Select Add-ons</a></li>
                        <li><a href="#configureAddonsAnchor">Configure Add-ons</a></li>
                    </ul>
                </div><!-- End sidebar -->

        </div>
        <div class="col-sm-9">
    % else:
         <div class="col-sm-12">
    % endif

    <!-- End left column -->
        % if 'write' in user['permissions']:  ## Begin Select Addons

            % if not node['is_registration']:
                <div class="panel panel-default" id="selectAddon">
                    <div class="panel-heading clearfix">
                        <div class="row">
                            <div class="col-md-12">
                                <h3 class="panel-title">Select Add-ons</h3>
                            </div>
                        </div>
                    </div>
                    <div class="panel-body">
                        Sync your projects with external services to help stay connected and organized. Select a category and browse the options.
                        <div class="select-addon-panel">
                            <table class="addon-table">
                                <thead>
                                    <tr>
                                        <td style="padding: 10px">
                                            <b>Categories</b>
                                        </td>
                                        <td>
                                            <input id="filter-addons" class="" placeholder="Search..." type="text">
                                        </td>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td class="addon-category-list">
                                            <ul class="nav nav-pills nav-stacked">
                                                <li data-toggle="tab" name="All"  class="addon-categories active">
                                                    <a href="#All" name="All">All
                                                        <span class="fa fa-caret-right pull-right"></span>
                                                    </a>
                                                </li>
                                                % for category in addon_categories:
                                                    <li data-toggle="tab" name="${category}" class="addon-categories">
                                                        <a href="#${category}" name="${category}">${category.capitalize()}
                                                            <span class="fa fa-caret-right pull-right"></span>
                                                        </a>
                                                    </li>
                                                % endfor
                                            </ul>
                                        </td>
                                        <td>
                                            <div class="addon-list">
                                                % for addon in addon_settings:
                                                     <div name="${addon['short_name']}" full_name="${addon['full_name']}" status="${'enabled' if addon.get('enabled') else 'disabled'}" categories="${' '.join(addon['categories'])}" class="addon-container">
                                                         <div class="row ${'text-muted' if addon.get('enabled') else ''}">
                                                             <div class="col-md-1">
                                                                 <img class="addon-icon" src="${addon['addon_icon_url']}">
                                                             </div>
                                                             <div class="col-md-4">
                                                                 <b>${addon['full_name']}</b>
                                                             </div>
                                                             <div class="col-md-7">
                                                                 % if addon.get('default'):
                                                                    <div class="text-muted">(This is a default addon)</div>
                                                                 % elif addon.get('enabled'):
                                                                    <a class="text-danger">Disable</a>
                                                                 % else:
                                                                     <a>Enable</a>
                                                                 % endif
                                                             </div>
                                                         </div>
                                                     </div>
                                                % endfor
                                            </div>
                                            <div class="addon-settings-message text-success padded" ></div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            % endif
        % endif  ## End Select Addons

        % if any(addon['enabled'] and not addon['default'] for addon in addon_settings):
            ## Begin Configure Addons
            <div class="panel panel-default" id="configureAddon">
                <span id="configureAddonsAnchor" class="anchor"></span>
                <div class="panel-heading clearfix">
                    <div class="row">
                        <div class="col-md-12">
                            <h3 class="panel-title">Configure Add-ons</h3>
                        </div>
                    </div>
                </div>
                <div style="padding: 10px">
                    % for addon in [addon for addon in addon_settings if addon['enabled'] and not addon['default']]:
                        % if addon.get('node_settings_template'):
                            ${render_node_settings(addon)}
                        % endif
                        % if addon['addon_short_name'] == 'github':
                            <div id='github-organization-repos-alert' class="dismissible-alerts hidden" data-bind="css: {'hidden': $root.isDismissed('githubOrgs')}">
                                <div class="alert alert-info alert-dismissible" role="alert">
                                    <button type="button" class="close" data-dismiss="alert" aria-label="Close"
                                        data-bind="click: $root.dismiss.bind($root, 'githubOrgs')">
                                        <span aria-hidden="true">&times;</span>
                                    </button>
                                    <div>
                                        <h4>Don’t see your GitHub organization repositories?</h4>
                                        <p>
                                            You may need to reauthorize your GitHub access token.
                                            Follow the steps in the <a class="alert-link" href="http://help.osf.io/a/850865-reauthorize-github" target="_black">help guide</a> to resolve the issue. <br>
                                        </p>
                                        <p>
                                            Please contact <a class="alert-link" href="mailto:support@osf.io">support@osf.io</a> if you have questions.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        % endif
                        % if addon['addon_short_name'] == 'zotero':
                            <div id='zotero-group-library-alert' class='scripted dismissible-alerts'>
                                <div class="alert alert-info alert-dismissible" role="alert">
                                    <button type="button" id="zoteroWarningCancel" class="close" data-dismiss="alert" aria-label="Close">
                                        <span aria-hidden="true">&times;</span>
                                    </button>
                                    <div>
                                        <h4>Don’t see your Zotero group libraries?</h4>
                                        <p>
                                            You may need to reauthorize your Zotero access token.
                                            Follow the steps in the <a class="alert-link" href='http://help.osf.io/a/850167-reauthorize-zotero' target="_black">help guide</a> to resolve the issue.
                                        </p>
                                        <p>
                                            Please contact <a class="alert-link" href="mailto:support@osf.io">support@osf.io</a> if you have questions.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        % endif
                        % if not loop.last:
                            <hr />
                        % endif
                    % endfor
                </div>
            </div>
        % endif
        ## End Configure Addons
    </div>
</div>



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
