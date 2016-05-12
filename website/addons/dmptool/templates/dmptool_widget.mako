% if complete:
<%inherit file="project/addon/widget.mako"/>

    <div id="dmptoolScope" class="scripted">

        <span data-bind="if: loaded">

            <span data-bind="if: connected">
                <%doc><pre data-bind="text: ko.toJSON($data, null, 2)"></pre></%doc>

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

                <div><span>current plan.id</span>: <span data-bind="text: plan_id"></span></div>
                <div><span>current plan.created</span>: <span data-bind="text: plan_created"></span></div>
                <div><span>current requirements.length</span>: <span data-bind="text: plan_requirements().length"></span></div>

            </span>

        </span>

        <div id="dmptool-output">
          <div><span>current plan name</span>: <span data-bind="text: plan_name"></span></div>

          <div data-bind="foreach: plan_requirements">
            <dl>
              <strong data-bind="text: text_brief"></strong>
              <div data-bind="text: response"></div>
            </dl>
          </div>

        </div>

        <div class="help-block">
            <p data-bind="html: message, attr: {class: messageClass}"></p>
        </div>

    </div>
% endif
