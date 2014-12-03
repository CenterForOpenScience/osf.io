% if summary['can_view']:
    <a href="${summary['url']}registrations/">
        <li
                node_id="${summary['id']}"
                node_reference="${summary['id']}:${'node' if summary['primary'] else 'pointer'}"
                class="
                    project list-group-item list-group-item-node cite-container
                    ${'pointer' if not summary['primary'] else ''}
            ">
            <h4 class="list-group-item-heading">
                ${summary['title']}
            </h4>
</a>

% endif
