<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title'] | n} Wiki</%def>

<div class="wiki">

    <%include file="wiki/templates/status.mako"/>
    <div class="row">

        <!-- Menu Bar -->
##        <div class="col-sm-2">
##            <%include file="wiki/templates/nav.mako"/>
##            <%include file="wiki/templates/toc.mako"/>
##        </div>

        <!-- Edit Page -->
        <div class="col-sm-4">

            <div class="panel panel-default">
                <div class="panel-heading">Edit</div>

                <div class="panel-body">
                    <form id="wikiForm" action="${urls['web']['edit']}" method="POST">
                        <div class="form-group wmd-panel">
                            <div class="row">
                                <div class="col-lg-6 col-md-7">
                                    <p>
                                        <em>Changes will be stored but not published until
                                        you click "Save."</em>
                                    </p>
                                    <div id="wmd-button-bar"></div>
                                </div>
                                <div class="col-lg-6 col-md-5">
                                    <div data-bind="fadeVisible: throttledStatus() === 'connected'" class="pull-right" style="display: none">
                                        <ul class="list-inline" data-bind="foreach: activeUsers">
                                            <!-- ko ifnot: id === '${user_id}' -->
                                                <li>
                                                    <a data-bind="attr: { href: url }">
                                                        <img height="27" width="27" data-bind="attr: {src: gravatar}, tooltip: {title: name, placement: 'bottom'}"
                                                             style="border: 1px solid black;">
                                                    </a>
                                                </li>
                                            <!-- /ko -->
                                        </ul>
                                    </div>
                                    <div data-bind="fadeVisible: throttledStatus() !== 'connected'" style="display: none">
                                        <div class="progress" style="margin-bottom: 5px;">
                                            <div role="progressbar" data-bind="attr: progressBar">
                                                <span data-bind="text: statusDisplay"></span>
                                                <a class="sharejs-info-btn">
                                                    <i class="icon-question-sign icon-large"
                                                       data-toggle="modal"
                                                       data-bind="attr: {data-target: modalTarget}"
                                                    ></i>
                                                </a>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="editor" class="wmd-input wiki-editor"
                                 data-bind="ace: currentText">Loading. . .</div>
                        </div>
                        <div class="pull-right">
                            <button class="btn btn-success"
                                    data-bind="click: revertChanges"
                                    >Revert</button>
                            <input type="submit"
                                   class="btn btn-primary"
                                   value="Save"
                                   onclick=$(window).off('beforeunload')>
                        </div>
                        <p class="help-block">Preview</p>
                        <!-- Invisible textarea for form submission -->
                        <textarea name="content" style="visibility: hidden; height: 0px"
                                  data-bind="value: currentText"></textarea>
                    </form>
                </div>
            </div>
        </div>

        <!-- View Panel -->
        <div class="col-sm-4">

            <div class="panel panel-default">

                <div class="panel-heading">
                    <div class="row">
                        <div class="col-sm-6">
                            View
                        </div>
                        <div class="col-sm-6">
                            <!-- Version Picker -->
                            <select id="viewSelect">
                                <option value="preview">Preview</option>
                                <option value="current">Current</option>
                                % for version in versions:
                                    <option value="${version['version']}">Version ${version['version']}</option>
                                % endfor
                            </select>
                        </div>
                    </div>
                </div>

                <div class="panel-body">
                    <!-- Live preview from editor -->
                    <div id="viewPreview">
                        <div id="markdown-it-preview" class="wmd-panel wmd-preview"></div>
                    </div>
                    <!-- Version view -->
                    <div id="viewVersion" style="display: none;">
                        % if not page and wiki_name != 'home':
                            <p><i>This wiki page does not currently exist.</i></p>
                        % else:
                            <div id="markdown-it-render">${wiki_content | n}</div>
                        % endif
                    </div>
                </div>

            </div>
        </div>

        <!-- Compare (Non functional)-->
        <div class="col-sm-4">
            <div class="panel panel-default">

                <div class="panel-heading">Compare</div>
                <div class="panel-body">
                    Comparison will go here
                </div>
            </div>
        </div>

    </div><!-- end row -->
</div><!-- end wiki -->

<div class="modal fade" id="permissionsModal">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">The permissions for this page have changed</h3>
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
      <div class="modal-header">
        <h3 class="modal-title">The content of this wiki has been moved to a different page</h3>
      </div>
      <div class="modal-body">
        <p>Your browser should refresh shortly&hellip;</p>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="deleteModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">This wiki page has been deleted</h3>
      </div>
      <div class="modal-body">
        <p>Press OK to return to the project wiki home page.</p>
      </div>
      <div class="modal-footer">
          <button type="button" class="btn btn-primary" data-dismiss="modal">OK</button>
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

    var canEditPageName = ${json.dumps(
        all([
            'write' in user['permissions'],
            not is_edit,
            wiki_id,
            wiki_name != 'home',
            not node['is_registration']
        ])
    )};

    window.contextVars = window.contextVars || {};
    window.contextVars.wiki = {
        canEditPageName: canEditPageName,
        usePythonRender: ${json.dumps(use_python_render)},
        urls: {
            content: '${urls['api']['content']}',
            rename: '${urls['api']['rename']}',
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