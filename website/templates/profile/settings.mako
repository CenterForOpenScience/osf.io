<%inherit file="base.mako"/>
<%def name="title()">Settings</%def>
<%def name="content()">
<h2 class="page-header">Account Settings</h2>

## TODO: Review and un-comment
##<div class="row">
##    <div class="col-md-6">
##        <div class="panel panel-default">
##            <div class="panel-heading"><h3 class="panel-title">Merge Accounts</h3></div>
##            <div class="panel-body">
##                <a href="/user/merge/">Merge with duplicate account</a>
##            </div>
##        </div>
##    </div>
##</div>

<div class="row">

    <div class="col-md-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="#">Profile Information</a></li>
                <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-md-6">

        <div id="userProfile">

            <ul class="nav nav-tabs">
                <li class="active"><a href="#names" data-toggle="tab">Name</a></li>
                <li><a href="#social" data-toggle="tab">Social</a></li>
                <li><a href="#jobs" data-toggle="tab">Employment</a></li>
                <li><a href="#schools" data-toggle="tab">Education</a></li>
            </ul>

            <div class="tab-content">

                <div class="tab-pane active" id="names">

                    <form role="form" data-bind="submit: submit">

                        <h3>Name</h3>

                        <div class="form-group">
                            <label>Full Name (e.g. Rosalind Elsie Franklin)</label>
                            <input class="form-control" data-bind="value: full" />
                        </div>

                        <span class="help-block">
                            Your full name, above, is the name that will be displayed in your profile.
                            To control the way your name will appear in citations, you can use the
                            "Guess names" button to automatically infer your first name, last
                            name, etc., or edit the fields directly below.
                        </span>

                        <div style="margin-bottom: 10px;">
                            <a class="btn btn-default" data-bind="enabled: hasFirst(), click: impute">Guess names</a>
                        </div>

                        <div class="form-group">
                            <label>Given Name (e.g. Rosalind)</label>
                            <input class="form-control" data-bind="value: given" />
                        </div>

                        <div class="form-group">
                            <label>Middle Name(s) (e.g. Elsie)</label>
                            <input class="form-control" data-bind="value: middle" />
                        </div>

                        <div class="form-group">
                            <label>Family Name (e.g. Franklin)</label>
                            <input class="form-control" data-bind="value: family" />
                        </div>

                        <div class="form-group">
                            <label>Suffix</label>
                            <input class="form-control" data-bind="value: suffix" />
                        </div>

                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Style</th>
                                    <th>Citation Format</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>APA</td>
                                    <td>{{ citeApa }}</td>
                                </tr>
                                <tr>
                                    <td>MLA</td>
                                    <td>{{ citeMla }}</td>
                                </tr>
                            </tbody>
                        </table>

                        <button
                                type="submit"
                                class="btn btn-success"
                                data-bind="enable: isValid"
                            >Submit</button>

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p data-bind="html: message, attr.class: messageClass"></p>
                        </div>

                    </form>

                </div>

                <div class="tab-pane" id="social">

                    <form role="form" data-bind="submit: submit">

                        <h3>Social</h3>

                        <div class="form-group">
                            <label>Personal Site</label>
                            <input class="form-control" data-bind="value: personal" />
                        </div>

                        <div class="form-group">
                            <label>ORCID</label>
                            <input class="form-control" data-bind="value: orcid" />
                        </div>

                        <div class="form-group">
                            <label>ResearcherID</label>
                            <input class="form-control" data-bind="value: researcherId" />
                        </div>

                        <div class="form-group">
                            <label>Twitter</label>
                            <input class="form-control" data-bind="value: twitter" />
                        </div>

                        <button
                                type="submit"
                                class="btn btn-success"
                                data-bind="enable: isValid"
                            >Submit</button>

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p data-bind="html: message, attr.class: messageClass"></p>
                        </div>

                    </form>

                </div>

                <div class="tab-pane" id="jobs">

                    <form role="form" data-bind="submit: submit">

                        <h3>Employment History</h3>

                        <div data-bind="foreach: contents">

                            <div class="well well-sm">
                                Position {{ $index() + 1 }}
                                <a
                                        class="text-danger pull-right"
                                        data-bind="click: $parent.removeContent,
                                                   visible: $parent.canRemove"
                                    >Remove</a>
                            </div>


                            <div class="form-group">
                                <label>Institution / Employer</label>
                                <input class="form-control" data-bind="value: institution" />
                            </div>

                            <div class="form-group">
                                <label>Department</label>
                                <input class="form-control" data-bind="value: department" />
                            </div>

                            <div class="form-group">
                                <label>Job Title</label>
                                <input class="form-control" data-bind="value: title" />
                            </div>

                            <div class="form-group">
                                <label>Start Date</label>
                                <input class="form-control" data-bind="value: start" />
                            </div>

                            <div class="form-group">
                                <label>End Date</label>
                                <input class="form-control" data-bind="value: end" />
                            </div>

                            <hr data-bind="visible: $index() != ($parent.contents().length - 1)" />

                        </div>

                        <div>
                            <a class="btn btn-default" data-bind="click: addContent">
                                Add another
                            </a>
                        </div>

                        <div class="padded">
                            <button
                                    type="submit"
                                    class="btn btn-success"
                                    data-bind="enable: isValid"
                                >Submit</button>
                        </div>

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p data-bind="html: message, attr.class: messageClass"></p>
                        </div>

                    </form>

                </div>

                <div class="tab-pane" id="schools">

                    <form role="form" data-bind="submit: submit">

                        <h3>Education</h3>

                        <div data-bind="foreach: contents">

                            <div class="well well-sm">
                                Position {{ $index() + 1 }}
                                <a
                                        class="text-danger pull-right"
                                        data-bind="click: $parent.removeContent,
                                                   visible: $parent.canRemove"
                                    >Remove</a>
                            </div>

                            <div class="form-group">
                                <label>Institution</label>
                                <input class="form-control" data-bind="value: institution" />
                            </div>

                            <div class="form-group">
                                <label>Department</label>
                                <input class="form-control" data-bind="value: department" />
                            </div>

                            <div class="form-group">
                                <label>Degree</label>
                                <input class="form-control" data-bind="value: degree" />
                            </div>

                            <div class="form-group">
                                <label>Start Date</label>
                                <input class="form-control" data-bind="value: start" />
                            </div>

                            <div class="form-group">
                                <label>End Date</label>
                                <input class="form-control" data-bind="value: end" />
                            </div>

                            <hr data-bind="visible: $index() != ($parent.contents().length - 1)" />

                        </div>

                        <div>
                            <a class="btn btn-default" data-bind="click: addContent">
                                Add another
                            </a>
                        </div>

                        <div class="padded">
                            <button
                                    type="submit"
                                    class="btn btn-success"
                                    data-bind="enable: isValid"
                                >Submit</button>
                        </div>

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p data-bind="html: message, attr.class: messageClass"></p>
                        </div>

                    </form>

                </div>

            </div>

        </div>

    </div>

</div>

## TODO: Review and un-comment
##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "/api/v1/settings/keys/",
##        "replace": true,
##        "kwargs" : {
##            "route": "/settings/"}
##        }'></div>

<script type="text/javascript">

    $script(['/static/js/profile.js']);
    $script.ready('profile', function() {
        var nameUrls = {
            crud: '${ api_url_for('serialize_names') }',
            impute: '${ api_url_for('impute_names') }'
        };
        var socialUrls = {
            crud: '${ api_url_for('serialize_social') }'
        };
        var jobsUrls = {
            crud: '${ api_url_for('serialize_jobs') }'
        };
        var schoolsUrls = {
            crud: '${ api_url_for('serialize_schools') }'
        };
        var names = new profile.Names('#names', nameUrls);
        var social = new profile.Social('#social', socialUrls);
        var jobs = new profile.Jobs('#jobs', jobsUrls);
        var schools = new profile.Schools('#schools', schoolsUrls);
    });

</script>


</%def>
