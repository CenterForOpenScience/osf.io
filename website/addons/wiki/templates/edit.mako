<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title'] | n} Wiki</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/wiki-page.css">
</%def>
## Use full page width
<%def name="container_class()">container-xxl</%def>

<div class="row" style="margin-bottom: 5px;">
    <div class="col-sm-6">
        <%include file="wiki/templates/status.mako"/>
    </div>
    <div class="col-sm-6">
        <div class="pull-right m-t-md">
          <div class="switch"></div>
          </div>
    </div>
</div>

    <div class="row wiki-wrapper">
        <div class="panel-toggle col-sm-${'3' if 'menu' in panels_used else '1' | n}">

            <!-- Menu with toggle normal -->
            <div class="osf-panel panel panel-default reset-height ${'' if 'menu' in panels_used else 'hidden visible-xs' | n}" data-bind="css: {  'osf-panel-flex': !$root.singleVis() }">
                <div class="panel-heading wiki-panel-header clearfix" data-bind="css: {  'osf-panel-heading-flex': !$root.singleVis()}">
                    % if user['can_edit']:
                        <div class="wiki-toolbar-icon text-success" data-toggle="modal" data-target="#newWiki">
                            <i class="fa fa-plus text-success"></i><span>New</span>
                        </div>
                        % if wiki_id and wiki_name != 'home':
                            <div class="wiki-toolbar-icon text-danger" data-toggle="modal" data-target="#deleteWiki">
                                <i class="fa fa-trash-o text-danger"></i><span>Delete</span>
                            </div>
                        % endif
                    % else:
                        <h3 class="panel-title"> <i class="fa fa-list"></i>  Menu </h3>
                    % endif
                    <div id="toggleIcon" class="pull-right hidden-xs">
                        <div class="panel-collapse pointer"><i class="fa fa-angle-left"></i></div>
                    </div>
                </div>
                <div id="grid">
                    <div class="spinner-loading-wrapper">
                        <div class="logo-spin logo-lg"></div>
                        <p class="m-t-sm fg-load-message"> Loading wiki pages...  </p>
                    </div>
                </div>
                <div class="hidden text-danger" id="wikiErrorMessage" style="padding: 15px"></div>
            </div>

            <!-- Menu with toggle collapsed -->
            <div class="osf-panel panel panel-default panel-collapsed hidden-xs text-center ${'hidden' if 'menu' in panels_used else '' | n}" >
                <div class="panel-heading pointer">
                    <i class="fa fa-list"> </i>
                    <i class="fa fa-angle-right"> </i>
                </div>
                <div>
                    <%include file="wiki/templates/nav.mako"/>
                </div>
            </div>
        </div>

    <div class="wiki" id="wikiPageContext">
    <div class="panel-expand col-sm-${'9' if 'menu' in panels_used else '11' | n}">
      <div class="row">

          <div data-osf-panel="View"
               class="${'col-sm-{0}'.format(12 / num_columns) | n}"
               style="${'' if 'view' in panels_used else 'display: none' | n}">
              <div class="osf-panel panel panel-default no-border" data-bind="css: { 'no-border reset-height': $root.singleVis() === 'view', 'osf-panel-flex': $root.singleVis() !== 'view' }">
                <div class="panel-heading wiki-panel-header wiki-single-heading" data-bind="css: { 'osf-panel-heading-flex': $root.singleVis() !== 'view', 'wiki-single-heading': $root.singleVis() === 'view' }">
                    <div class="row">
                        <div class="col-sm-4">
                            <span class="panel-title" > <i class="fa fa-eye"> </i>  View</span>
                        </div>
                        <div class="col-sm-8">

                            <div class="pull-right">
                                <!-- Version Picker -->
                                <select class="form-control" data-bind="value:viewVersion" id="viewVersionSelect">
                                    % if user['can_edit_wiki_body']:
                                        <option value="preview" ${'selected' if version_settings['view'] == 'preview' else ''}>Preview</option>
                                    % endif
                                    % if len(versions) > 0:
                                        <option value="current" ${'selected' if version_settings['view'] == 'current' else ''}>(Current) ${versions[0]['user_fullname']}: ${versions[0]['date']}</option>
                                    % else:
                                        <option value="current" ${'selected' if version_settings['view'] == 'current' else ''}>Current</option>
                                    % endif
                                    % if len(versions) > 1:
                                        % for version in versions[1:]:
                                            <option value="${version['version']}" ${'selected' if version_settings['view'] == version['version'] else ''}>(${version['version']}) ${version['user_fullname']}: ${version['date']}</option>
                                        % endfor
                                    % endif
                                </select>

                            </div>

                        </div>
                    </div>
                </div>

                <div id="wikiViewPanel"  class="panel-body" data-bind="css: { 'osf-panel-body-flex': $root.singleVis() !== 'view' }">
                  <div id="wikiViewRender" data-bind="html: renderedView, mathjaxify: renderedView, anchorScroll : { buffer: 50, elem : '#wikiViewPanel'}" class=" markdown-it-view">
                      % if wiki_content:
                          ${wiki_content | n}
                      % else:
                          <p><em>No wiki content</em></p>
                      % endif
                  </div>
                </div>
              </div>
          </div>

          % if user['can_edit_wiki_body']:
            <div data-bind="with: $root.editVM.wikiEditor.viewModel"
                 data-osf-panel="Edit"
                 class="${'col-sm-{0}'.format(12 / num_columns) | n}"
                 style="${'' if 'edit' in panels_used else 'display: none' | n}">
              <form id="wiki-form" action="${urls['web']['edit']}" method="POST">
                <div class="osf-panel panel panel-default" data-bind="css: { 'no-border': $root.singleVis() === 'edit' }">
                  <div class="panel-heading wiki-panel-header clearfix" data-bind="css : { 'wiki-single-heading': $root.singleVis() === 'edit' }">
                    <div class="row">
                      <div class="col-md-6">
                           <h3 class="panel-title" > <i class="fa fa-pencil-square-o"> </i>   Edit </h3>
                      </div>
                        <div class="col-md-6">
                          <div class="pull-right">
                            <div class="progress no-margin pointer " data-toggle="modal" data-bind="attr: {data-target: modalTarget}" >
                                <div role="progressbar"data-bind="attr: progressBar">
                                    <span class="progress-bar-content p-h-sm">
                                        <span data-bind="text: statusDisplay"></span>
                                        <span class="sharejs-info-btn">
                                            <i class="fa fa-question-circle fa-large"></i>
                                        </span>
                                    </span>
                                </div>
                            </div>
                          </div>
                        </div>

                    </div>
                  </div>
                  <div class="panel-body">
                        <div class="row">
                        <div class="col-xs-12">
                          <div class="form-group wmd-panel">
                              <ul class="list-inline" data-bind="foreach: activeUsers" class="pull-right">
                                  <!-- ko ifnot: id === '${user_id}' -->
                                      <li><a data-bind="attr: { href: url }" >
                                          <img data-container="body" data-bind="attr: {src: gravatar}, tooltip: {title: name, placement: 'top'}"
                                               style="border: 1px solid black;">
                                      </a></li>
                                  <!-- /ko -->
                              </ul>

                              <div id="wmd-button-bar"></div>
                              <div id="editor" class="wmd-input wiki-editor"
                                   data-bind="ace: currentText">Loading. . .</div>
                          </div>
                        </div>
                      </div>
                  </div>
                  <div class="panel-footer">
                      <div class="row">
                        <div class="col-xs-12">
                           <div class="pull-right">
                              <button id="revert-button"
                                      class="btn btn-danger"
                                      data-bind="click: revertChanges"
                                      >Revert</button>
                              <input type="submit"
                                     class="btn btn-success"
                                     value="Save"
                                     onclick=$(window).off('beforeunload')>
                          </div>
                        </div>
                      </div>
                        <!-- Invisible textarea for form submission -->
                        <textarea name="content" style="display: none;"
                                  data-bind="value: currentText"></textarea>
                  </div>
                </div>
                </form>

            </div>
          % endif


          <div data-osf-panel="Compare"
               class="${'col-sm-{0}'.format(12 / num_columns) | n}"
               style="${'' if 'compare' in panels_used else 'display: none' | n}">
            <div class="osf-panel panel panel-default osf-panel-flex" data-bind="css: { 'no-border reset-height': $root.singleVis() === 'compare', 'osf-panel-flex': $root.singleVis() !== 'compare' }">
              <div class="panel-heading osf-panel-heading-flex" data-bind="css: {  'osf-panel-heading-flex': $root.singleVis() !== 'compare', 'wiki-single-heading': $root.singleVis() === 'compare'}">
                  <div class="row">
                      <div class="col-xs-12">
                          <span class="panel-title m-r-xs"> <i class="fa fa-exchange"> </i>   Compare </span>
                          <div class="inline" data-bind="css: { 'pull-right' :  $root.singleVis() === 'compare' }">
                            <!-- Version Picker -->
                            <span class="compare-version-text"><i> <span data-bind="text: viewVersionDisplay"></span></i> to
                              <select class="form-control" data-bind="value: compareVersion" id="compareVersionSelect">
                                  % if len(versions) > 0:
                                      <option value="current" ${'selected' if version_settings['compare'] == 'current' else ''}>(Current) ${versions[0]['user_fullname']}: ${versions[0]['date']}</option>
                                  % else:
                                      <option value="current" ${'selected' if version_settings['view'] == 'current' else ''}>Current</option>
                                  % endif
                                  % if len(versions) > 1:
                                      % for version in versions[1:]:
                                          <option value="${version['version']}" ${'selected' if version_settings['compare'] == version['version'] else ''}>(${version['version']}) ${version['user_fullname']}: ${version['date']}</option>
                                      % endfor
                                  % endif

                              </select></span>

                          </div>

                      </div>
                  </div>
              </div>
              <div data-bind="html: renderedCompare, css: { 'osf-panel-body-flex': $root.singleVis() !== 'compare' }" class="panel-body wiki-compare-view">
              </div>
            </div>
          </div>
      </div><!-- end row -->
    </div>

  </div>
