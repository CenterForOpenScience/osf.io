<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>


<%def name="file_versions()">
    <table class="table" id="fileVersionHistory">

        <thead>
            <tr>
                <th>ID</th>
                <th>Date</th>
            </tr>
        </thead>

        <tbody data-bind="foreach: revisions">
            <tr>
                <td data-bind="text: rev"></td>
                <td data-bind="text: modified.local, tooltip: {title: modified.utc}"></td>
            </tr>
        </tbody>

    </table>

<script>

    $(function() {
        var url = '${revisionsUrl}';
        var Revision = function(data) {
            this.rev = data.rev;
            this.modified = new FormattableDate(data.rev.modified);
        }
        var RevisionViewModel = function(url) {
            var self = this;
            self.revisions = ko.observableArray([]);
            $.ajax({
                url: url,
                type: 'GET', dataType: 'json',

            })
            .done(function(response) {
                self.revisions(ko.utils.arrayMap(response.result, function(rev) {
                    return new Revision(rev);
                }));
            });
        }
        var $elem = $('#fileVersionHistory');
        ko.applyBindings(new RevisionViewModel(url), $elem[0]);
    })
</script>

</%def>


