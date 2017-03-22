/**
* Mithril component to show latest topic excerpts from the forum.
*/
'use strict';
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var utils = require('js/components/utils');
var required = utils.required;

require('css/forum-feed.css');

var ForumFeed = {
    controller: function(options) {
        var self = this;
        self.loading = true;
        self.failed = false;
        self.node = required(options, 'node');
        self.user = required(options, 'user');
        self.discourse_url = required(options, 'discourse_url');
        self.view_only = required(options, 'view_only');
        self.user_apikey = required(options, 'discourse_user_apikey');

        // Replace guids with names in @mentions, and make relative urls absolute
        var fixTopicExcerpt = function(topic) {
            if (!topic.excerpt) {
                topic.excerpt = '';
                return;
            }
            var excerpt = topic.excerpt;
            var mentions = topic.excerpt.match(/@[a-z0-9]+/g);
            if (mentions) {
                mentions.forEach(function(mention) {
                    var username = mention.substr(1);
                    if (self.usernamesToNames[username]) {
                        excerpt = excerpt.replace(mention, '@' + self.usernamesToNames[username]);
                        excerpt = excerpt.replace('href="/users', 'href="' + self.discourse_url + 'users');
                    }
                });
                topic.excerpt = excerpt;
            }
        };

        var requestUrl = self.discourse_url + 'forum/' + self.node.id + '/latest.json';
        var data;
        if (self.view_only) {
            data = { view_only: self.view_only };
        } else {
            data = { api_key: self.user_apikey, api_username: self.user.id };
        }
        m.request({method : 'GET', url : requestUrl, data: data}).then(function(results) {
            self.topics = results.topic_list.topics;
            // Collect guid and name pairs so we can translate guids to names
            self.usernamesToNames = {};
            var addGuidNamePair = function(user) {
                self.usernamesToNames[user.username] = user.name;
            };

            results.users.forEach(addGuidNamePair);
            self.topics.forEach(function(topic) {
                if (topic.excerpt_mentioned_users) {
                    topic.excerpt_mentioned_users.forEach(addGuidNamePair);
                }
            });
            results.topic_list.contributors.forEach(addGuidNamePair);

            self.topics.forEach(fixTopicExcerpt);
            self.loading = false;
        }, function(xhr, textStatus, error) {
            self.failed = true;
            self.loading = false;
            var message = 'Error retrieving latest forum topics for ' + self.node.id;
            Raven.captureMessage(message, {extra: {url: requestUrl, textStatus: textStatus, error: error}});
        });
    },
    view: function(ctrl, options) {
        var self = this;
        var queryString = $osf.urlParams().view_only;
        queryString = queryString ? '?view_only=' + queryString : '';

        var contentForTopic = function(topic)  {
            var postNumber = topic.highest_post_number;
            if (topic.last_read_post_number) {
                postNumber = Math.min(topic.last_read_post_number + 1, topic.highest_post_number);
            }
            var postUrl = ctrl.discourse_url + 't/' + topic.slug + '/' + topic.id + '/' + postNumber + queryString;
            var projectUrl = ctrl.discourse_url + 'forum/' + topic.project_guid + queryString;
            return m('tr',
                m('td', [
                    m('a.title', {href: postUrl}, topic.fancy_title),
                    m('div.osf-parent-project',
                        m('a', {href: projectUrl}, topic.project_name)
                    ),
                    m('div.topic-excerpt', m.trust(topic.excerpt))
                ])
            );
        };

        var forumFeedContent;
        if (ctrl.failed) {
            forumFeedContent = m('p', [
                'Unable to retrieve forum topics at this time. Please refresh the page or contact ',
                m('a', {'href': 'mailto:support@osf.io'}, 'support@osf.io'),
                ' if the problem persists.'
            ]);
        } else if (ctrl.loading) {
            forumFeedContent = m('.spinner-loading-wrapper', [
                m('.logo-spin.logo-lg'),
                m('p.m-t-sm.fg-load-message', 'Loading forum topics...')
            ]);
        } else {
            forumFeedContent = m('table', m('tbody', ctrl.topics.slice(0, 5).map(contentForTopic)));
        }

        return m('div.forum-feed ', forumFeedContent);
    }
};

module.exports = {
    ForumFeed: ForumFeed,
};