</div><!-- end wiki -->

<!-- Wiki modals should also be placed here! --> 
  <%include file="wiki/templates/add_wiki_page.mako"/>
% if wiki_id and wiki_name != 'home':
  <%include file="wiki/templates/delete_wiki_page.mako"/>
% endif

<div class="modal fade" id="permissionsModal">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">Page permissions have changed</h3>
      </div>
      <div class="modal-body">
        <p>Your browser should refresh shortly&hellip;</p>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="renameModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="spinner-loading-wrapper">
                <div class="logo-spin logo-xl"></div>
                 <p class="m-t-sm fg-load-message"> Renaming wiki...  </p>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="deleteModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">Wiki page deleted</h3>
      </div>
      <div class="modal-body">
        <p>Press Confirm to return to the project wiki home page.</p>
      </div>
      <div class="modal-footer">
          <button type="button" class="btn btn-success" data-dismiss="modal">Confirm</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="connectedModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Connected to the collaborative wiki</h3>
      </div>
      <div class="modal-body">
        <p>
            This page is currently connected to the collaborative wiki. All edits made will be visible to
            contributors with write permission in real time. Changes will be stored
            but not published until you click the "Save" button.
        </p>
      </div>
      <div class="modal-footer">
          <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="connectingModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Connecting to the collaborative wiki</h3>
      </div>
      <div class="modal-body">
        <p>
            This page is currently attempting to connect to the collaborative wiki. You may continue to make edits.
            <strong>Changes will not be saved until you press the "Save" button.</strong>
        </p>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="disconnectedModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Collaborative wiki is unavailable</h3>
      </div>
      <div class="modal-body">
        <p>
            The collaborative wiki is currently unavailable. You may continue to make edits.
            <strong>Changes will not be saved until you press the "Save" button.</strong>
        </p>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="unsupportedModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Browser unsupported</h3>
      </div>
      <div class="modal-body">
        <p>
            Your browser does not support collaborative editing. You may continue to make edits.
            <strong>Changes will not be saved until you press the "Save" button.</strong>
        </p>
      </div>
    </div>
  </div>
