<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Add-ons</%def>

<div class="row project-page">
    <span id="selectAddonsAnchor" class="anchor"></span>

    <!-- Begin left column -->
    % if permissions.WRITE in user['permissions'] and any(addon['enabled'] for addon in addon_settings):
        <div class="col-sm-3 affix-parent scrollspy">


                <div class="panel panel-default osf-affix" data-spy="affix" data-offset-top="0" data-offset-bottom="263"><!-- Begin sidebar -->
                    <ul class="nav nav-stacked nav-pills">
                        <li><a href="#selectAddonsAnchor">${_("Select Add-ons")}</a></li>
                        <li><a href="#configureAddonsAnchor">${_("Configure Add-ons")}</a></li>
                    </ul>
                </div><!-- End sidebar -->

        </div>
        <div class="col-sm-9">
    % else:
         <div class="col-sm-12">
    % endif

    <!-- End left column -->
        % if permissions.WRITE in user['permissions']:  ## Begin Select Addons

            % if not node['is_registration']:
                <div class="panel panel-default" id="selectAddon">
                    <div class="panel-heading clearfix">
                        <div class="row">
                            <div class="col-md-12">
                                <h3 class="panel-title">${_("Select Add-ons")}</h3>
                            </div>
                        </div>
                    </div>
                    <div class="panel-body">
                        ${_("Sync your projects with external services to help stay connected and organized. Select a category and browse the options.")}
                        <div class="select-addon-panel">
                            <table class="addon-table">
                                <thead>
                                    <tr>
                                        <td style="padding: 10px">
                                            <b>${_("Categories")}</b>
                                        </td>
                                        <td>
                                            <input id="filter-addons" class="" placeholder="${_('Search...')}" type="text">
                                        </td>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td class="addon-category-list">
                                            <ul class="nav nav-pills nav-stacked">
                                                <li data-toggle="tab" name="All"  class="addon-categories active">
                                                    <a href="#All" name="All">${_("All")}
                                                        <span class="fa fa-caret-right pull-right"></span>
                                                    </a>
                                                </li>
                                                % for category in addon_categories:
                                                    <li data-toggle="tab" name="${category}" class="addon-categories">
                                                        <a href="#${category}" name="${category}">${_(category.capitalize())}
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
                                                                    % if addon['short_name'] == 'metadata' and not addon.get('enabled'):
                                                                        <a>${_("Enable")}</a>
                                                                    % else:
                                                                        <div class="text-muted">${_("(This is a default addon)")}</div>
                                                                    % endif
                                                                 % elif addon.get('enabled'):
                                                                    <a class="text-danger">${_("Disable")}</a>
                                                                 % else:
                                                                     <a>${_("Enable")}</a>
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

        % if any(addon['enabled'] and (addon.get('addon_short_name', '') == 'metadata' or not addon['default']) for addon in addon_settings):
            ## Begin Configure Addons
            <div class="panel panel-default" id="configureAddon">
                <span id="configureAddonsAnchor" class="anchor"></span>
                <div class="panel-heading clearfix">
                    <div class="row">
                        <div class="col-md-12">
                            <h3 class="panel-title">${_("Configure Add-ons")}</h3>
                        </div>
                    </div>
                </div>
                <div style="padding: 10px">
                    % for addon in [addon for addon in addon_settings if addon['enabled'] and (addon.get('addon_short_name', '') == 'metadata' or not addon['default'])]:
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
                                        <h4>${_("Don't see your GitHub organization repositories?")}</h4>
                                        <p>
                                            ${_("You may need to reauthorize your GitHub access token.")}
                                            ${_('Follow the steps in the <a %(osfHelp)s>help guide</a> to resolve the issue.') % \
                                            dict(osfHelp='class="alert-link" href="http://help.osf.io/a/850865-reauthorize-github" target="_black"') | n} <br>
                                        </p>
                                        <p>
                                            ${_('Please contact <a %(mailtoRdmSupport)s>rdm_support@nii.ac.jp</a> if you have questions.') % dict(mailtoRdmSupport='class="alert-link" href="mailto:rdm_support@nii.ac.jp"') | n}
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

% for name, capabilities in addon_capabilities.items():
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
