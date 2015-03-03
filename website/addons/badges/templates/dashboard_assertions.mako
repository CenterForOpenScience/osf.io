<div class="hgrid" id="assertionGrid" width="100%"></div>

<script type="text/javascript">
$script.ready('hgrid', function() {
        var assertions = [
            %for assertion in assertions:
                %if not assertion.revoked:
                    {
                        date: '${assertion.issued_date}',
                        badge: '${assertion.badge.name}',
                        badge_id: '${assertion.badge._id}',
                        project: '${assertion.node.title}',
                        project_id:'${assertion.node._id}',
                        assertion_id: '${assertion._id}',
                        node_api_url: '${assertion.node.api_url}'
                    },
                %endif
            %endfor
        ];

        var dateColumn = {
            text: 'Awarded on',
            itemView: '{{ date }}',
            sortable: true,
            sortkey: 'date' // property of item object on which to sort on
        };
        var badgeColumn = {
            text: 'Badge',
            itemView: '<a href="/{{ badge_id }}/">{{ badge }}</a>',
            sortable: true,
            sortkey: 'badge' // property of item object on which to sort on
        };
        var projectColumn = {
            text: 'Project',
            itemView: '<a href="/{{ project_id }}/">{{ project }}</a>',
            sortable: true,
            sortkey: 'project' // property of item object on which to sort on
        };
        var revokeColumn = {
            text: 'revoke',
            itemView: '<button class="btn btn-xs btn-danger revoke-badge" aid="{{ assertion_id }}" url="{{ node_api_url }}"><i class="icon-minus"></i></button>',
            sortable: false
        };
        var grid = new HGrid('#assertionGrid', {
            columns: [
                badgeColumn,
                dateColumn,
                projectColumn,
                revokeColumn
            ],
            data: assertions,
            width: '100%'
        });

        $('.revoke-badge').click(function() {
            var $self = $(this);
            bootbox.confirm('Revoke this badge?', function(result) {
                var bid = $self.attr('aid');
                var url = $self.attr('url');
                if(result && bid) {
                    $.ajax({
                        url: url + 'badges/revoke/',
                        method: 'POST',
                        dataType: 'json',
                        contentType: 'application/json',
                        data: JSON.stringify({reason: '', id: bid}),
                        success: function(data) {
                            location.reload();
                        },
                        error: function(xhr, status, error) {
                            $.osf.growl('Could not revoke badge','');
                        }
                    });
                }
            });
        });
});
</script>
