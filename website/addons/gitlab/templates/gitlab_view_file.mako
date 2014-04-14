<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">

<div class="scripted" id="commitScope">

    <table class="table">

        <thead>
            <tr>
                <th>Commit</th>
                <th>Date</th>
                <th>User</th>
                <th colspan="2">Downloads</th>
            </tr>
        </thead>

        <tbody data-bind="foreach: {data: commits}">
            <tr data-bind="css.active: $data.sha === $root.sha">
                <td>
                    <a data-bind="attr.href: $data.urls.view">{{ $data.sha.slice(0, 10) }}</a>
                </td>
                <td>
                    <a data-bind="attr.href: $data.committer.url">
                        {{ $data.committer.name }}
                    </a>
                </td>
                <td>{{ $data.modified.local }}</td>
                <td>{{ $data.downloads }}</td>
                <td>
                    <a data-bind="attr.href: $data.urls.download">
                        <i class="icon-download-alt"></i>
                    </a>
                </td>
            </tr>
        </tbody>

    </table>

</div>

<script>
    $script(['/static/addons/gitlab/commits.js'], function() {
        var url = '${commits_url}';
        var commitTable = new CommitTable('#commitScope', url);
    });
</script>

</%def>
