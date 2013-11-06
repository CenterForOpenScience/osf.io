
function attrMap(list, attr) {
    return $.map(list, function(item) {
        return item[attr];
    });
}

NODE_OFFSET = 25;

var addContributorModel = function(title, parentId, parentTitle) {

    var self = this;

    self.title = title;
    self.parentId = parentId;
    self.parentTitle = parentTitle;

    self.page = ko.observable('whom');
    self.pageTitle = ko.computed(function() {
        return {
            whom: 'Add contributors',
            which: 'Select components'
        }[self.page()];
    });

    self.query = ko.observable();
    self.results = ko.observableArray();
    self.selection = ko.observableArray();

    self.nodes = ko.observableArray([]);
    self.nodesToChange = ko.observableArray();
    $.getJSON(
        nodeToUseUrl() + '/get_editable_children/',
        {},
        function(result) {
            $.each(result['children'], function(idx, child) {
                child['margin'] = NODE_OFFSET + child['indent'] * NODE_OFFSET + 'px';
            });
            self.nodes(result['children']);
        }
    );

    self.selectWhom = function() {
        self.page('whom');
    };
    self.selectWhich = function() {
        self.page('which');
    };

    self.search = function() {
        $.getJSON(
            '/api/v1/user/search/',
            {query: self.query()},
            function(result) {
                self.results(result['users']);
            }
        )
    };

    self.importFromParent = function() {
        $.getJSON(
            nodeToUseUrl() + '/get_contributors_from_parent/',
            {},
            function(result) {
                self.results(result['contributors']);
            }
        )
    };

    self.addTips = function(elements) {
        elements.forEach(function(element) {
            $(element).find('.contrib-button').tooltip();
        });
    };

    self.add = function(data) {
        self.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.remove = function(data) {
        self.selection.splice(
            self.selection.indexOf(data), 1
        );
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.addAll = function() {
        $.each(self.results(), function(idx, result) {
            if (!(result in self.selection())) {
                self.add(result);
            }
        });
    };

    self.removeAll = function() {
        $.each(self.selection(), function(idx, selected) {
            self.remove(selected);
        });
    };

    self.cantSelectNodes = function() {
        return self.nodesToChange().length == self.nodes().length;
    };
    self.cantDeselectNodes = function() {
        return self.nodesToChange().length == 0;
    };

    self.selectNodes = function() {
        self.nodesToChange(attrMap(self.nodes(), 'id'));
    };
    self.deselectNodes = function() {
        self.nodesToChange([]);
    };

    self.selected = function(data) {
        for (var idx=0; idx < self.selection().length; idx++) {
            if (data.id == self.selection()[idx].id)
                return true;
        }
        return false;
    };

    self.addingSummary = ko.computed(function() {
        var names = $.map(self.selection(), function(result) {
            return result.fullname
        });
        return names.join(', ');
    });

    self.submit = function() {
        var user_ids = attrMap(self.selection(), 'id');
        $.ajax(
            nodeToUseUrl() + '/addcontributors/',
            {
                type: 'post',
                data: JSON.stringify({
                    user_ids: user_ids,
                    node_ids: self.nodesToChange()
                }),
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    if (response.status === 'success') {
                        window.location.reload();
                    }
                }
            }
        )
    };

    self.clear = function() {
        self.page('whom');
        self.query('');
        self.results([]);
        self.selection([]);
        self.nodesToChange([]);
    };

};
