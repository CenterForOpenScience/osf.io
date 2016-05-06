% if complete:
<%inherit file="project/addon/widget.mako"/>

    <div id="dmptoolScope" class="scripted">

        <span data-bind="if: loaded">

            <span data-bind="if: connected">

                <table>
                    <thead><tr>
                        <th>Title</th><th>created</th><th>modified</th><th>View</th>
                    </tr></thead>
                    <!-- Todo: Generate table body -->
                    <tbody data-bind="foreach: plans">
                      <tr>
                          <! -- link https://dmptool.org/plans/21222/edit -->

                          <td><a data-bind="attr: {href: url}, text: name"></a></td>
                          <td data-bind="text: created"></td>
                          <td data-bind="text: modified"></td>
                          <td><button data-bind="click: $root.renderPlan">Render</button></td>
                      </tr>
                    </tbody>
                </table>

            </span>

        </span>

        <div id="dmptool-output">
        </div>

        <div class="help-block">
            <p data-bind="html: message, attr: {class: messageClass}"></p>
        </div>



    </div>
% endif
