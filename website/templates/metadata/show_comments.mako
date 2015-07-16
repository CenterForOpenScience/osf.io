## TODO: Only seems to be referenced in comment_group.mako. Is this deprecated?

% if comments:

    <div class="accordion-header">

        <h2>
            <a
                    data-toggle="collapse"
                    data-parent="#comments-${guid}"
                    href="#comments-inner-${guid}"
                >Comments</a>
        </h2>

        <div id="comments-inner-${guid}" class="accordion-body collapse in">

            % for comment in comments:

                <!-- The comment -->
                <div>
                    <div>${comment['user_fullname']} at ${comment['date']}</div>
                    <div>${comment['payload']['comment']}</div>
                </div>

                <!-- Comments on the comment -->
                <div>

                    <div mod-meta='{
                            "tpl": "metadata/comment_group.mako",
                            "kwargs": {
                                "guid": "${comment['comment_id']}",
                                "top": false
                            },
                            "replace": true
                        }'></div>

                </div>

                <hr />

            % endfor

        </div>

    </div>

% endif
