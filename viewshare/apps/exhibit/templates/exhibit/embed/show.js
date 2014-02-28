{% load viewshare_helpers %}

window.Freemix = window.Freemix || {};

window.Freemix.profile = {{ metadata|safe }};

window.Freemix.data = {{ data|safe }};

window.Freemix.title = "{{ title|linebreaksbr|safe }}";

window.Freemix.description = "{{ description|linebreaksbr|safe }}";

window.Freemix.permalink = "{{ permalink }}";

window.Freemix.home = "{% site_url %}";

window.Freemix.homeName = "{{ SITE_NAME }}";

window.Freemix.prefix = "{% site_url "" %}{{ STATIC_URL }}";

var FreemixEmbed = {};

FreemixEmbed.insert = function(tag, type, attrs) {
    var ans = document.createElement(tag);
    ans.setAttribute('type', type);
    for (var attr in attrs) {
        ans.setAttribute(attr, attrs[attr]);
    }
    document.getElementsByTagName('head')[0].appendChild(ans);
};

FreemixEmbed.insertStyle = function(src) {
    FreemixEmbed.insert(
        'link',
        'text/css',
        { 'rel': 'stylesheet', 'href': src }
    );
};

(function() {
    {% include "exhibit/embed/js_file.html" %}
    {% include "exhibit/embed/embed_css.html" %}
}());
