<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Settings</%def>

<div class="page-header visible-xs">
  <h2 class="text-300">Settings</h2>
</div>

<div class="row project-page">
    <!-- Begin left column -->
    <div class="col-md-3 col-xs-12 affix-parent scrollspy">

        % if 'write' in user['permissions']:

            <div class="panel panel-default osf-affix" data-spy="affix" data-offset-top="0" data-offset-bottom="263"><!-- Begin sidebar -->
                <ul class="nav nav-stacked nav-pills">

                    % if not node['is_registration']:
                        <li><a href="#configureNodeAnchor">${node['node_type'].capitalize()}</a></li>
                    % endif

                    <li><a href="#nodeStorageLocation">Storage Location</a></li>

                    % if not node['is_registration']:
                        % if 'admin' in user['permissions']:
                            <li><a href="#createVolsAnchor">View-only Links</a></li>
                            <li><a href="#enableRequestAccessAnchor">Access Requests</a></li>
                        % endif

                        <li><a href="#configureWikiAnchor">Wiki</a></li>

                        % if 'admin' in user['permissions']:
                            <li><a href="#configureCommentingAnchor">Commenting</a></li>
                        % endif

                        <li><a href="#configureNotificationsAnchor">Email Notifications</a></li>

                        <li><a href="#redirectLink">Redirect Link</a></li>

                    % endif

                    % if node['is_registration']:

                        % if (node['is_public'] or node['embargo_end_date']) and 'admin' in user['permissions']:
                            <li><a href="#withdrawRegistrationAnchor">Withdraw Public Registration</a></li>
                        % endif

                    % endif

                    % if enable_institutions:
                        <li><a href="#configureInstitutionAnchor">Project Affiliation / Branding</a></li>
                    % endif

                </ul>
            </div><!-- End sidebar -->
        % endif

    </div>
    <!-- End left column -->

    <!-- Begin right column -->
    <div class="col-md-9 col-xs-12">

        % if 'write' in user['permissions']:  ## Begin Configure Project

            % if not node['is_registration']:
                <div class="panel panel-default">
                    <span id="configureNodeAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 id="configureNode" class="panel-title">${node['node_type'].capitalize()}</h3>
                    </div>

                    <div id="projectSettings" class="panel-body">
                        <div class="form-group">
                            <label for="category">Category:</label>
                            <i>(For descriptive purposes)</i>
                            <div class="dropdown generic-dropdown category-list">
                                <button class="btn btn-default dropdown-toggle" type="button" data-toggle="dropdown">
                                    <span data-bind="getIcon: selectedCategory"></span>
                                    <span data-bind="text: selectedCategory" class="text-capitalize"></span>
                                    <span data-bind="ifnot: selectedCategory">Uncategorized</span>
                                    <i class="fa fa-sort"></i>
                                </button>
                                <ul class="dropdown-menu" data-bind="foreach: {data: categoryOptions, as: 'category'}">
                                    <li>
                                          <a href="#" data-bind="click: $root.setCategory.bind($root, category.value)">
                                              <span data-bind="getIcon: category.value"></span>
                                              <span data-bind="text: category.label"></span>
                                          </a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="title">Title:</label>
                            <input class="form-control" type="text" maxlength="200" placeholder="Required" data-bind="value: title,
                                                                                                      valueUpdate: 'afterkeydown'">
                            <span class="text-danger" data-bind="validationMessage: title"></span>
                        </div>
                        <div class="form-group">
                            <label for="description">Description:</label>
                            <textarea placeholder="Optional" data-bind="value: description,
                                             valueUpdate: 'afterkeydown'",
                            class="form-control resize-vertical" style="max-width: 100%"></textarea>
                        </div>
                           <button data-bind="click: cancelAll"
                            class="btn btn-default">Cancel</button>
                            <button data-bind="click: updateAll"
                            class="btn btn-success">Save changes</button>
                        <div class="help-block">
                            <span data-bind="css: messageClass, html: message"></span>
                        </div>
                    % if 'admin' in user['permissions']:
                        <hr />
                            <span data-bind="stopBinding: true">
                                <span id="deleteNode">
                                    <button
                                    data-toggle="modal" data-target="#nodesDelete"
                                    data-bind="click: $root.delete.bind($root, ${node['child_exists'] | sjson, n}, '${node['node_type']}', ${node['is_preprint'] | sjson, n}, '${node['api_url']}')"
                                    class="btn btn-danger btn-delete-node">Delete ${node['node_type']}</button>
                                    <%include file="project/nodes_delete.mako"/>
                                </span>
                            </span>
                    % endif
                    </div>
                </div>

            % endif

        <div class="panel panel-default">
            <span id="nodeStorageLocation" class="anchor"></span>
            <div class="panel-heading clearfix">
                <h3 id="nodeStorageLocation" class="panel-title">Storage Location</h3>
            </div>
            <div class="panel-body">
                <p>
                    <b>Storage location:</b> ${node['storage_location']}
                </p>
                <div class="help-block">
                    <p class="text-muted">This is set on project creation and cannot be changed once set.</p>
                </div>

            </div>
        </div>

        % endif  ## End Configure Project

        % if 'admin' in user['permissions']:  ## Begin create VOLS
            % if not node['is_registration']:
                <div class="panel panel-default">
                    <span id="createVolsAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">View-only Links</h3>
                    </div>
                    <div class="panel-body">
                        <p>
                            Create a link to share this project so those who have the link can view&mdash;but not edit&mdash;the project.
                        </p>
                        <a href="#addPrivateLink" data-toggle="modal" class="btn btn-success btn-sm">
                          <i class="fa fa-plus"></i> Add
                        </a>
                        <%include file="project/private_links.mako"/>
                    </div>
                </div>
            % endif
        % endif ## End create vols

        % if 'admin' in user['permissions']:  ## Begin enable request access
            % if not node['is_registration']:
                <div class="panel panel-default">
                    <span id="enableRequestAccessAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Access Requests</h3>
                    </div>
                    <div class="panel-body">
                        <form id="enableRequestAccessForm">
                            <div>
                                <label class="break-word">
                                    <input
                                            type="checkbox"
                                            name="projectAccess"
                                            class="project-access-select"
                                            data-bind="checked: enabled"
                                    />
                                    Allow users to request access to this project.
                                </label>
                                <div data-bind="visible: enabled()" class="text-success" style="padding-left: 15px">
                                    <p data-bind="text: requestAccessMessage"></p>
                                </div>
                                <div data-bind="visible: !enabled()" class="text-danger" style="padding-left: 15px">
                                    <p data-bind="text: requestAccessMessage"></p>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            % endif
        % endif ## End enable request access

        % if 'write' in user['permissions']:  ## Begin Wiki Config
            % if not node['is_registration']:
                <div class="panel panel-default">
                    <span id="configureWikiAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Wiki</h3>
                    </div>

                <div class="panel-body">
                        <form id="selectWikiForm">
                            <div>
                                <label class="break-word">
                                    <input
                                            type="checkbox"
                                            name="wiki"
                                            class="wiki-select"
                                            data-bind="checked: enabled"
                                    />
                                    Enable the wiki in <b>${node['title']}</b>.
                                </label>

                                <div data-bind="visible: enabled()" class="text-success" style="padding-left: 15px">
                                    <p data-bind="text: wikiMessage"></p>
                                </div>
                                <div data-bind="visible: !enabled()" class="text-danger" style="padding-left: 15px">
                                    <p data-bind="text: wikiMessage"></p>
                                </div>
                            </div>
                        </form>

                        %if wiki_enabled:
                            <h3>Configure</h3>
                            <div style="padding-left: 15px">
                                %if node['is_public']:
                                    <p class="text">Control who can edit the wiki of <b>${node['title']}</b></p>
                                %else:
                                    <p class="text">Control who can edit your wiki. To allow all OSF users to edit the wiki, <b>${node['title']}</b> must be public.</p>
                                %endif
                            </div>

                            <form id="wikiSettings" class="osf-treebeard-minimal">
                                <div id="wgrid">
                                    <div class="spinner-loading-wrapper">
                                        <div class="ball-scale ball-scale-blue">
                                            <div></div>
                                        </div>
                                        <p class="m-t-sm fg-load-message"> Loading wiki settings...  </p>
                                    </div>
                                </div>
                                <div class="help-block" style="padding-left: 15px">
                                    <p id="configureWikiMessage"></p>
                                </div>
                            </form>
                        %endif
                    </div>
                </div>
            %endif
        %endif ## End Wiki Config

        % if 'admin' in user['permissions']:  ## Begin Configure Commenting

            % if not node['is_registration']:

                <div class="panel panel-default">
                    <span id="configureCommentingAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Commenting</h3>
                    </div>

                    <div class="panel-body">

                        <form class="form" id="commentSettings">

                            <div class="radio">
                                <label>
                                    <input type="radio" name="commentLevel" value="private" ${'checked' if comments['level'] == 'private' else ''}>
                                    Only contributors can post comments
                                </label>
                            </div>
                            <div class="radio">
                                <label>
                                    <input type="radio" name="commentLevel" value="public" ${'checked' if comments['level'] == 'public' else ''}>
                                    When the ${node['node_type']} is public, any OSF user can post comments
                                </label>
                            </div>

                            <button class="btn btn-success">Save</button>

                            <!-- Flashed Messages -->
                            <div class="help-block">
                                <p id="configureCommentingMessage"></p>
                            </div>
                        </form>

                    </div>

                </div>
                %endif
            % endif  ## End Configure Commenting

        % if user['has_read_permissions']:  ## Begin Configure Email Notifications

            % if not node['is_registration']:

                <div class="panel panel-default">
                    <span id="configureNotificationsAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Email Notifications</h3>
                    </div>
                    <div class="panel-body">
                        <div class="help-block">
                            <p class="text-muted">These notification settings only apply to you. They do NOT affect any other contributor on this project.</p>
                        </div>
                        <form id="notificationSettings" class="osf-treebeard-minimal">
                            <div id="grid">
                                <div class="spinner-loading-wrapper">
                                    <div class="ball-scale ball-scale-blue">
                                        <div></div>
                                    </div>
                                    <p class="m-t-sm fg-load-message"> Loading notification settings...  </p>
                                </div>
                            </div>
                            <div class="help-block" style="padding-left: 15px">
                                <p id="configureNotificationsMessage"></p>
                            </div>
                        </form>
                    </div>
                </div>

            %endif

        % endif ## End Configure Email Notifications

        % if 'write' in user['permissions']:  ## Begin Redirect Link Config
            % if not node['is_registration']:

                <div class="panel panel-default">
                    <span id="redirectLink" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Redirect Link</h3>
                    </div>
                    <div class="panel-body" id="configureForward">
                        <div>
                            <label>
                                <input
                                    type="checkbox"
                                    name="forward"
                                    data-bind="checked: enabled, disable: pendingRequest"
                                    ${'disabled' if node['is_registration'] else ''}
                                />
                                Redirect visitors from your project page to an external webpage
                            </label>
                        </div>

                        <div data-bind="visible: enabled" style="display: none">

                            <div class="forward-settings">

                                <form class="form" data-bind="submit: submitSettings">

                                    <div class="form-group">
                                        <label for="forwardUrl">URL</label>
                                        <input
                                            id="forwardUrl"
                                            class="form-control"
                                            data-bind="value: url"
                                            placeholder="Send people who visit your OSF project page to this link instead"
                                        />
                                    </div>

                                    <div class="form-group">
                                        <label for="forwardLabel">Label</label>
                                        <input
                                            id="forwardLabel"
                                            class="form-control"
                                            data-bind="value: label"
                                            placeholder="Optional"
                                        />
                                    </div>

                                    <div class="row">
                                        <div class="col-md-10 overflow">
                                            <p data-bind="html: message, attr: {class: messageClass}"></p>
                                        </div>
                                        <div class="col-md-2">
                                            <input
                                                type="submit"
                                               class="btn btn-success pull-right"
                                               value="Save"
                                            />
                                        </div>
                                    </div>

                                </form>

                            </div><!-- end .forward-settings -->
                        </div><!-- end #configureForward -->

                    </div>
                </div>
            %endif
        %endif ## End Redirect Link Config

        % if 'admin' in user['permissions']:  ## Begin Retract Registration

            % if node['is_registration']:

                % if node['is_public'] or node['is_embargoed']:

                    <div class="panel panel-default">
                        <span id="withdrawRegistrationAnchor" class="anchor"></span>

                        <div class="panel-heading clearfix">
                            <h3 class="panel-title">Withdraw Registration</h3>
                        </div>

                        <div class="panel-body">

                            % if parent_node['exists']:

                                <div class="help-block">
                                  Withdrawing children components of a registration is not allowed. Should you wish to
                                  withdraw this component, please withdraw its parent registration <a href="${web_url_for('node_setting', pid=node['root_id'])}">here</a>.
                                </div>

                            % else:

                                <div class="help-block">
                                    Withdrawing a registration will remove its content from the OSF, but leave basic metadata
                                    behind. The title of a withdrawn registration and its contributor list will remain, as will
                                    justification or explanation of the withdrawal, should you wish to provide it. Withdrawn
                                    registrations will be marked with a <strong>withdrawn</strong> tag.
                                </div>

                                %if not node['is_pending_retraction']:
                                    <a class="btn btn-danger" href="${web_url_for('node_registration_retraction_get', pid=node['id'])}">Withdraw Registration</a>
                                % else:
                                    <p><strong>This registration is already pending withdrawal.</strong></p>
                                %endif

                            % endif

                        </div>
                    </div>

                % endif

            % endif

        % endif  ## End Retract Registration

        % if enable_institutions:
             <div class="panel panel-default scripted" id="institutionSettings">
                 <span id="configureInstitutionAnchor" class="anchor"></span>
                 <div class="panel-heading clearfix">
                     <h3 class="panel-title">Project Affiliation / Branding</h3>
                 </div>
                 <div class="panel-body">
                     <div class="help-block">
                         % if 'write' not in user['permissions']:
                             <p class="text-muted">Contributors with read-only permissions to this project cannot add or remove institutional affiliations.</p>
                         % endif:
                         <!-- ko if: affiliatedInstitutions().length == 0 -->
                         Projects can be affiliated with institutions that have created OSF for Institutions accounts.
                         This allows:
                         <ul>
                            <li>institutional logos to be displayed on public projects</li>
                            <li>public projects to be discoverable on specific institutional landing pages</li>
                            <li>single sign-on to the OSF with institutional credentials</li>
                            <li><a href="http://help.osf.io/m/os4i">FAQ</a></li>
                         </ul>
                         <!-- /ko -->
                     </div>
                     <!-- ko if: affiliatedInstitutions().length > 0 -->
                     <label>Affiliated Institutions: </label>
                     <!-- /ko -->
                     <table class="table">
                         <tbody>
                             <!-- ko foreach: {data: affiliatedInstitutions, as: 'item'} -->
                             <tr>
                                 <td><img class="img-circle" width="50px" height="50px" data-bind="attr: {src: item.logo_path}"></td>
                                 <td><span data-bind="text: item.name"></span></td>
                                 <td>
                                     % if 'admin' in user['permissions']:
                                         <button data-bind="disable: $parent.loading(), click: $parent.clearInst" class="pull-right btn btn-danger">Remove</button>
                                     % elif 'write' in user['permissions']:
                                         <!-- ko if: $parent.userInstitutionsIds.indexOf(item.id) !== -1 -->
                                            <button data-bind="disable: $parent.loading(), click: $parent.clearInst" class="pull-right btn btn-danger">Remove</button>
                                         <!-- /ko -->
                                     % endif
                                 </td>
                             </tr>
                             <!-- /ko -->
                         </tbody>
                     </table>
                         </br>
                     <!-- ko if: availableInstitutions().length > 0 -->
                     <label>Available Institutions: </label>
                     <table class="table">
                         <tbody>
                             <!-- ko foreach: {data: availableInstitutions, as: 'item'} -->
                             <tr>
                                 <td><img class="img-circle" width="50px" height="50px" data-bind="attr: {src: item.logo_path}"></td>
                                 <td><span data-bind="text: item.name"></span></td>
                                 % if 'write' in user['permissions']:
                                     <td><button
                                             data-bind="disable: $parent.loading(),
                                             click: $parent.submitInst"
                                             class="pull-right btn btn-success">Add</button></td>
                                 % endif
                             </tr>
                             <!-- /ko -->
                         </tbody>
                     </table>
                     <!-- /ko -->
                 </div>
            </div>
        % endif

    </div>
    <!-- End right column -->

