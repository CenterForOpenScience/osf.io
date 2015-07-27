<%inherit file="project/project_base.mako"/>

## Use full page width
<%def name="container_class()">container-xxl</%def>

<%def name="title()">
    % if blog is None:
        New Post
    % else:
        Edit Post
    % endif
</%def>
<div class="row">
  <div class="col-sm-12">
    <h2 class="break-word">
        % if blog is None:
            New Post
        % else:
            Edit Post
        % endif
    </h2>
  </div>
</div>
<hr>
<div class="row">

  <div id="file-navigation" class="panel-toggle col-sm-3 file-tree">
    <div class="osf-panel panel panel-default osf-panel-hide osf-panel-flex reset-height">
      <div class="panel-heading clearfix osf-panel-header-flex" style="display:none">
        <div id="filesSearch"></div>
        <div id="toggleIcon" class="pull-right">
          <div class="panel-collapse"><i class="fa fa-angle-left"></i></div>
        </div>
      </div>

      <div class="osf-panel-body-flex file-page reset-height">
        <div id="grid">
          <div class="spinner-loading-wrapper">
            <div class="logo-spin text-center"><img src="/static/img/logo_spin.png" alt="loader"> </div>
            <p class="m-t-sm fg-load-message"> Loading files...  </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Menu toggle closed -->
    <div class="panel panel-default osf-panel-show text-center reset-height"  style="display: none">
      <div class="panel-heading">
        <i class="fa fa-file"></i>
        <i class="fa fa-angle-right"></i>
      </div>
    </div>
  </div>


  <div id="fileViewPanelLeft" class="col-sm-9 panel-expand">
    <form id="wiki-form" data-bind="submit: save">

    <div class="row">
        <div class="col-lg-6">
            <input type="text" class="form-control" name="title" placeholder="Post Title">
        </div>
    </div>
    <div class="row">

        <!-- Edit panel -->
        <div class="file-view-panels col-lg-6">
            <div data-osf-panel="Edit">
                <div class="osf-panel panel panel-default">
                  <div class="panel-heading clearfix">
                    <div class="row">
                      <div class="col-md-12">
                           <span class="panel-title" > <i class="fa fa-pencil-square-o"> </i>   Edit </span>
                      </div>
                    </div>
                  </div>
                  <div class="panel-body">
                        <div class="row">
                        <div class="col-xs-12">
                          <div id="editPanel" class="form-group wmd-panel">
                              <div id="wmd-button-bar"></div>

                              <div id="editor" class="wmd-input wiki-editor"
                                   data-bind="ace: currentText"></div>
                          </div>
                        </div>
                      </div>
                  </div>
                  <div class="panel-footer">
                      <div class="row">
                        <div class="col-xs-12">
                           <div class="pull-right">
                              <input type="submit"
                                     class="btn btn-success"
                                     value="Save">
                          </div>
                        </div>
                      </div>
                        <!-- Invisible textarea for form submission -->
                        <textarea id="hidden" name="content" style="display: none;"
                                  data-bind="html: currentText"></textarea>

                      </div>
                </div>
            </div>
            </div>

        <!-- View panel -->
        <div id="viewParent" class="col-sm-6">
              <div class="osf-panel panel panel-default">
                <div class="panel-heading clearfix">
                    <div class="row">
                        <div class="col-sm-12">
                            <span class="panel-title" > <i class="fa fa-eye"> </i>  View</span>
                        </div>
                    </div>
                </div>

                <div id="wikiViewPanel"  class="panel-body">
                  <div id="wikiViewRender" data-bind="html: renderedView, mathjaxify: renderedView, anchorScroll : { buffer: 50, elem : '#wikiViewPanel'}" class=" markdown-it-view">
                  </div>
                </div>
              </div>
          </div>


    </div>
        </form>
  </div>

</div>


## Begin Modals
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
## End Modals block

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
      window.contextVars = $.extend(true, {}, window.contextVars, {
        file: {
            provider: '${provider | js_str}',
            name: '${name | js_str}',
        },
        uid: '${user['id'] | js_str}',
        guid:'${node['root_id'] | js_str}',
        node: {
          path: '${path | js_str}',
          urls: {
            files: '${urls['files'] | js_str}'
          }
        },
        blog: ${json.dumps(blog)}
      });
    </script>

    <link href="/static/css/pages/blog-creation.css" rel="stylesheet">
    <script src=${"/static/public/js/add-blog-post.js" | webpack_asset}></script>
    <script src=${"/static/public/js/view-file-tree-page.js" | webpack_asset}></script>
</%def>
