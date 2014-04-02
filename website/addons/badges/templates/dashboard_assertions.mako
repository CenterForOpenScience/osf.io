<div class="hgrid" id="assertionGrid" width="100%"></div>

<script src="/static/vendor/hgrid/hgrid.js"></script>


<script type="text/javascript">
    var assertions = [
    %for assertion in assertions:
        {
            date: '${assertion.issued_date}',
            badge: '${assertion.badge.name}',
            badge_id: '${assertion.badge._id}',
            project: '${assertion.node.title}',
            project_id:'${assertion.node._id}'
        },
    %endfor
    ];

    var dateColumn = {
        text: 'Awarded on',
        itemView: '{{ date }}',
        sortable: true,
        sortkey: 'date', // property of item object on which to sort on
    };
    var badgeColumn = {
        text: 'Badge',
        itemView: '<a href="/{{ badge_id }}/">{{ badge }}</a>',
        sortable: true,
        sortkey: 'badge', // property of item object on which to sort on
    };
    var projectColumn = {
        text: 'Project',
        itemView: '<a href="/{{ project_id }}/">{{ project }}</a>',
        sortable: true,
        sortkey: 'project', // property of item object on which to sort on
    };

    var grid = new HGrid('#assertionGrid', {
        columns: [
            badgeColumn,
            dateColumn,
            projectColumn
        ],
        data: assertions,
        width: '100%'
    });
</script>
