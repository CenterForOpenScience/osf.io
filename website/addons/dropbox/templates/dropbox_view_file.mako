<%inherit file="project/addon/view_file.mako" />

<%def name="file_versions()">
<div class="scripted" id="revisionScope">
    <div id="deletingAlert" class="alert alert-warning fade">
        Deleting your file…
    </div>

    <ol class="breadcrumb">
        <li><a data-bind="attr: {href: filesUrl()}">{{nodeTitle}}</a></li>
        <li>Dropbox</li>
        <li class="active overflow" >{{path}}</li>
    </ol>

    <p>
        <!-- Download button -->
        <a
                data-bind="attr.href: downloadUrl"
                class="btn btn-success btn-md"
            >Download <i class="icon-download-alt" ></i>
        </a>
        % if user['can_edit'] and 'write' in user['permissions']:
            <!--Delete button -->
            <button
                    data-bind="visible: deleteUrl() && !registered(), click: deleteFile"
                    class="btn btn-danger btn-md"
                >Delete <i class="icon-trash"></i>
            </button>
        % endif
    </p>

    <table class="table dropbox-revision-table ">
        <thead>
            <tr>
                <th>Revision</th>
                <th>Date</th>
                <th></th>
            </tr>
        </thead>

        <!-- Highlight current revision in grey, or yellow if modified post-registration -->
        <!--
            Note: Registering Dropbox content is disabled for now; leaving
            this code here in case we enable registrations later on.
            @jmcarp
        -->
        <tbody data-bind="foreach: {data: revisions, as: 'revision'}">
            <tr data-bind="css: {
                    warning: $root.registered() && revision.modified.date > $root.registered(),
                    active: revision.rev === $root.currentRevision
                }">
                <td>
                    <a data-bind="attr: {href: revision.view}">{{ revision.rev }}</a>
                </td>
                <td>{{ revision.modified.local }}</td>
                <td>
                    <a data-bind="attr: {href: revision.download}" class="btn btn-primary btn-sm">
                        <i class="icon-download-alt"></i>
                    </a>
                </td>
            </tr>
        </tbody>

    </table>
    <div class="help-block">
        <p data-bind="if: registered">Revisions marked in
            <span class="text-warning">yellow</span> were made after this
            project was registered.</p>
    </div>
</div>

<script type="text/javascript">
    window.contextVars = $.extend(true, {}, window.contextVars, {
        node: {
            urls: {
                revisions_url: '${revisions_url}'
                }
        }
    });
</script>
</%def>
<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script src="/static/public/js/dropbox/file-detail.js"></script>
</%def>
