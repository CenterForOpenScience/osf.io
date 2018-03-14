<h2 style="padding-bottom: 30px;">
  ${ meeting['name'] }
</h2>

% if meeting['location']:
   <span>${meeting['location']}</span>
% endif
% if meeting['location'] and meeting['start_date']:
    |
% endif
% if meeting['start_date']:
    <span>${meeting['start_date'].strftime('%b %d, %Y')}</span>
    %if meeting['end_date']:
        - <span>${meeting['end_date'].strftime('%b %d, %Y')}</span>
    %endif
% endif

% if meeting['logo_url']:
    <img src="${ meeting['logo_url'] }" class="img-responsive" />
    <br /><br />
  % endif

% if meeting['active']:
    <div>
        <a id="addLink" onclick="" href="#">${('Add your ' + meeting['field_names']['add_submission']) if meeting['poster'] and meeting['talk'] else ('Add your ' + meeting['field_names']['submission1_plural']) if meeting['poster'] else ('Add your ' + meeting['field_names']['submission2_plural'])}</a>

        % if meeting['info_url']:
          | <a href="${ meeting['info_url'] }">${meeting['field_names'].get('homepage_link_text', 'Conference homepage')}</a>
        % endif
    </div>

    <div style="display: none" id="submit">
        <h3>${('Add your ' + meeting['field_names']['add_submission']) if meeting['poster'] and meeting['talk'] else ('Add your ' + meeting['field_names']['submission1_plural']) if meeting['poster'] else ('Add your ' + meeting['field_names']['submission2_plural'])}</h3>
        <p>
            Send an email to the following address(es) from the email
            account you would like used on the OSF:
        </p>
        <ul>
            % if meeting['poster']:
                <li>For ${meeting['field_names']['submission1_plural']}, email <a href="mailto:${ label }-${meeting['field_names']['submission1']}@osf.io">${ label }-${meeting['field_names']['submission1']}@osf.io</a></li>
            % endif
            % if meeting['talk']:
                <li>For ${meeting['field_names']['submission2_plural']}, email <a href="mailto:${ label }-${meeting['field_names']['submission2']}@osf.io">${ label }-${meeting['field_names']['submission2']}@osf.io</a></li>
            % endif
        </ul>
        <p>The format of the email should be as follows:</p>
        <div>
            <dl style="padding-left: 25px">
                <dt>Subject</dt>
                <dd>${meeting['field_names']['mail_subject']}</dd>
                <dt>Message body</dt>
                <dd>${meeting['field_names']['mail_message_body']}</dd>
                <dt>Attachment</dt>
                <dd>${meeting['field_names']['mail_attachment']}</dd>
            </dl>
        </div>
        <p>
            Once sent, we will follow-up by sending you the permanent identifier
            that others can use to cite your work; you can also login and make changes,
            such as uploading additional files, to your project at that URL. If you
            didn't have an OSF account, one will be created automatically and a link
            to set your password will be emailed to you; if you do, we will simply create
            a new project in your account. By creating an account you agree to our
            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/TERMS_OF_USE.md">Terms</a>
            and that you have read our
            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>,
            including our information on
            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md#f-cookies">Cookie Use</a>.
        </p>
    </div>
% endif

<div class="tb-head">
    <div class="tb-head-filter col-xs-12 col-sm-6 col-sm-offset-6">
        <form id="meetingsFilter" method="GET">
            <input type="hidden" name="page" value="1">
            <input id="filterAttachments" placeholder="Search" value="${ q }" name="q" type="text" style="width:100%;display:inline;" class="pull-right form-control">
            <input type="hidden" name="sort" value="${ sort }">
        </form>
    </div>
</div>

<div style="width: 100%;">
    <div class="gridWrapper">
        <div style="width:auto;" class="tb-table">
            <div class="tb-row-titles" id="meetingFiltering">
                <div class="tb-th" data-tb-th-col="0" style="width: 49%;">
                    <span class="m-r-sm">Title</span>
                    <span data-bind="foreach: titleFilters">
                        <a data-bind="attr: {href: $data.href}"><i data-bind="css: filterCSS" class="fa"></i></a>
                    </span>
                </div>
                <div class="tb-th" data-tb-th-col="1" style="width: 9%">
                    <span class="m-r-sm">Author</span>
                    <span data-bind="foreach: authorFilters">
                        <a data-bind="attr: {href: $data.href}"><i data-bind="css: filterCSS" class="fa"></i></a>
                    </span>
                </div>
                <div class="tb-th" data-tb-th-col="2" style="width: 11%">
                    <span class="m-r-sm">Category</span>
                    <span data-bind="foreach: categoryFilters">
                        <a data-bind="attr: {href: $data.href}"><i data-bind="css: filterCSS" class="fa"></i></a>
                    </span>
                </div>
                <div class="tb-th" data-tb-th-col="3" style="width: 14%">
                    <span class="m-r-sm">Date Created</span>
                    <span data-bind="foreach: createdFilters">
                        <a data-bind="attr: {href: $data.href}"><i data-bind="css: filterCSS" class="fa"></i></a>
                    </span>
                </div>
                <div class="tb-th" data-tb-th-col="4" style="width: 13%">
                    <span class="m-r-sm">Downloads</span>
                    <span data-bind="foreach: downloadsFilters">
                        <a data-bind="attr: {href: $data.href}"><i data-bind="css: filterCSS" class="fa"></i></a>
                    </span>
                </div>
            </div>
        </div>
    </div>
</div>

% if not data:
    <div class="tb-no-results" style="border-left:1px solid #eee; border-right: 1px solid #eee;">
        No results found for this search term.
    </div>
% endif

<div id="grid" style="width:100%; height:500px;">
    <div class="spinner-loading-wrapper">
        <div class="ball-scale ball-scale-blue">
            <div></div>
        </div>
    </div>
</div>

% if page.has_other_pages():
    <div class="pull-right">
        <ul id="meetingPagination" class="pagination" data-bind="foreach: pagination">
            <li class="active" data-bind="if: $data.isCurrent"><span data-bind='text:$data.page'><span class="sr-only">(current)</span></span></li>
            <li class="disabled" data-bind="if: $data.isDisabled"> <span data-bind='text:$data.page'><span> </li>
            <li data-bind="if: $data.href"><a data-bind="attr: {href: $data.href}, text:$data.page"></a></li>
        </ul>
    </div>
% endif
