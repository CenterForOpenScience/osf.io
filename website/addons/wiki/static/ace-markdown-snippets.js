ace.define("ace/snippets/markdown",["require","exports","module"], function(require, exports, module) {
"use strict";

//    Important: In the body of each snippet, the white spaces is a tab, not a series of spaces, and is required.

exports.snippetText = "# Markdown\n\
\n\
snippet font-italic\n\
	*${1:text}*\n\
\n\
snippet font-bold\n\
	**${1:text}**\n\
\n\
snippet math-inline\n\
	\$${1:text}\$\n\
snippet heading-1\n\
	\n\
	# ${1:title}\n\
\n\
snippet heading-2\n\
	\n\
	## ${1:title}\n\
\n\
snippet heading-3\n\
	\n\
	### ${1:title}\n\
\n\
snippet heading-4\n\
	\n\
	#### ${1:title}\n\
\n\
snippet horizontal-rule\n\
	\n\
	---\n\
	\n\
\n\
snippet blockquote\n\
	\n\
	> ${1:quote}\n\
\n\
snippet codeblock\n\
	\n\
	```\n\
	${1:snippet}\n\
	```\n\
\n\
snippet ![ (image)\n\
snippet image\n\
	![${1:alttext}](${2:url} \"${3:title}\")\n\
\n\
snippet [ (hyperlink)\n\
snippet hyperlink\n\
	[${1:linktext}](${2:url} \"${3:title}\")\n\
\n\
snippet numbered-list\n\
	\n\
	1. ${1:item}\n\
\n\
snippet bulleted-list\n\
	\n\
	* ${1:item}\n\
\n\
snippet video\n\
	\n\
	@[${1:service}](${2:url})\n\
\n\
snippet youtube-video\n\
	\n\
	@[youtube](${1:url})\n\
\n\
snippet vimeo-video\n\
	\n\
	@[vimeo](${1:url})\n\
\n\
snippet table-of-contents\n\
	\n\
	@[toc](${1:optional_label})\n\
\n\
";
exports.scope = "markdown";

});
