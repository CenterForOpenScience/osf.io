// based on PHP Name Parser by Josh Fraser (joshfraser.com)
// http://www.onlineaspect.com/2009/08/17/splitting-names/
// ported to JavaScript by Mark Pemburn (pemburnia.com)
// released under Apache 2.0 license

Array.prototype.in_array = function (value) {
    for (var i = 0; i < this.length; i++) {
        if (this[i] == value) {
            return true;
        }
    }
    return false;
};
Array.prototype.implode = function (separator) {
    var output = "";
    var sep = "";
    for (var i = 0; i < this.length; i++) {
        output += sep + this[i];
        sep = separator;
    }
    return output;
};
if (!String.prototype.trim) {
  String.prototype.trim = function () {
    return this.replace(/^\s+|\s+$/gm, '');
  };
}
String.prototype.ucfirst = function() {
    return this.substr(0,1).toUpperCase() + this.substr(1,this.length - 1).toLowerCase();
};

function NameParse() {
	var me = this;

	// split full names into the following parts:
	// - prefix / salutation  (Mr., Mrs., etc)
	// - given name / first name
	// - middle initials
	// - surname / last name
	// - suffix (II, Phd, Jr, etc)
	NameParse.prototype.parse = function (fullastName) {
		fullastName = fullastName.trim();
		// split into words
		var unfilteredNameParts = fullastName.split(" ");
		var name = {};
		var nameParts = [];
		var lastName = "";
		var firstName = "";
		var initials = "";
		var j = 0;
		var i = 0;
		// completely ignore any words in parentheses
		for (i=0; i<unfilteredNameParts.length; i++) {
			if (unfilteredNameParts[i].indexOf("(") == -1) {
				nameParts[j++] = unfilteredNameParts[i];
			}
		}
		var numWords = nameParts.length;
		// is the first word a title? (Mr. Mrs, etc)
		var salutation = me.is_salutation(nameParts[0]);
		var suffix = me.is_suffix(nameParts[nameParts.length - 1]);
		// set the range for the middle part of the name (trim prefixes & suffixes)
		var start = (salutation) ? 1 : 0;
		var end = (suffix) ? numWords - 1 : numWords;

		// concat the first name
		for (i=start; i<(end - 1); i++) {
			word = nameParts[i];
			// move on to parsing the last name if we find an indicator of a compound last name (Von, Van, etc)
			// we use i != start to allow for rare cases where an indicator is actually the first name (like "Von Fabella")
			if (me.is_compound_lastName(word) && i != start) {
				break;
			}
			// is it a middle initial or part of their first name?
			// if we start off with an initial, we'll call it the first name
			if (me.is_initial(word)) {
				// is the initial the first word?
				if (i == start) {
					// if so, do a look-ahead to see if they go by their middle name
					// for ex: "R. Jason Smith" => "Jason Smith" & "R." is stored as an initial
					// but "R. J. Smith" => "R. Smith" and "J." is stored as an initial
					if (me.is_initial(nameParts[i + 1])) {
						firstName += " " +  word.toUpperCase();
					} else {
						initials += " " +  word.toUpperCase();
					}
				// otherwise, just go ahead and save the initial
				} else {
					initials += " " +  word.toUpperCase();
				}
			} else {
				firstName += " " + me.fix_case(word);
			}
		}

		// check that we have more than 1 word in our string
		if ((end - start) > 1) {
			// concat the last name
			for (j=i; j<end; j++) {
				lastName += " " + me.fix_case(nameParts[j]);
			}
		} else {
			// otherwise, single word strings are assumed to be first names
			firstName = me.fix_case(nameParts[i]);
		}

		// return the various parts in an array
		name.salutation = (salutation != false) ? salutation : "";
		name.firstName = (firstName != "") ? firstName.trim() : "";
		name.initials = (initials != "") ? initials.trim() : "";
		name.lastName = (lastName != "") ? lastName.trim() : "";
		name.suffix = (suffix != false) ? suffix : "";

		return name;
	};

	// detect and format standard salutations
	// I'm only considering english honorifics for now & not words like
	this.is_salutation = function (word) {
		// ignore periods
		word = word.replace(".","").toLowerCase();
		// returns normalized values
		if (word == "mr" || word == "master" || word == "mister") {
			return "Mr.";
		} else if (word == "mrs") {
			return "Mrs.";
		} else if (word == "miss" || word == "ms") {
			return "Ms.";
		} else if (word == "dr") {
			return "Dr.";
		} else if (word == "rev") {
			return "Rev.";
		} else if (word == "fr") {
			return "Fr.";
		} else {
			return false;
		}
	};

	//  detect and format common suffixes
	this.is_suffix = function (word) {
		// ignore periods
		word = word.replace(/\./g,"").toLowerCase();
		// these are some common suffixes - what am I missing?
		var suffixArray = ['I','II','III','IV','V','Senior','Junior','Jr','Sr','PhD','APR','RPh','PE','MD','MA','DMD','CME'];
		for (var i=0; i<suffixArray.length; i++) {
			if (suffixArray[i].toLowerCase() == word) {
				return suffixArray[i];
			}
		}
		return false;
	};

	// detect compound last names like "Von Fange"
	this.is_compound_lastName = function (word) {
		word = word.toLowerCase();
		// these are some common prefixes that identify a compound last names - what am I missing?
		var words = ['vere','von','van','de','del','della','di','da','pietro','vanden','du','st.','st','la','lo','ter'];
		return words.in_array(word);
	};

	// single letter, possibly followed by a period
	this.is_initial = function (word) {
		// ignore periods
		word = word.replace(".","");
		return (word.length == 1);
	};

	// detect mixed case words like "McDonald"
	// returns false if the string is all one case
	this.is_camel_case = function (word) {
		var ucReg = /|[A-Z]+|s/;
		var lcReg = /|[a-z]+|s/;
		return (word.match(ucReg) != null && word.match(lcReg) != null);
	};

	// ucfirst words split by dashes or periods
	// ucfirst all upper/lower strings, but leave camelcase words alone
	this.fix_case = function (word) {
		// uppercase words split by dashes, like "Kimura-Fay"
		word = me.safe_ucfirst("-",word);
		// uppercase words split by periods, like "J.P."
		word = me.safe_ucfirst(".",word);
		return word;
	};

	// helper this.for fix_case
	this.safe_ucfirst = function (seperator, word) {
		var words = [];
		// uppercase words split by the seperator (ex. dashes or periods)
		parts = word.split(seperator);
		for (var i=0; i<parts.length; i++) {
			var thisWord = parts[i];
			words[i] = (me.is_camel_case(thisWord)) ? thisWord : thisWord.ucfirst.toLowerCase();
		}
		return words.implode(seperator);
	};
}