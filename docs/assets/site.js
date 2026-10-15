// Shared header, menu and footer. Each page includes:
//   <div id="site-header"></div><script src="assets/site.js" data-root=""></script>
//   ... page ...
//   <div id="site-footer"></div>
// data-root is the path back to the site's top folder ("" or "../").
(function () {
  var me = document.currentScript;
  var root = (me && me.dataset.root) || "";
  var section = document.body.dataset.section || "";
  var LINKS = {
    leadForm: "https://www.leadmanagementlab.com/Form.aspx?id=b9f88dcd-0046-43a9-9866-7195957a39b6",
    facebook: "https://www.facebook.com/aaron.simac"
  };
  window.SITE = LINKS;

  var menu = [
    ["articles", "", "Articles", "Research, myth checks, arguments"],
    ["live", "live/", "Live", "Updates every morning in season"],
    ["about", "about/", "About", "Who's doing this, and why"],
    ["harold", "harold/", "What's a Harold?", "Our unit of a very good career"],
    ["how", "how/", "How We Do This", "Cutoffs, sources, definitions"]
  ];

  var head = document.getElementById("site-header");
  if (head) {
    head.outerHTML =
      '<header class="site-top gut"><div class="col">' +
      '<div class="site-bar">' +
      '<a class="site-brand" href="' + (root || "./") + '"><b>Sox Fan. Stat Fan.</b><span>Just an insurance guy with a spreadsheet.</span></a>' +
      '<button class="site-menubtn" id="site-menubtn" aria-expanded="false" aria-controls="site-drawer"><i><span></span></i>Menu</button>' +
      '</div>' +
      '<nav class="site-drawer" id="site-drawer" hidden>' +
      menu.map(function (m) {
        return '<a href="' + (root + m[1] || "./") + '"' + (m[0] === section ? ' aria-current="page"' : "") +
          '><b>' + m[2] + '</b><small>' + m[3] + '</small></a>';
      }).join("") +
      '</nav></div></header>';
    var btn = document.getElementById("site-menubtn"), drawer = document.getElementById("site-drawer");
    btn.addEventListener("click", function () {
      drawer.hidden = !drawer.hidden;
      btn.setAttribute("aria-expanded", String(!drawer.hidden));
    });
  }

  function foot() {
    var f = document.getElementById("site-footer");
    if (!f) return;
    f.outerHTML =
      '<footer class="site-foot gut"><div class="col">' +
      '<div class="links">' + menu.map(function (m) { return '<a href="' + (root + m[1] || "./") + '">' + m[2] + '</a>'; }).join("") + '</div>' +
      '<p>A fan site. Not affiliated with the Chicago White Sox or Major League Baseball. Stats from MLB and Baseball-Reference.</p>' +
      '<p>Aaron Simac Insurance, Indiana and Illinois. <a href="' + LINKS.leadForm + '" target="_blank" rel="noopener">Get a coverage review</a></p>' +
      '</div></footer>';
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", foot); else foot();
})();
