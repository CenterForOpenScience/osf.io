'use strict';

var $ = require('jquery');
require('./dryad-node-config.js');
var bootbox = require('bootbox');
var AddonHelper = require('js/addonHelper');


    $(document).ready(function() {

        $('#dryadsubmitkey').on('click', function() {
        	var doi = $('#dryaddoitext').val();

            var check_url = $(dryad_check_url).val();
            var add_url = $(dryad_add_url).val();
        	var doi_response = $.ajax({
	    		type: "GET",   
    			url: check_url,   
                data: {'doi' : doi},
			    success : function(response) {
			        if(response =="True"){

                    $.ajax({
                        type: "GET",   
                        url: add_url,   
                        data: {'doi' : doi},
                        success : function(response) {
                        bootbox.alert("Successfully added  "+doi+" to project.");
                        }
                    });


                    }
                    else{
                        bootbox.alert("Failed to add DOI: "+doi+" to project. DOIs come in the form doi:10.5061/dryad.XXXX.");
                    }
			    }
			});

        });

    });

$(window.contextVars.dryadSettingsSelector).on('submit', AddonHelper.onSubmitSettings);
