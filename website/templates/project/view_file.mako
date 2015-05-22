<%inherit file="project/project_base.mako"/>

## Use full page width
<%def name="container_class()">container-xxl</%def>

<%def name="title()">${file_name | h}</%def>
    <div class="row">
        <div class="col-sm-6">
            <h2 class="break-word">
                ${file_name | h}
                % if file_revision:
                    <small>&nbsp;${file_revision | h}</small>
                % endif
            </h2>
        </div>
        <div class="col-sm-6">
            <div class="pull-right">
                <div class="switch"></div>
            </div>
        </div>
    </div>

    <div id="file-container" class="row">

    <div id="file-navigation" class="panel-toggle col-md-3">
        <div class="osf-panel osf-panel-flex hidden-xs reset-height">
            <div class="osf-panel-header osf-panel-header-flex" style="display:none">
                <div id="filesSearch"></div>
                <div id="toggleIcon" class="pull-right">
                    <div class="panel-collapse"> <i class="fa fa-angle-left"> </i> </div>
                </div>
            </div>

            <div class="osf-panel-body osf-panel-body-flex file-page reset-height">
                <div id="grid">
                      <div class="fangorn-loading"> 
                        <div class="logo-spin text-center"><img src="/static/img/logo_spin.png" alt="loader"> </div> 
                        <p class="m-t-sm fg-load-message"> Loading files...  </p> 
                      </div>
                </div>
            </div>
        </div>

    <!-- Menu toggle closed -->
        <div class="osf-panel panel-collapsed hidden-xs text-center reset-height"  style="display: none">
            <div class="osf-panel-header">
                <i class="fa fa-file"> </i>
                <i class="fa fa-angle-right"> </i>
            </div>
        </div>
    </div>

    <div class="panel-expand col-md-6">
        <div id="fileRendered" class="mfr mfr-file">
            <div class="wiki" id="filePageContext">

            % if user['can_edit'] and is_editable:

                <div data-bind="with: $root.editVM.fileEditor.viewModel" data-osf-panel="Edit" style="display: none">
                    <div class="osf-panel" >
                        <div class="osf-panel-header" >
                            <div class="wiki-panel">
                                <div class="wiki-panel-header">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <span class="wiki-panel-title" > <i class="fa fa-pencil-square-o"></i>   Edit </span>
                                        </div>
                                        <div class="col-md-6">
                                            <div class="pull-right">
                                                <div class="progress progress-no-margin pointer " data-toggle="modal" data-bind="attr: {data-target: modalTarget}" >
                                                    <div role="progressbar" data-bind="attr: progressBar">
                                                        <span class="progress-bar-content">
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
                            </div>
                        </div>

                        <form id="file-edit-form">
                            <div class="wiki-panel-body" style="padding: 10px">
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
                                            <div id="wmd-button-bar" style="display: none"></div>
                                            <div id="editor" class="wmd-input wiki-editor" data-bind="ace: currentText">Loading. . .</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="wiki-panel-footer">
                                <div class="row">
                                    <div class="col-xs-12">
                                        <div class="pull-right">
                                            <button id="revert-button" class="btn btn-danger" data-bind="click: revertChanges">Revert</button>
                                            <input type="submit" class="btn btn-success" value="Save" id="submitEdit">
                                        </div>
                                    </div>
                                </div>

                                <!-- Invisible textarea for form submission -->
                                <textarea id="original_content" style="display: none;">${content}</textarea>
                                <textarea id="edit_content" style="display: none;" data-bind="value: currentText"></textarea>

                            </div>
                        </form>
                    </div>
                </div>
            % else:
                % if rendered is not None:
                    ${rendered}
                % else:
                    <img src="/static/img/loading.gif">
                % endif
            % endif
        </div>
    </div>

    % if user['can_edit'] and is_editable:
    <div data-osf-panel="View">
        <div class="osf-panel" data-bind="css: { 'no-border reset-height': $root.singleVis() === 'view', 'osf-panel-flex': $root.singleVis() !== 'view' }">
            <div class="osf-panel-header bordered" data-bind="css: { 'osf-panel-header-flex': $root.singleVis() !== 'view', 'bordered': $root.singleVis() === 'view' }">
                <div class="row">
                    <div class="col-sm-6">
                        <span class="wiki-panel-title" > <i class="fa fa-eye"> </i>  View</span>
                    </div>
                </div>
            </div>

            <div id="wikiViewPanel"  class="osf-panel-body" >
                <div id="wikiViewRender" >
                    % if content:
                        <pre style="background-color: white; border: none">${content}</pre>
                     % else:
                        <p><em>No file content</em></p>
                    % endif
                </div>
            </div>
        </div>
    </div>

    % endif
    </div>

    <div class="modal fade" id="connectedModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                    <h3 class="modal-title">Connected to collaborative file editing</h3>
                </div>
                <div class="modal-body">
                    <p>
                        This page is currently connected to collaborative file editing. All edits made will be visible to
                        contributors with write permission in real time. Changes will be stored
                        but not published until you click the "Save" button.
                    </p>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="connectingModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                    <h3 class="modal-title">Connecting to collaborative file editing</h3>
                </div>
                <div class="modal-body">
                    <p>
                        This page is currently attempting to connect to collaborative file editing. You may continue to make edits.
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
                    <h3 class="modal-title">Collaborative file editing is unavailable</h3>
                </div>
                <div class="modal-body">
                    <p>
                        Collaborative file editing is currently unavailable. You may continue to make edits.
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

    <div class="col-md-3">
        <div id="fileRevisions" class="scripted">
          <ol class="breadcrumb">
            <li><a href="{{ node.urls.files }}" data-bind="text: node.title"></a></li>
            <li class="active overflow" data-bind="text: file.provider"></li>
            <!-- ko foreach: path.slice(1) -->
            <li class="active overflow" data-bind="text: $data"></li>
            <!-- /ko -->
          </ol>

          <span data-bind="if: currentVersion">
            <a class="btn btn-success btn-md file-download" href="{{ currentVersion().osfDownloadUrl }}" data-bind="click: currentVersion().download">
              Download <i class="fa fa-download"></i>
            </a>
          </span>

          <span data-bind="if: editable">
            <button class="btn btn-danger btn-md file-delete" data-bind="click: askDelete">
              Delete <i class="fa fa-trash-o"></i>
            </button>
          </span>


          <table class="table" data-bind="if: versioningSupported && revisions().length">
            <thead class="file-version-thread">
              <tr>
                <th width="10%">Version ID</th>
                <th data-bind="if: hasDate">Date</th>
                <th data-bind="if: userColumn">User</th>
                <th colspan="2">Download</th>
                <th></th>
              </tr>
            </thead>

            <tbody class="file-version" data-bind="foreach: {data: revisions, as: 'revision'}">
              <tr data-bind="css: $parent.isActive(revision)">
                <td>
                  <a href="{{ revision.osfViewUrl }}" data-bind="if: revision !== $parent.currentVersion()">
                    {{ revision.displayVersion }}
                  </a>
                  <span data-bind="if: revision === $parent.currentVersion()">
                    {{ revision.displayVersion }}
                  </span>
                </td>
                <td data-bind="if: $parent.hasDate">{{ revision.displayDate }}</td>
                <td data-bind="if: $parent.userColumn">
                  <a class="word-break-word" data-bind="if: revision.extra.user.url"
                    href="{{ revision.extra.user.url }}">
                    {{ revision.extra.user.name }}
                  </a>
                  <span data-bind="ifnot: revision.extra.user.url">
                    {{ revision.extra.user.name }}
                  </span>
                </td>
                <td>
                  <span class="badge" data-bind="if: revision.extra.downloads !== undefined">
                    {{ revision.extra.downloads }}
                  </span>
                </td>
                <td>
                  <a class="btn btn-primary btn-sm file-download" href="{{ revision.osfDownloadUrl }}"
                    data-bind="click: revision.download">
                    <i class="fa fa-download"></i>
                  </a>
                </td>
              </tr>
            </tbody>
          </table>

          <div data-bind="ifnot: versioningSupported">
            <hr>
            <div class="alert alert-warning" role="alert">
              {{ errorMessage }}
            </div>
          </div>

        </div>
      </div>
    </div>


