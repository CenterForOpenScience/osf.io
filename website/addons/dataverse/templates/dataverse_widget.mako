% if complete:
<%inherit file="project/addon/widget.mako"/>

    <div id="dataverseScope" class="scripted">


        <span data-bind="if: loaded">

            <span data-bind="if: connected">
                <dl class="dl-horizontal dl-dataverse" style="white-space: normal">

                    <dt>Study</dt>
                    <dd>{{ study }}</dd>

                    <dt>Global ID</dt>
                    <dd><a data-bind="attr: {href: studyUrl}">{{ doi }}</a></dd>

                    <dt>Dataverse</dt>
                    <dd><a data-bind="attr: {href: dataverseUrl}">{{ dataverse }}</a></dd>

                    <dt>Citation</dt>
                    <dd>{{ citation }}</dd>

                </dl>
            </span>

        </span>

        <div class="help-block">
            <p data-bind="html: message, attr: {class: messageClass}"></p>
        </div>

    </div>
% endif
