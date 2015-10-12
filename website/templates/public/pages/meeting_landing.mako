<%inherit file="base.mako"/>

<%def name="title()">Meetings</%def>

<%def name="content()">

    <div class="row">
        <div class="col-md-12">

            <h1 class="text-center">OSF for Meetings</h1>

            <p>
                The OSF can host posters and talks for scholarly meetings.
                Submitting a presentation is easy—just send an email to the conference
                address, and we'll create an OSF project for you. You'll get a permanent
                link to your presentation, plus analytics about who has viewed and
                downloaded your work.
            </p>
            <p>
                OSF for Meetings is a product that we offer to
                academic conferences at no cost. To request poster and talk hosting
                for a conference, email us at
                <a href="mailto:contact@cos.io">contact@cos.io</a>. We'll review
                and add your conference within one business day.
            </p>

            <div role="tabpanel">
                <!-- Nav tabs -->
                <ul class="nav nav-tabs m-b-md" role="tablist">
                    <li role="presentation" class="active">
<<<<<<< HEAD
                        <a href="#meetings" aria-controls="meetings" role="tab" data-toggle="tab">All meetings</a>
                    </li>
                    <li role="presentation">
                        <a href="#submissions" aria-controls="submissions" role="tab" data-toggle="tab">All submissions</a>
=======
                        <a href="#meetings" aria-controls="meetings" role="tab" data-toggle="tab">All Meetings</a>
                    </li>
                    <li role="presentation">
                        <a href="#submissions" aria-controls="submissions" role="tab" data-toggle="tab">All Submissions</a>
>>>>>>> 91d28b170401de7fdf8ee333cb3e5d44d3071aac
                    </li>
                </ul>
                <!-- Tab panes -->
                <div class="tab-content">
                    <div role="tabpanel" class="tab-pane active" id="meetings">
                        <p>
                            <small>Only conferences with at least five submissions are displayed here.</small>
                        </p>
                        <div id="meetings-grid"></div>
                    </div>
                    <div role="tabpanel" class="tab-pane" id="submissions">
                        <div id="submissions-grid"></div>
                    </div>
                </div>
            </div>

        </div>
    </div>

</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = window.contextVars || {};
        window.contextVars.meetings = ${meetings | sjson, n};
        window.contextVars.submissions = ${submissions | sjson, n};
    </script>
    <script src=${"/static/public/js/meetings-page.js" | webpack_asset}></script>
</%def>
