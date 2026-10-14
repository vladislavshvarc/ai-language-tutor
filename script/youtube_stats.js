// Video quality check for course videos (course.md, "Videos for units").
// Run in the built-in browser pane (or Claude in Chrome) on any https://www.youtube.com page:
// paste this whole file into the javascript tool, then call one of the functions in the same
// call, e.g.   ...file...;  await ytSearch("passé composé explained", 8)
//              ...file...;  await ytStats(["84olv0BM4oY", "wa4ILiCUeiE"])
//              ...file...;  await ytChannel("@learnfrenchwithalexa", "nasal")
//              ...file...;  ytTopComments(8)   (on an open watch page, after scrolling to the comments)
// Same-origin fetches of youtube.com pages; nothing is posted and no account is needed.

const _yt = {
  num(s) { // "3,2 тыс." / "1.2K" / "2,45 миллиона" / "2.45M" / "51369" -> number
    if (s == null) return null;
    s = String(s).replace(/[\u00a0\u202f\u2009]/g, " ").trim();
    const m = s.match(/([\d.,\s]+)\s*(миллиард|млрд|миллион|млн|тысяч|тыс|billion|million|thousand|K|M|B)?/i);
    if (!m) return null;
    let n = m[1].replace(/\s/g, "");
    n = m[2] ? parseFloat(n.replace(",", ".")) : parseFloat(n.replace(/[.,]/g, ""));
    const u = (m[2] || "").toLowerCase();
    const mult = /^(миллиард|млрд|billion|b)$/.test(u) ? 1e9 : /^(миллион|млн|million|m)$/.test(u) ? 1e6 : /^(тысяч|тыс|thousand|k)$/.test(u) ? 1e3 : 1;
    return Math.round(n * mult);
  },
  async page(url) { return (await fetch(url, { credentials: "omit" })).text(); },
  json(h, name) {
    const i = h.indexOf(name + " = ");
    if (i < 0) return null;
    let j = h.indexOf("{", i), depth = 0, k = j, inStr = false, esc = false;
    for (; k < h.length; k++) {
      const c = h[k];
      if (inStr) { if (esc) esc = false; else if (c === "\\") esc = true; else if (c === '"') inStr = false; continue; }
      if (c === '"') inStr = true; else if (c === "{") depth++; else if (c === "}" && --depth === 0) break;
    }
    try { return JSON.parse(h.slice(j, k + 1)); } catch (e) { return null; }
  },
  walk(o, key, out = []) {
    if (o && typeof o === "object") { if (o[key]) out.push(o[key]); for (const v of Object.values(o)) _yt.walk(v, key, out); }
    return out;
  },
};

// Views, likes, comments, channel subscribers, length and date for each video id.
async function ytStats(ids) {
  return Promise.all([].concat(ids).map(async id => {
    const h = await _yt.page("/watch?v=" + id + "&hl=en&gl=US");
    const g = re => { const m = h.match(re); return m ? m[1] : null; };
    const views = +g(/"viewCount":"(\d+)"/) || null;
    const likes = _yt.num(g(/like this video along with ([\d,]+) other/)) || _yt.num(g(/"likeCount":"?(\d+)/));
    const comments = _yt.num(g(/"commentCount":\{"simpleText":"([^"]+)"/) || g(/"contextualInfo":\{"runs":\[\{"text":"([^"]+)"\}\]/));
    const subs = _yt.num(g(/"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"/) || g(/"subscriberCountText":\{"simpleText":"([^"]+)"/));
    return {
      id, url: "https://www.youtube.com/watch?v=" + id,
      title: JSON.parse('"' + (g(/"title":"((?:[^"\\]|\\.)*)","lengthSeconds"/) || "") + '"'),
      channel: g(/"ownerChannelName":"((?:[^"\\]|\\.)*)"/), channel_url: g(/"ownerProfileUrl":"([^"]+)"/),
      views, likes, comments, subscribers: subs,
      like_rate: views && likes ? +(100 * likes / views).toFixed(2) : null,
      minutes: Math.round((+g(/"lengthSeconds":"(\d+)"/) || 0) / 6) / 10,
      published: (g(/"publishDate":"([^"]+)"/) || "").slice(0, 10),
    };
  }));
}

// Search results (videos only) with their stats; sorted by views.
async function ytSearch(query, n = 8) {
  const h = await _yt.page("/results?search_query=" + encodeURIComponent(query) + "&hl=en&gl=US");
  const data = _yt.json(h, "ytInitialData");
  const ids = [...new Set(_yt.walk(data, "videoRenderer").map(v => v.videoId))].slice(0, n);
  return (await ytStats(ids)).sort((a, b) => (b.views || 0) - (a.views || 0));
}

// Videos of one channel matching a query (e.g. a preferred channel), with stats.
async function ytChannel(handle, query, n = 8) {
  const h = await _yt.page("/" + handle.replace(/^\/?/, "") + "/search?query=" + encodeURIComponent(query) + "&hl=en&gl=US");
  const data = _yt.json(h, "ytInitialData");
  const ids = [...new Set(_yt.walk(data, "videoRenderer").map(v => v.videoId))].slice(0, n);
  return ytStats(ids);
}

// Top comments of the watch page that is open in the tab (scroll down first so they load).
function ytTopComments(n = 8) {
  return [...document.querySelectorAll("ytd-comment-thread-renderer #content-text")].slice(0, n).map(e => e.innerText.trim().slice(0, 300));
}
