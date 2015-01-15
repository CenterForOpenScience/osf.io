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
                        <div class="col-sm-8">
                             <p>
                                 <em>Changes will be stored but not published until
                                 you click "Save Version."</em>
                             </p>
                            <div id="wmd-button-bar"></div>
                        </div>
                        <div class="col-sm-4">
                            <ul class="list-inline" data-bind="foreach: activeUsers" style="float: right">
                                <!-- ko ifnot: id === '${user_id}' -->
                                    <li><a data-bind="attr: { href: url }" >
                                        <img data-bind="attr: {src: gravatar}, tooltip: name"
                                             style="border: 1px solid black;">
                                    </a></li>
                                <!-- /ko -->
                            </ul>
                        </div>
                    </div>
                    <div id="editor" class="wmd-input wiki-editor"
                         data-bind="ace: currentText">Loading. . .</div>
                    <!-- Invisible textarea for form submission -->
                    <textarea name="content" style="visibility: hidden" data-bind="value: currentText"></textarea>
                </div>
                <div class="pull-right">
                    <!-- clicking "Cancel" overrides unsaved changes check -->
                        <a class="btn btn-default"
                           data-toggle="tooltip"
                           data-placement="top"
                           title="Your draft version will be saved, but only visible to users with edit permissions."
                        % if wiki_created:
                           href="${urls['web']['home']}"
                        % else:
                           href="${urls['web']['page']}"
                        % endif
                           >
                            Return To View
                        </a>
                    <button id="revert-button"
                            class="btn btn-primary"
                            data-bind="click: loadPublished, enable: changed"
                            data-toggle="tooltip"
                            data-placement="top"
                            title="Clicking this button will revert the current draft to the last published version of this wiki."
                            >Revert to Last Publication</button>
                    <input type="submit"
                           class="btn btn-success"
                           value="Publish Version"
                           data-toggle="tooltip"
                           data-placement="top"
                           title="Publishing this wiki version will allow anyone with read access to view it."
                           data-bind="enable: changed"
                           onclick=$(window).off('beforeunload')>
                </div>
                <p class="help-block">Preview</p>
                <div id="wmd-preview" class="wmd-panel wmd-preview"></div>
            </form>
        </div>
    </div><!-- end row -->
</div><!-- end wiki -->

<div class="modal fade" id="refresh-modal">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h4 class="modal-title">The permissions for this page have changed</h4>
      </div>
      <div class="modal-body">
        <p>Your browser should refresh shortly&hellip;</p>
      </div>
    </div>
  </div>
</div>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script src="/static/vendor/bower_components/ace-builds/src-noconflict/ace.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Converter.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Sanitizer.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Editor.js"></script>

<!-- Necessary for ShareJS communication -->
<script src="http://${sharejs_host}:${sharejs_port}/text.js"></script>
<script src="http://${sharejs_host}:${sharejs_port}/share.js"></script>
<script src="/static/addons/wiki/ace.js"></script>
<script src="/static/addons/wiki/ReconnectingWebSocket.js"></script>

<!-- MD5 Hashing to generate gravatar -->
<script src="http://crypto-js.googlecode.com/svn/tags/3.1.2/build/rollups/md5.js"></script>

<script>
    // Generate gravatar URL
    var baseGravatarUrl = 'http://secure.gravatar.com/avatar/';
    var hash = CryptoJS.MD5('${user_name}'.toLowerCase().trim());
    var params = '?d=identicon&size=32';
    var gravatar = baseGravatarUrl + hash + params;

    window.contextVars = window.contextVars || {};
    window.contextVars.wiki = {
        urls: {content: '${urls['api']['content']}'},
        metadata: {
            registration: true,
            docId: '${sharejs_uuid}',
            userId: '${user_id}',
            userName: '${user_full_name}',
            userUrl: '${user_url}',
            sharejsHost: '${sharejs_host}',
            sharejsPort: '${sharejs_port}',
            gravatarUrl: gravatar
        }
    };

    // Toggle tooltips
    $(function () {
        $('[data-toggle="tooltip"]').tooltip();
    });
</script>
<script src=${"/static/public/js/wiki-edit-page.js" | webpack_asset}></script>
</%def>