<%inherit file="base.mako"/>

<%def name="title()">Conferences</%def>

<%def name="content()">

    <div class="row">

        <div class="col-md-8 col-md-offset-2">

            <h1>Presentation Submission Service</h1>

            <p>
                The OSF can host posters and talks for scholarly meetings.
                Submitting a presentation is easy—just send an email to the conference
                address, and we'll create an OSF project for you. You'll get a permanent
                link to your presentation, plus analytics about who has viewed and
                downloaded your work.
            </p>

            <p>
                The Presentation Submission Service is a product that we offer to
                academic conferences at no cost. To request poster and talk hosting
                for a conference, email us at
                <a href="mailto:contact@cos.io">contact@cos.io</a>. We'll review
                and add your conference within one business day.
            </p>

            <p>
                <small>Only conferences with at least five submissions are displayed here.</small>
            </p>

            <table class="table table-striped" id="conferenceViewTable">
                <tbody>
                % for meeting in meetings:
                    <tr>
                        <td>
                            <div style="font-size: 18px; font-weight: bold;">
                                <a href="${meeting['url']}">
                                    ${meeting['name']}
                                </a>
                            </div>
                            <span
                                % if not meeting['active']:
                                    style="color: grey;"
                                % endif
                                >
                                ${'Not a' if not meeting['active'] else 'A'}ccepting submissions
                            </span>
                        </td>
                        <td>${meeting['submissions']} submission(s)</td>
                    </tr>
                % endfor
                </tbody>
            </table>

        </div>

    </div>

</%def>
