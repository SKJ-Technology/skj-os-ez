// SKJ OS EZ defaults for Firefox (default prefs: users can still change them).
//
// Firefox loads defaults/preferences/*.js so that the alphabetically first
// file has the last word; the 00- prefix makes these win over Fedora's
// firefox-redhat-default-prefs.js.

// Firefox's own start page instead of start.fedoraproject.org
pref("browser.startup.homepage", "about:home");

// New profiles import this file instead of the bookmarks built into Fedora's
// Firefox (only on first run; existing bookmarks are never touched).
pref("browser.bookmarks.file", "/usr/share/skj/firefox/bookmarks.html");
