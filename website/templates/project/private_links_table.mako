<script id="linkTbl" type="text/html">
    <tr>
        <td data-bind="attr: {class: expanded() ? 'expanded' : null,
                                role: $root.collapsed() ? 'button' : null},
                       click: $root.collapsed() ? toggleExpand : null">
            <span class="link-name m-b-xs" data-bind="text: name"></span>
            <span data-bind="attr: {class: expanded() ? 'fa toggle-icon fa-angle-up' : 'fa toggle-icon fa-angle-down'}"></span>
            <div>
                <div class="btn-group">
                    <button title="Copy to clipboard" class="btn btn-default btn-sm m-r-xs copy-button"
                            data-bind="attr: {'data-clipboard-text': linkUrl}" >
                        <i class="fa fa-copy"></i>
                    </button>
                    <input class="link-url" type="text" data-bind="value: linkUrl, attr:{readonly: readonly}, click: toggle, clickBubble: false"  />
                </div>
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: $root.collapsed() && expanded()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || expanded()">
                <ul class="private-link-list narrow-list" data-bind="foreach: nodesList">
                    <li class="private-link-list-node">
                        <span data-bind="getIcon: $data.category"></span>
                        <a data-bind="text:$data.title, attr: {href: $data.url}"></a>
                    </li>
                </ul>
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: $root.collapsed() && expanded()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || expanded()">
                <span class="link-create-date" data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}"></span>
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: $root.collapsed() && expanded()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || expanded()">
                <a data-bind="text: creator.fullname, attr: {href: creator.url}" class="overflow-block"></a>
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: $root.collapsed() && expanded()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || expanded()">
                <span data-bind="html: anonymousDisplay"></span>
            </div>
        </td>
        <td>
            <div class="td-content" data-bind="visible: expanded() || !$root.collapsed()">
                <span data-bind="click: $root.removeLink, visible: !$root.collapsed()"><i class="fa fa-times fa-2x remove-or-reject"></i></span>
                <button class="btn btn-default btn-sm m-l-md" data-bind="click: $root.removeLink, visible: $root.collapsed()"><i class="fa fa-minus"></i> Remove</button>
            </div>
        </td>
    </tr>
</script>