</div>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/project-page.css">
    <link rel="stylesheet" href="/static/css/responsive-tables.css">
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script>
      window.contextVars = window.contextVars || {};
      window.contextVars.node = window.contextVars.node || {};
      window.contextVars.node.description = ${node['description'] | sjson, n };
      window.contextVars.node.nodeType = ${ node['node_type'] | sjson, n };
      window.contextVars.node.institutions = ${ node['institutions'] | sjson, n };
      window.contextVars.node.requestProjectAccessEnabled = ${node['access_requests_enabled'] | sjson, n };
      window.contextVars.nodeCategories = ${ categories | sjson, n };
      window.contextVars.wiki = window.contextVars.wiki || {};
      window.contextVars.wiki.isEnabled = ${wiki_enabled | sjson, n };
      window.contextVars.currentUser = window.contextVars.currentUser || {};
      window.contextVars.currentUser.institutions = ${ user['institutions'] | sjson, n };
      window.contextVars.currentUser.permissions = ${ user['permissions'] | sjson, n } ;
      window.contextVars.analyticsMeta = $.extend(true, {}, window.contextVars.analyticsMeta, {
          pageMeta: {
              title: 'Settings',
              pubic: false,
          },
      });
    </script>

    <script type="text/javascript" src=${"/static/public/js/project-settings-page.js" | webpack_asset}></script>
    <script src=${"/static/public/js/sharing-page.js" | webpack_asset}></script>

    % if not node['is_registration']:
        <script type="text/javascript" src=${"/static/public/js/forward/node-cfg.js" | webpack_asset}></script>
    % endif


</%def>
