# Audit du thème `hibris` — NCTF

Deux passes indépendantes (modèle **fable**) : **sécurité** (XSS/injection, CSRF, ressources externes) et **UX/qualité** (scoreboard kart, responsive, accessibilité, cohérence CTFd 3.8.7, i18n). Les 4 findings HIGH ont été re-vérifiés à la main contre les fichiers source (voir la note _vérifié_).

## Synthèse

| passe      | 🔴 crit | 🟠 high | 🟡 med | 🔵 low | ⚪ info | total  |
| ---------- | ------- | ------- | ------ | ------ | ------- | ------ |
| sécurité   | 0       | 0       | 2      | 3      | 9       | 14     |
| UX/qualité | 0       | 4       | 7      | 9      | 3       | 23     |
| **total**  | **0**   | **4**   | **9**  | **12** | **12**  | **37** |

**Verdict :** aucune XSS atteignable par un joueur (noms d'équipe/joueur échappés, scoreboard kart sûr). Mais **4 HIGH UX bloquants pour l'événement**, chacun corrigeable en une ligne / un bloc. Correctifs prioritaires ci-dessous.

## Correctifs prioritaires (high + medium)

### 🟠 high · FontAwesome and offline fonts never loaded: css/fonts.css link was dropped

- **Où :** `CTFd/themes/hibris/templates/base.html`:17
- **Passe :** UX/qualité · catégorie bug/assets
- **Problème :** core-deprecated base.html links css/fonts.css before main.css; hibris removed it. The .fas/.fa-_ icon classes and every @font-face (Font Awesome 5 Free/Brands, Lato/Raleway offline) exist ONLY in static/css/fonts.dev.css (main.dev.css has 0 @font-face and 0 .fa-_ rules). Result: every icon on the site is blank — navbar icons (bell/user/cogs/logout), the challenges page loading spinner (fa-circle-notch: players see nothing while the board loads), solved check marks (corner-button-check), download/hint icons, external-link icons, search button (icon-only!), country flags via the icon font, modal 'x' glyph is text so it survives.
- **Correctif :** Add <link rel="stylesheet" href="{{ url_for('views.themes', path='css/fonts.css') }}"> before main.css in base.html (or inline the FA @font-face + classes into main.css).
- **Vérifié :** CONFIRMÉ — FontAwesome @font-face n'est que dans fonts.css (13 occurrences), non lié dans base.html (seuls main.css + core.css le sont) ; les templates utilisent des icônes fa-\*.

### 🟠 high · Connection Info block deleted: players never see nc host/port or challenge URLs

- **Où :** `CTFd/themes/hibris/templates/challenge.html`:39
- **Passe :** UX/qualité · catégorie consistency/CTFd-3.8.7
- **Problème :** The {% block connection_info %} span present in core-deprecated (and 3.8.7 core) was removed from the modal template. Both CTFd/plugins/challenges/assets/view.html and dynamic_challenges/assets/view.html simply {% extends "challenge.html" %} and do not define that block, so the challenge.connection_info field set by admins (typical for pwn/web/misc: 'nc host 1337', 'http://...') is silently dropped for all players.
- **Correctif :** Restore the block from core-deprecated/templates/challenge.html: <span class="challenge-connection-info">{% block connection_info %}{% set conn = challenge.connection_info %}{% if not conn %}{% elif conn.startswith("http") %}{{ conn | urlize(target="_blank") }}{% else %}<code>{{ conn }}</code>{% endif %}{% endblock %}</span>.
- **Vérifié :** CONFIRMÉ (diff) — le bloc connection_info existe dans core et core-deprecated mais est ABSENT de hibris/challenge.html ; impact : le `nc host port` / la chaîne SSH des challenges servis risque de ne pas s'afficher (à valider sur instance live).

### 🟠 high · Empty scoreboard (pre-event / no solves) renders a blank panel in both views

- **Où :** `CTFd/themes/hibris/templates/scoreboard.html`:416
- **Passe :** UX/qualité · catégorie scoreboard/empty-state
- **Problème :** refresh() hides #board-table as soon as the first successful API response arrives (line 416-419) BEFORE checking teams.length. On an empty scoreboard it then writes '<div class="waiting">En attente…</div>' into .track, but .track > \* { position:absolute } (line 106) and track.style.height is never set in that branch, so the track collapses to ~24px (padding only) with overflow:hidden and the message is clipped/invisible. The server-side table is wrapped in {% if standings %} with no else, so the 'Table' view is also blank. Net effect: at T-0 with ~300 players on /scoreboard, the page shows a header, two buttons and an empty box. Also, innerHTML replacement destroys .startline/.finishline and any existing lane DOM while the `lanes` map keeps detached references.
- **Correctif :** Do not hide the table when teams.length===0; render the waiting message outside .track (e.g. in a sibling div) or give .race .waiting { position:static } and set track.style.height; add an {% else %}<p class="text-center text-muted">Aucun score pour le moment</p> to the server table; reset `lanes = {}` whenever track.innerHTML is replaced.
- **Vérifié :** CONFIRMÉ — {% if standings %} sans {% else %}, et `.track > * {position:absolute}` tronque le message d'attente ; scoreboard vide au T-0.

### 🟠 high · Compiled main.css tail carries a leftover third palette that overrides the NCTF brand

- **Où :** `CTFd/themes/hibris/static/css/main.dev.css`:11135
- **Passe :** UX/qualité · catégorie consistency/branding
- **Problème :** The end of main.dev.css/main.min.css (after .badge-notification) contains an older 'Blueshield'-style block: body{background-color:#0f172a !important; grid background-image; color:#f1f5f9}, a:hover,.btn:hover,.nav-link:hover{color:#38bdf8; box-shadow:0 0 5px #38bdf8}, body,h1..h6{font-family:'Inter'} (Inter is never loaded), :root{--primary:#38bdf8}. The base.html body rule (background-color:var(--bg) #00040d) has no !important, so the slate-blue #0f172a wins site-wide, and every nav-link/btn hover gets a sky-blue glow that clashes with the Togo red/yellow/green identity. main.css also keeps .input-filled-valid/.form-control:focus green #a3d39c borders (old core theme) which show after typing in any input.
- **Correctif :** Delete the trailing custom block from main.dev.css and main.min.css (and the .input-filled-\* green rules), or override in base.html with body{background-color:var(--bg)!important} and .nav-link:hover,.btn:hover{box-shadow:none}.
- **Vérifié :** CONFIRMÉ — main.dev.css (fin de fichier) porte une 3e palette (#0f172a !important, #38bdf8, police 'Inter') qui écrase le thème NCTF.

### 🟡 medium · Flag 'Submit' button is grey-on-dark (btn-outline-secondary), the event's primary action

- **Où :** `CTFd/themes/hibris/assets/js/pages/challenges.js`:62
- **Passe :** UX/qualité · catégorie accessibility/contrast
- **Problème :** challenges.js adds 'btn btn-md btn-outline-secondary float-right' to #challenge-submit. Bootstrap's outline-secondary is #6c757d text/border on transparent; on the --panel #0b0f18 modal that is ~3.3:1 contrast (fails WCAG AA for normal text) and visually reads as disabled. base.html restyles .btn-primary/.btn-secondary/.btn-info but never .btn-outline-secondary.
- **Correctif :** Change the class list to 'btn btn-md btn-primary float-right' (Togo red) or add a base.html rule for .btn-outline-secondary { color:var(--yellow); border-color:var(--yellow) }.

### 🟡 medium · Solved-challenge styling is dead CSS; solved tiles become 40%-opacity low-contrast buttons

- **Où :** `CTFd/themes/hibris/templates/base.html`:116
- **Passe :** UX/qualité · catégorie bug/css
- **Problème :** base.html styles .solved .challenge-button / .challenge.solved (green top border, green tint), but challenges.js marks solved tiles with class 'solved-challenge' (never 'solved'). challenge-board.css .solved-challenge{background:#37d63e!important;opacity:.4} then fights base.html's .challenge-button{background:var(--panel)!important} (base wins: it is declared later at equal specificity), so a solved tile is simply the dark panel at opacity .4 — white text at ~40% on near-black, with the check icon missing (see fonts.css finding). Players cannot reliably distinguish solved from unsolved.
- **Correctif :** Target .challenge-button.solved-challenge in base.html (border-top-color:var(--green-b); background:rgba(23,176,107,.12)!important; opacity:1) and drop the opacity from challenge-board.css.

### 🟡 medium · Challenge description overflow rules missing: long strings/images break the modal at 360px

- **Où :** `CTFd/themes/hibris/static/css/core.dev.css`:1
- **Passe :** UX/qualité · catégorie responsive/mobile
- **Problème :** core-deprecated core.dev.css ends with .challenge-desc{overflow-wrap:anywhere}.challenge-desc img{max-width:100%}; hibris core.dev.css/core.min.css lack them. Long flags, URLs, base64 blobs, or wide screenshots in a description force horizontal scroll of the modal on phones. challenge-board.css .modal-content{max-width:1000px;padding:1em} also has no responsive margin.
- **Correctif :** Append .challenge-desc{overflow-wrap:anywhere} .challenge-desc img{max-width:100%;height:auto} .challenge-desc pre{overflow-x:auto} to core.dev.css/core.min.css (or base.html).

### 🟡 medium · Preselection (~300 teams): 288 teams collapse into one 'peloton' bubble with no way to find yourself

- **Où :** `CTFd/themes/hibris/templates/scoreboard.html`:371
- **Passe :** UX/qualité · catégorie scoreboard/UX
- **Problème :** TOPN=12 (14 in big mode). Everyone else is a single '+288 karts dans le peloton' pill. There is no highlight of the viewer's own team (the .yourcar CSS exists but is never used; init.teamId/teamName were removed from base.html so the script cannot even know the team), karts are not links to team pages (the table rows are), and the fallback Table view is a raw 300-row table with no own-row highlight, no search, no sticky header. For the 10-team finale the race view is fine.
- **Correctif :** Re-add 'teamId'/'teamName' to init in base.html; in layout() always render the viewer's own kart as an extra lane (rank shown) when outside top N; wrap .car-name in <a href=account_url> (the API already returns account_url); in the table add class="table-info"/own-row highlight via account_id===init.teamId and a sticky thead.

### 🟡 medium · Trailing karts are clipped off the left edge on phones

- **Où :** `CTFd/themes/hibris/templates/scoreboard.html`:335
- **Passe :** UX/qualité · catégorie responsive/mobile
- **Problème :** .car-wrap is centred at left:xpct% with translate(-50%,-50%); the last of top N sits at 12%. On a 360px viewport (track ~330px) 12% = 40px, but the wrap (46px kart + 100px name + score + gaps ≈ 200px) is centred there, so ~60px of kart/name are outside the track (overflow:hidden) and under the 28px rank badge at left:12px. On desktop (1100px) the same lane starts at ≈-18px. Long names hide behind the badge.
- **Correctif :** Clamp the kart: compute xpct from a minimum left offset (e.g. left = max(12%, badgeWidth + wrapWidth/2)) or use translateX(0) with left:calc(...) so the wrap's left edge, not its centre, is positioned; reduce the spread on small screens via the 640px media query.

### 🟡 medium · Dates rendered in English 12-hour format with no locale; UI is a French/English patchwork

- **Où :** `CTFd/themes/hibris/assets/js/times.js`:11
- **Passe :** UX/qualité · catégorie i18n
- **Problème :** times.js formats every [data-time] with dayjs 'MMMM Do, h:mm:ss A' (e.g. 'September 15th, 3:04:05 PM') and never loads the fr locale; solve times, token dates and notification dates all appear in English/AM-PM to a Togolese audience. Meanwhile the scoreboard ('Course', 'Table', 'DÉPART DANS', 'TEMPS RESTANT', 'peloton'), error pages, footer are French, but navbar (Users/Teams/Scoreboard/Challenges/Login/Register/Settings/Logout/Notifications), all forms, challenge modal ('Challenge', 'Solves', 'Submit', 'View Hint', 'Unlock Hint for N points'), JS alerts ('Got it!', 'Challenge Hidden!'), 'No solves yet', 'There are no notifications yet', 'Powered by', 'place/points' are English. Server-side flash messages from CTFd 3.8.7 follow the Babel locale, so a third source of language appears.
- **Correctif :** Pick one language per surface (or use CTFd 3.8.7's {% trans %} + Babel 'fr' locale for templates); in times.js import 'dayjs/locale/fr', call dayjs.locale(document.documentElement.lang||'fr') and use a 24h format like 'D MMM YYYY HH:mm:ss'; set <html lang="fr"> in base.html.

### 🟡 medium · No lang attribute on <html>; Bootstrap defaults produce several dark-mode contrast failures

- **Où :** `CTFd/themes/hibris/templates/base.html`:2
- **Passe :** UX/qualité · catégorie accessibility
- **Problème :** <html> has no lang (screen readers use the wrong voice for French). Unrestyled Bootstrap components on the dark theme: .text-muted #6c757d !important on the register hints ('Your username on the site', 'Never shown to the public'), 'Optional' labels, pagination and modal hints (~3.3:1); modal .close button color:#000 with white text-shadow on the dark modal (nearly invisible x); .nav-tabs .nav-link.active white background with #495057 text inside the dark modal (jarring white tab); .custom-select arrow SVG fill #343a40 on the #060a12 select background (invisible dropdown arrow on Country/Field selects); .alert-info/.alert-danger keep light pastel backgrounds.
- **Correctif :** Add lang="fr" to <html>; in base.html override .text-muted{color:var(--muted)!important}, .close{color:#fff;text-shadow:none;opacity:.7}, .nav-tabs .nav-link.active{background:var(--raised);color:#fff;border-color:var(--line)}, .custom-select{background-image with fill %23ffce00}, and tone alerts (.alert-info{background:rgba(23,176,107,.15);color:#fff;border-color:var(--green-b)}).

### 🟡 medium · Challenge name injected as raw HTML into the challenge board

- **Où :** `CTFd/themes/hibris/assets/js/pages/challenges.js`:311
- **Passe :** sécurité · catégorie XSS (DOM injection, admin-sourced)
- **Problème :** `const chalheader = $("<p>{0}</p>".format(chalinfo.name));` builds a jQuery element from an HTML string containing the unescaped challenge name returned by /api/v1/challenges. Same pattern at line 282: `$("<h3>" + category + "</h3>")` for the category header. Neither value passes through build_markdown/sanitize_html (HTML_SANITIZATION only wraps markdown/HTML page bodies), and the modal template challenge.html:25 renders `{{ challenge.name }}` autoescaped, so the board is the one inconsistent sink. Source is admin-controlled (challenge create/edit, or importing an untrusted CTFd export zip), so it is not reachable by players, but a compromised admin account or a poisoned import runs JS in every player's browser on /challenges. The built bundle static/js/pages/challenges.dev.js contains the identical string.
- **Correctif :** Use text nodes: `$("<p>").text(chalinfo.name)` and `$("<h3>").text(category)` (or htmlEntities() before .format()). Rebuild static/js afterwards (see stale-bundle finding).

### 🟡 medium · Notification toast renders raw notification title and markdown source as HTML, bypassing html_sanitization

- **Où :** `CTFd/themes/hibris/assets/js/ezq.js`:114
- **Passe :** sécurité · catégorie XSS (DOM injection, admin-sourced) / sanitizer bypass
- **Problème :** `toastTpl.format(args.title, args.body)` is parsed with `$(res)` and prepended to the DOM. events.js:56-63 passes `data.title` and `trimmed_content` = `data.content` (the raw markdown SOURCE from the SSE event, not the server-rendered `data.html`). Because the server-side `html_sanitization` switch only runs inside build_markdown(), the toast path bypasses it entirely even when an operator has enabled sanitization; the 47-char truncation can also split a tag. ezAlert (line 66, `<p>${args.body}</p>`) receives `data.html`, which is server-rendered with CMARK_OPT_UNSAFE (CTFd/utils/**init**.py:18) and only sanitized when HTML_SANITIZATION/html_sanitization is on (default False, config.py:263). Only admins can POST /api/v1/notifications, so the source is trusted, but a compromised admin session pushes script to every connected player in one shot.
- **Correctif :** In ezToast build the toast with DOM APIs / `.text()` (or htmlEntities(args.title), htmlEntities(args.body)); in events.js keep the toast body as plain text and only use `data.html` inside ezAlert. Enable `html_sanitization` in Admin > Config if raw admin HTML is not required.

## sécurité — low / info (12)

| sév  | fichier                                                    | titre                                                                                                    | correctif                                                                                                                                                                                                                                                                      |
| ---- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| low  | `CTFd/themes/hibris/templates/users/public.html:63`        | User website link has no http/https guard (unlike the team templates)                                    | Mirror the team templates: `{% if user.website and (user.website.startswith('http://') or user.website.startswith('https://')) %}`.                                                                                                                                            |
| low  | `CTFd/themes/hibris/templates/base.html:14`                | Google Fonts stylesheet loaded from fonts.googleapis.com on every page (twice)                           | Self-host Tourney/Lato/JetBrains Mono woff2 under static/fonts (already exists) with @font-face, drop the <link>/preconnect and the @import in main.min.css. If kept, add a CSP style-src/font-src allow-list and a Referrer-Policy header.                                    |
| low  | `CTFd/themes/hibris/assets/js/pages/setup.js:116`          | Setup page posts admin email to CTFd LLC Mailchimp via JSONP (default-checked box)                       | Remove the newsletter checkbox and the $.ajax JSONP block (or default it unchecked). Rebuild bundles.                                                                                                                                                                          |
| info | `CTFd/themes/hibris/static/js/pages/challenges.dev.js:165` | Shipped static bundles are the stock old-core build, not compiled from assets/js                         | Rebuild the theme bundles (yarn build / CTFd theme build pipeline) after fixing assets/js, and verify the fix string is present in static/js/pages/\*.min.js before the event.                                                                                                 |
| info | `CTFd/themes/hibris/templates/page.html:5`                 | CMS page content rendered with \|safe; sanitization off by default                                       | No template change needed. Set `html_sanitization` = true in Admin > Config (or HTML_SANITIZATION=true in config.ini) for the event unless raw admin HTML/iframes are required; restrict admin accounts to 2FA/strong passwords since every admin-HTML sink is script-capable. |
| info | `CTFd/themes/hibris/templates/scoreboard.html:353`         | Kart scoreboard renders team names safely (no stored-XSS via team name)                                  | None required. Keep textContent/esc() if the kart is extended (e.g. do not switch to innerHTML for name badges).                                                                                                                                                               |
| info | `CTFd/themes/hibris/assets/js/utils.js:47`                 | String.prototype.format uses String.replace, so `$'`/`` $` `` in user names duplicate template fragments | Pass a function to replace: `s = s.replace(re, () => arguments[i])`, or escape `$` in htmlEntities().                                                                                                                                                                          |
| info | `CTFd/themes/hibris/assets/js/pages/settings.js:129`       | location.hash 'sanitizer' is a no-op before use in a jQuery selector                                     | Use `$('.nav-pills a').filter((i, a) => a.getAttribute('href') === hash)` or CSS.escape(hash).                                                                                                                                                                                 |
| info | `CTFd/themes/hibris/templates/teams/public.html:11`        | MajorLeagueCyber profile links embed raw (autoescaped) team/user name in the path without URL-encoding   | Use `{{ team.name \| urlencode }}` (or drop MLC links entirely since the theme is de-branded and MLC is unused for this event).                                                                                                                                                |
| info | `CTFd/themes/hibris/assets/js/events.js:18`                | Notification sound hardcoded to /themes/core/static/sounds/ rather than the hibris theme                 | Point at the hibris theme (`/themes/hibris/static/sounds/...`) or use `init.themeSounds`/url_for from the template.                                                                                                                                                            |
| info | `CTFd/themes/hibris/assets/js/fetch.js:22`                 | CSRF nonce is applied centrally; no gaps found                                                           | None.                                                                                                                                                                                                                                                                          |
| info | `CTFd/themes/hibris/templates/base.html:237`               | No hardcoded secrets or debug flags; all target=\_blank links carry rel=noopener                         | Optionally add `rel="noopener"` in the markdown-it link_open hook for plugin consumers; set X-Frame-Options/frame-ancestors and a CSP at the proxy.                                                                                                                            |

## UX/qualité — low / info (12)

| sév  | fichier                                                  | titre                                                                                                             | correctif                                                                                                                                                                                                                                                                             |
| ---- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| low  | `CTFd/themes/hibris/templates/scoreboard.html:14`        | Race/Table switch uses role=tablist without tabpanel wiring or keyboard semantics; rank changes are not announced | Add aria-controls="race"/"board-table" and role="tabpanel" on the targets; add .rsw-btn:focus-visible{outline:2px solid var(--yellow)}; mark the SVG aria-hidden="true"; optionally add a visually-hidden aria-live="polite" element updated with 'X passe en tête' on leader change. |
| low  | `CTFd/themes/hibris/templates/scoreboard.html:437`       | Global 'f' key toggles fullscreen for every visitor                                                               | Only bind the handler when ?big=1 (bigmode) or require a modifier (Shift+F), and ignore events with e.target.isContentEditable or tagName SELECT.                                                                                                                                     |
| low  | `CTFd/themes/hibris/templates/scoreboard.html:92`        | Frozen state never surfaced in the race clock; ties and cache lag not communicated                                | Expose Configs.freeze in init and render 'CLASSEMENT GELÉ' with the .frozen class when set; consider POLL_MS = 30000–60000 to match the server cache; optionally show '=' for equal scores.                                                                                           |
| low  | `CTFd/themes/hibris/templates/scoreboard.html:58`        | Top-10 echarts graph and js/pages/scoreboard.js are never loaded; shape still compatible if re-enabled            | Either delete assets/js/pages/scoreboard.js + echarts bundle, or add the entrypoint and a #score-graph container (dark echarts theme) and use teams[i].account_url. Document that static/js must be rebuilt from the core-deprecated toolchain.                                       |
| low  | `CTFd/themes/hibris/templates/challenge.html:15`         | '1 Solves' pluralisation is a no-op and the solves counter is parsed from text                                    | Use '{{ solves }} {% if solves == 1 %}Solve{% else %}Solves{% endif %}' (or French 'résolution(s)'), add aria-label="Flag" to the input, and keep the count in a data attribute instead of parsing text.                                                                              |
| low  | `CTFd/themes/hibris/templates/scoreboard.html:31`        | Table headers are <td scope=col> so the branded '.table thead th' style and header semantics never apply          | Replace thead <td> with <th scope="col"> across templates; move width to a class/style.                                                                                                                                                                                               |
| low  | `CTFd/themes/hibris/templates/setup.html:195`            | Setup: End-time UTC preview is bound to form.start; several 3.8.7 SetupForm fields not rendered                   | Use {{ form.end(class="form-control", id="end-preview", readonly=True) }} (as in core-deprecated); consider copying the 3.8.7 core-deprecated setup.html wholesale.                                                                                                                   |
| low  | `CTFd/themes/hibris/templates/components/navbar.html:33` | Scoreboard link shown even when account_visibility is admins-only (route then 403s)                               | Restore the combined condition; translate/hide MLC buttons (integrations.mlc() is false unless configured, so they will not show — just remove for cleanliness).                                                                                                                      |
| low  | `CTFd/themes/hibris/templates/base.html:14`              | Display fonts loaded from Google Fonts CDN; on-site event with restricted/slow internet will fall back            | Self-host the three families under static/fonts and declare them in fonts.css (which must be linked anyway), keep Google Fonts only as an optional fallback.                                                                                                                          |
| info | `CTFd/themes/hibris/assets/js/events.js:18`              | Notification sound: works, but path points at the core theme and playback depends on autoplay policy              | Use init.urlRoot + '/themes/hibris/static/sounds/…' (or a config-driven theme name); optionally add howl.once('playerror', …) to show the toast without sound; document that admins should expect no sound before first interaction.                                                  |
| info | `CTFd/themes/hibris/static/img/challdesc.PNG`            | Mixed-case .PNG screenshots are unreferenced in the theme (dead assets, ~1.5 MB incl. ctfd.ai)                    | Delete the unused screenshots and .ai source from static/img (they are served publicly), or rename to lowercase if any page content references them.                                                                                                                                  |
| info | `CTFd/themes/hibris/assets/js/pages/challenges.js:282`   | Category and challenge names are inserted as raw HTML on the board                                                | Use htmlEntities() (already imported) for name/category and render 'Aucune épreuve disponible pour le moment' when challenges.length === 0.                                                                                                                                           |

## Recommandations d'exploitation (hors code)

- **Activer `html_sanitization`** (Admin > Config) pour l'événement : durcit en un cran les rendus `|safe` (pages, descriptions, notifications, hints) — ne couvre PAS les 2 findings medium sécurité qui exigent le correctif code.
- **Auto-héberger les polices** (Google Fonts est chargé sur chaque page → fuite IP/UA/Referer, pas de SRI possible).
- **Rebuild des bundles** : `static/js` est un build figé ; toute correction dans `assets/js` ne s'applique qu'après reconstruction du thème.

> Rappel CI : le thème hibris n'est pas couvert par « Theme Verification » (qui ne vérifie qu'admin+core) et les `.html` sont dans `.prettierignore` — cet audit est purement qualité/sécurité, sans garde-fou CI.

## Corrections appliquées

Correctifs à effet immédiat (aucun rebuild requis) — les 4 HIGH + contrastes + XSS admin :

- **HIGH icônes** — `base.html` lie désormais `css/fonts.css` (avant `main.css`) → FontAwesome + webfonts chargés.
- **HIGH connection_info** — bloc `{% block connection_info %}` restauré dans `challenge.html` (après la description) → le `nc host port` / la chaîne SSH des challenges servis s'affiche à nouveau.
- **HIGH scoreboard vide** — `scoreboard.html` : ajout d'un `{% else %}` (« Aucun score pour le moment ») sur la table serveur, `.race .waiting { position:static }`, et le JETON JS ne cache plus la table quand `teams.length===0` et rend un message d'attente lisible (hauteur auto, `lanes` réinitialisé). Inline JS re-validé (`node --check`).
- **HIGH palette parasite** — bloc de queue (`#0f172a !important`, `#38bdf8`, police `Inter`, `:root`) retiré de `main.dev.css` (le `main.min.css` de prod était déjà propre → dev aligné sur prod).
- **MEDIUM contraste** — bouton `.challenge-submit` re-stylé (rouge haute-lisibilité) ; les tuiles résolues ciblent désormais `.solved` **et** `.solved-challenge` (le JS applique les deux).
- **MEDIUM XSS (admin)** — `challenges.js` : nom et catégorie de challenge injectés via `$("<p>").text(...)` / `$("<h3>").text(...)` au lieu de HTML brut ; corrigé dans la **source ET les bundles servis** (`challenges.min.js`, `challenges.dev.js`), `node --check` OK.
- **LOW i18n** — `<html lang="fr">`.

**Reportés (nécessitent un rebuild de thème ou touchent un bundle partagé) :**

- **MEDIUM toast notification** (`ezq.js` + `events.js`) : `data.title`/`data.content` rendus en HTML brut. Correctif dans le bundle `core` partagé (rayon d'action large) → à traiter lors d'un rebuild du thème. **Mitigation d'ici là :** activer `html_sanitization` (Admin > Config).
- Divers LOW/INFO (auto-hébergement des polices, beacon Mailchimp du setup, contrastes dark-mode Bootstrap résiduels, `init.teamId` pour la surbrillance de sa propre équipe) — cosmétiques, non bloquants.
