<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title'] | n} Wiki (Edit)</%def>

<div class="wiki">
    <div class="row">
        <div class="col-sm-3">
            <%include file="wiki/templates/nav.mako"/>
            <%include file="wiki/templates/toc.mako"/>
        </div>
        <div class="col-sm-9">
            <%include file="wiki/templates/status.mako"/>
            <form id="wiki-form" action="${urls['web']['edit']}" method="POST">
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
                            <div data-bind="fadeVisible: status() === 'connected'" style="float: right">
                                <ul class="list-inline" data-bind="foreach: activeUsers">
                                    <!-- ko ifnot: id === '${user_id}' -->
                                        <li>
                                            <a data-bind="attr: { href: url }">
                                                <img data-bind="attr: {src: gravatar}, tooltip: {title: name, placement: 'bottom'}"
                                                     style="border: 1px solid black;">
                                            </a>
                                        </li>
                                    <!-- /ko -->
                                </ul>
                            </div>
                            <div data-bind="fadeVisible: status() !== 'connected'">
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
                    <button id="revert-button"
                            class="btn btn-success"
                            data-bind="click: revertChanges"
                            >Revert</button>
                    <input type="submit"
                           class="btn btn-primary"
                           value="Save"
                           onclick=$(window).off('beforeunload')>
                </div>
                <p class="help-block">Preview</p>
                <div id="wmd-preview" class="wmd-panel wmd-preview"></div>
                <!-- Invisible textarea for form submission -->
                <textarea name="content" style="visibility: hidden; height: 0px"
                          data-bind="value: currentText"></textarea>
            </form>
        </div>
    </div><!-- end row -->
</div><!-- end wiki -->

<div class="modal fade" id="permissions-modal">
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

<div class="modal fade" id="rename-modal">
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

<div class="modal fade" id="delete-modal" tabindex="-1">
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

<div class="modal fade" id="connecting-modal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Connecting to the live editor</h3>
      </div>
      <div class="modal-body">
        <p>
            This page is currently attempting to connect to the live
            editor. While you are not yet connected, changes will not be
            saved after leaving this page unless you press the "Save" button.
        </p>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="disconnected-modal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
        <h3 class="modal-title">Live editing is unavailable</h3>
      </div>
      <div class="modal-body">
        <p>
            The live editor is currently unavailable. Other contributors
            are not able to see any of your changes, and changes will not be
            saved after leaving this page unless you press the "Save" button.
        </p>
      </div>
    </div>
  </div>
</div>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script>
    window.contextVars = window.contextVars || {};
    window.contextVars.wiki = {
        urls: {
            content: '${urls['api']['content']}',
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