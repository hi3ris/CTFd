CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function() {};
CTFd._internal.challenge.render = null;

// After CTFd renders the challenge modal, inject the instance control panel and
// wire it to the team_instancer routes. The flag is still submitted through the
// normal attempt form (the team_hmac flag class validates it).
CTFd._internal.challenge.postRender = function() {
  var $ = CTFd.lib.$;
  var id = parseInt($("#challenge-id").val());
  var base = "/plugins/team_instancer";

  if ($("#ti-panel").length === 0) {
    $(".challenge-desc").after(
      '<div id="ti-panel" class="mt-3 mb-3 p-2" style="border:1px solid #4443;border-radius:6px">' +
      '<div id="ti-status" class="mb-2 small text-muted">Instance : inconnue</div>' +
      '<button id="ti-spawn" class="btn btn-sm btn-success">Démarrer mon instance</button> ' +
      '<button id="ti-renew" class="btn btn-sm btn-secondary" style="display:none">Prolonger</button> ' +
      '<button id="ti-destroy" class="btn btn-sm btn-danger" style="display:none">Arrêter</button>' +
      '<div id="ti-conn" class="mt-2" style="display:none"><code></code></div>' +
      '</div>'
    );
  }

  function render(r) {
    var s = $("#ti-status"), conn = $("#ti-conn");
    if (!r || r.status === "none" || r.success === false) {
      s.text(r && r.error ? r.error : "Aucune instance active.");
      $("#ti-spawn").show(); $("#ti-renew").hide(); $("#ti-destroy").hide(); conn.hide();
      return;
    }
    var mins = Math.floor((r.remaining || 0) / 60);
    s.text("Instance " + r.status + " — expire dans " + mins + " min");
    $("#ti-spawn").hide(); $("#ti-renew").show(); $("#ti-destroy").show();
    if (r.connection) {
      conn.find("code").text(r.connection.host + ":" + r.connection.port);
      conn.show();
    }
  }

  function post(path, cb) {
    CTFd.fetch(base + path, {
      method: "POST",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ challenge_id: id })
    }).then(function(r){ return r.json(); }).then(cb);
  }

  $("#ti-spawn").off("click").on("click", function(){
    $("#ti-status").text("Démarrage…"); post("/spawn", render);
  });
  $("#ti-renew").off("click").on("click", function(){ post("/renew", function(){ refresh(); }); });
  $("#ti-destroy").off("click").on("click", function(){ post("/destroy", render); });

  function refresh() {
    CTFd.fetch(base + "/status?challenge_id=" + id, { headers: { "Accept": "application/json" } })
      .then(function(r){ return r.json(); }).then(render);
  }
  refresh();
};

CTFd._internal.challenge.submit = function(preview) {
  var $ = CTFd.lib.$;
  var challenge_id = parseInt($("#challenge-id").val());
  var submission = $("#challenge-input").val();
  var body = { challenge_id: challenge_id, submission: submission };
  var params = {};
  if (preview) { params["preview"] = true; }
  return CTFd.api.post_challenge_attempt(params, body).then(function(response) {
    return response;
  });
};
