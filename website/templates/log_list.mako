<%page args="scripted" />

### Included where the LogsViewModel is used ###
<div id="logProgressBar" class="progress progress-striped active">
    <div class="progress-bar"  role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" style="width: 100%">
        <span class="sr-only">Loading</span>
    </div>
</div>

<div
    %if scripted:
        class="scripted"
    %endif
        id="logScope">

    <div class="logs">

        <div class="components panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Recent activity </h3>
                <div class="pull-right">
                </div>
            </div>
            <div class="panel-body">
                <p class="help-block" data-bind="if: tzname">
                    All times displayed at
                    <span data-bind="text: tzname"></span>
                    <a href="http://en.wikipedia.org/wiki/Coordinated_Universal_Time" target="_blank">UTC</a> offset.
                </p>
                <span data-bind="if: loading()">
                    <div class="spinner-loading-wrapper">
		                <div class="logo-spin logo-lg"></div>
	                	<p class="m-t-sm text-center"> Loading logs...  </p>
	                </div>
                </span>
                <p data-bind="if: !logs().length && !loading()" class="help-block">
                    No logs to show.
                </p>
                <span data-bind="if: !loading()">
                    <dl class="dl-horizontal activity-log" data-bind="foreach: {data: logs, as: 'log'}"  >
                        <dt><span class="date log-date" data-bind="text: log.date.local, tooltip: {title: log.date.utc}"></span></dt>
                        <dd class="log-content break-word">
                        <!-- ko if: log.hasTemplate() -->
                            <!-- ko if: log.hasUser() -->
                            <span data-bind="if:log.anonymous">
                                <span class="contributor-anonymous">A user</span>
                            </span>
                                <span data-bind="ifnot:log.anonymous">
                                    <span data-bind="if: log.userURL">
                                        <a class="overflow" data-bind="text: log.userFullName || log.apiKey, attr: {href: log.userURL}"></a>
                                    </span>
                                    <span data-bind="ifnot: log.userURL">
                                        <span class="overflow" data-bind="text: log.userFullName"></span>
                                    </span>
                                </span>
                                <!-- Log actions are the same as their template name -->
                                    <span data-bind="template: {name: log.action, data: log}"></span>
                                <!-- /ko -->
                                <!-- ko ifnot: log.hasUser() -->
                                    <!-- Log actions are the same as their template name  + no_user -->
                                    <span data-bind="template: {name: log.action + '_no_user', data: log}"></span>
                                <!-- /ko -->
                            <!-- /ko -->


                            <!-- For debugging purposes: If a log template for a the Log can't be found, show
                                an error message with its log action. -->
                            <!-- ko ifnot: log.hasTemplate() -->
                            <span class="text-danger">Could not render log: "<span data-bind="text: log.action"></span>"</span>
                            <!-- /ko -->
                        </dd>
                    </dl><!-- end foreach logs -->
                </span>
                <div class='help-block absolute-bottom'>
                    <ul class="pagination pagination-sm" data-bind="foreach: paginators">
                        <li data-bind="css: style"><a href="#" data-bind="click: handler, html: text"></a></li>
                    </ul>
                </div>

            </div>
        </div>
</div>
</div><!-- end #logScope -->
<%include file="_log_templates.mako"/>
