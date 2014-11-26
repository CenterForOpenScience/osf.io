$script.ready(['rubeus'], function() {
//styles = new Bloodhound({
//    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('title'),
//    queryTokenizer: Bloodhound.tokenizers.whitespace,
//    remote: '/api/v1/citation_styles?q=%QUERY'
//});
//styles.initialize();

    var r = function(query) {
        query.callback({results: [
            {
                _id: "academy-of-management-review",
                summary: null,
                short_title: "AMR",
                title: "Academy of Management Review"
            }
        ]})
    }

    var formatResult = function(state) {
        var html = "<div class='citation-result-title'>" + state.title + "</div>";
        //if (state.short_title_!== null) {
        //    html += "<div class='citation-result-slug'>" + state.short_title + "</div>";
        //};
        //if (state.summary !== null) {
        //    html += "<div class='citation-result-summary'>" + state.summary + "</div>";
        //};
        return html;
    };

    var formatSelection = function(state) {
        console.log("Formatting Selection");
        return state.title;
    };

    var input = $('#citation-style-input');
    var citationElement = $('#citation-text');

    input.select2({
        allowClear: true,
        formatResult: formatResult,
        formatSelection: formatSelection,
        placeholder: 'Citation Style (e.g. "APA")',
        minimumInputLength: 1,
        ajax: {
            url: '/api/v1/citation_styles/',
            quietMillis: 200,
            data: function(term, page) {
                return {
                    'q': term
                }
            },
            results: function(data, page) {
                return {results: data.styles}
            },
            cache: true,
        }
    }).on('select2-selecting', function(e) {
        $.get(
            nodeApiUrl + 'citation/' + e.val,
            {},
            function(data) {
                citationElement.text(data.citation).slideDown();
            }
        );
    }).on('select2-removed', function (e) {
        citationElement.slideUp().text();
    });

})