</div>

<%def name="javascript_bottom()">
<% import json %>
${parent.javascript_bottom()}
<script>

    var canEditBody = ${user['can_edit_wiki_body'] | sjson, n};
    var isContributor = ${user['can_edit']  | sjson, n};

    var canEditPageName = isContributor && ${json.dumps(
        wiki_id and wiki_name != 'home'
    )};

    window.contextVars = window.contextVars || {};
    window.contextVars.wiki = {
        canEdit: canEditBody,
        canEditPageName: canEditPageName,
        usePythonRender: ${json.dumps(use_python_render)},
        versionSettings: ${json.dumps(version_settings) | n},
        panelsUsed: ${json.dumps(panels_used) | n},
        wikiID: '${wiki_id}',
        urls: {
            draft: '${urls['api']['draft']}',
            content: '${urls['api']['content']}',
            rename: '${urls['api']['rename']}',
            grid: '${urls['api']['grid']}',
            page: '${urls['web']['page']}',
            base: '${urls['web']['base']}',
            sharejs: '${sharejs_url}'
        },
        metadata: {
            registration: true,
            docId: '${sharejs_uuid}',
            userId: '${user_id}',
            userName: '${user_full_name}',
            userUrl: '${user_url}',
            userGravatar: '${urls['gravatar']}'.replace('&amp;', '&')
        }
    };
</script>
<script src="//${sharejs_url}/text.js"></script>
<script src="//${sharejs_url}/share.js"></script>
<script src=${"/static/public/js/wiki-edit-page.js" | webpack_asset}></script>
</%def>
