importScripts('https://www.gstatic.com/firebasejs/4.8.0/firebase.js');
firebase.initializeApp({
  'messagingSenderId': '340702114761'
});

var rdmGettext = require('js/rdmGettext');
var gt = rdmGettext.rdmGettext();
var _ = function(msgid) { return gt.gettext(msgid); };

const messaging = firebase.messaging();
messaging.setBackgroundMessageHandler(function(payload) {
  // Customize notification here
  const notificationTitle = _('RDM Announcements');
  const notificationOptions = {
    body: _('Background Message body.'),
    icon: '/static/public/css/images/firebase-logo.png'
  };

  return self.registration.showNotification(notificationTitle,
      notificationOptions);
});