<%def name="javascript_bottom()">
<% import json %>
    ${parent.javascript_bottom()}
    % for script in tree_js:
        <script type="text/javascript" src="${script | webpack_asset}"></script>
    % endfor

    % if 'osf.io' in domain:
    <script>
        // IE10 Same Origin (CORS) fix
        document.domain = 'osf.io';
    </script>
    %endif
    <script type="text/javascript">
        var isEditable = false;
      % if user['can_edit'] and is_editable:
          isEditable = true;
      % endif

      window.contextVars = $.extend(true, {}, window.contextVars, {

        %if user['can_edit'] and is_editable:
            renderURL: undefined,
        %elif rendered is not None:
            renderURL: undefined,
        %else:
            renderURL: '${urls['api']['render'] | js_str}',
        %endif

            file: {
                extra: ${extra},
                name: '${file_name | js_str}',
                path: '${file_path | js_str}',
                provider: '${provider | js_str}',
                safeName: '${file_name | h,js_str}'
            },
            node: {
              urls: {
                files: '${files_url | js_str}'
              }
            },
            currentUser: {
              canEdit: ${int(user['can_edit'])}
            },
            files: {
                canEdit: ${json.dumps(user['can_edit'])},
                panelsUsed: ${json.dumps(panels_used) | n},
                isEditable: isEditable,
                urls: {
                    draft: '${urls['api']['render'] | js_str}',
                    content: '${urls['api']['render'] | js_str}',
                    page: '${urls['api']['render'] | js_str}',
                    base: '${urls['api']['render'] | js_str}',
                    sharejs: '${urls['web']['sharejs']}'
                },
                metadata: {
                    registration: true,
                    docId: '${sharejs_uuid}',
                    userId: '${user_id}',
                    userName: '${user_full_name}',
                    userUrl: '${user_url}',
                    userGravatar: '${urls['web']['gravatar']}'.replace('&amp;', '&')
                }
            }
      });
    </script>

    <script>

        $('#submitEdit').on('click', function(e) {
            e.preventDefault();
            var editContent = $('#edit_content').val();
            var originalContent = $('#original_content').val();

            if (editContent != originalContent) {
                var request = $.ajax({
                    type: 'PUT',
                    url: '${urls['web']['edit']}',
                    data: editContent
                });

                request.done(function () {
                    $.ajax({
                        type: 'GET',
                        url: '${urls['web']['view']}'
                    }).done(function() {
                        window.location.href = '${urls['web']['view']}';
                    });
                });

                request.fail(function(error) {
                   $osf.growl('Error', 'The file could not be updated.');
                   Raven.captureMessage('Could not PUT file content.', {
                       url: '${urls['web']['edit']}',
                       error: error
                   });
                });

            } else {
                alert("There are no changes to be saved.");
            }
        });
    </script>

    <script src="//${urls['web']['sharejs']}/text.js"></script>
    <script src="//${urls['web']['sharejs']}/share.js"></script>

    % if user['can_edit'] and is_editable:
        <script src=${"/static/public/js/file-edit-page.js" | webpack_asset}></script>
    % endif

    <script src=${"/static/public/js/view-file-page.js" | webpack_asset}></script>
    <script src=${"/static/public/js/view-file-tree-page.js" | webpack_asset}></script>
</%def>
