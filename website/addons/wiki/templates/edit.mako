<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title'] | n} Wiki (Edit)</%def>

<style type="text/css" media="screen">
    #editor {
        position: relative;
        height: 300px;
        border: solid;
        border-width: 1px;
    }
</style>

<div class="wiki">
    <div class="row">
        <div class="col-sm-3">
            <%include file="wiki/templates/nav.mako"/>
            <%include file="wiki/templates/toc.mako"/>
        </div>
        <div class="col-sm-9">
            <%include file="wiki/templates/status.mako"/>
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
                        <span data-bind="visible: displayCollaborators()" style="display: none">
                            Also Editing This Wiki:
                        </span>
                        <ul class="list-inline" data-bind="foreach: activeUsers">
                            <!-- ko ifnot: id === '${user_id}' -->
                                <li><a data-bind="text: name, attr: { href: url }" ></a></li>
                            <!-- /ko -->
                        </ul>
                    </div>
                </div>
                <div id="editor" class="wmd-input"
                     data-bind="ace: wikiText">Loading. . .</div>
            </div>
            <div class="pull-right">
                <!-- clicking "Cancel" overrides unsaved changes check -->
                % if wiki_created:
                    <a href="${urls['web']['home']}" class="btn btn-default">Return</a>
                % else:
                    <a href="${urls['web']['page']}" class="btn btn-default">Return</a>
                % endif
                <button id="revert-button" class="btn btn-primary"
                        data-bind="click: revertChanges, enable: changed">Revert to Last Save</button>
                <input type="submit" class="btn btn-success" value="Save Version"
                       data-bind="enable: changed,
                                  click: function() {updateChanged('${urls['web']['edit']}')}"
                       onclick=$(window).off('beforeunload')>
            </div>
            <p class="help-block">Preview</p>
            <div id="wmd-preview" class="wmd-panel wmd-preview"></div>
        </div>
    </div><!-- end row -->
</div><!-- end wiki -->

<script src="/static/vendor/bower_components/ace-builds/src-noconflict/ace.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Converter.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Sanitizer.js"></script>
<script src="/static/vendor/pagedown-ace/Markdown.Editor.js"></script>

<!-- Necessary for ShareJS communication -->
<script src="http://localhost:7007/text.js"></script>
<script src="http://localhost:7007/share.uncompressed.js"></script>
<script src="/static/addons/wiki/ace.js"></script>

<script>

    var url = '${urls['api']['content']}';
    var registration = {
        registration: true,
        docId: '${share_uuid}',
        userId: '${user_id}',
        userName: '${user_full_name}',
        userUrl: '${user_url}'
    };


    $script(['/static/addons/wiki/WikiEditor.js', '/static/addons/wiki/ShareJSDoc.js'], function() {
        var wikiEditor = new WikiEditor('.wiki', url);
        var shareJSDoc = new ShareJSDoc(wikiEditor.viewModel, url, registration);
    });

</script>
