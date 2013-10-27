<div class="comment-container">

    <a class="btn comment-reply">
        % if top:
            Comment
        % else:
            Reply
        % endif
    </a>

    <!-- Build comment form -->
    <form id="comment-${guid}" method="POST" action="/api/v1/guid/${guid}/comment/" class="comment-form form-horizontal" style="display: none;">

        <div data-bind="with:currentPage">
            <div data-bind="foreach:questions">
                <div class="control-group">
                    <label class="control-label" data-bind="text:$data.label, attr:{for:$data.id}"></label>
                    <div class="controls">
                        <div data-bind='item:$data, attr:{id:$data.id}'></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="control-group">
            <div class="controls">
                <input type="submit" value="Submit" class="btn" />
                <a class="btn comment-cancel">Cancel</a>
            </div>
        </div>

    </form>

</div>

<!-- Apply view model -->
<script type="text/javascript">
    view_model = new ViewModel(${schema});
    ko.applyBindings(view_model, $('#comment-${guid}')[0]);
</script>
