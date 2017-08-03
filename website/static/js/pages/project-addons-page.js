'use strict';
var $ = require('jquery');

var filterAddons = function(event) {
    var input = document.getElementById('filter-addons');
    var filter = input.value.toUpperCase();
    var containers = document.getElementsByClassName('addon-container');
    var active_category;
    if(event.target.localName === 'input'){
        active_category =  document.querySelectorAll('.addon-categories.active')[0].getAttribute('name');
    } else {
        active_category = event.target.getAttribute('name');
    }
    for (var i = 0; i < containers.length; i++) {
        if (containers[i].getAttribute('name').toUpperCase().indexOf(filter) > -1 &&
                (containers[i].getAttribute('categories').toUpperCase().indexOf(active_category.toUpperCase()) > -1 ||
                active_category === 'All' ))
        {
            containers[i].style.display = '';
        } else {
            containers[i].style.display = 'none';
        }
    }
};

$('#filter-addons').keyup(filterAddons);
$('.addon-categories').click(filterAddons);
