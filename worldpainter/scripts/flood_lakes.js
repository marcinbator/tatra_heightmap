// Tools -> Run script..., argument: pelna sciezka do *_water.png
var ImageIO = Java.type("javax.imageio.ImageIO");
var File = Java.type("java.io.File");
var IntArray = Java.type("int[]");

var SHORE_PCT = 2; // percentyl brzegu = poziom wody
var SLOPE = 0.35; // ile blokow glebiej na kazdy blok od brzegu (mniej = lagodniej)

var img = ImageIO.read(new File(arguments[0]));
var raster = img.getRaster();
var w = img.getWidth(),
  h = img.getHeight();
var row = new IntArray(w);
var bb = {};

// 1. bboxy jezior
for (var y = 0; y < h; y++) {
  wp.checkForInterrupt();
  raster.getSamples(0, y, w, 1, 0, row);
  for (var x = 0; x < w; x++) {
    var id = row[x];
    if (id > 0) {
      var b = bb[id];
      if (b === undefined) bb[id] = { x0: x, y0: y, x1: x, y1: y };
      else {
        if (x < b.x0) b.x0 = x;
        if (x > b.x1) b.x1 = x;
        if (y > b.y1) b.y1 = y;
      }
    }
  }
}

var ids = Object.keys(bb);
var lakes = 0,
  cols = 0,
  reshaped = 0,
  filled = 0;
var DX = [-1, 1, 0, 0],
  DY = [0, 0, -1, 1];

for (var k = 0; k < ids.length; k++) {
  wp.checkForInterrupt();
  var id = parseInt(ids[k]);
  var b = bb[id];
  var x0 = Math.max(b.x0 - 1, 0),
    y0 = Math.max(b.y0 - 1, 0);
  var x1 = Math.min(b.x1 + 1, w - 1),
    y1 = Math.min(b.y1 + 1, h - 1);
  var bw = x1 - x0 + 1,
    bh = y1 - y0 + 1;
  var win = new IntArray(bw * bh);
  raster.getSamples(x0, y0, bw, bh, 0, win);

  // 2. najplytsze dno i wysokosci brzegu
  var maxBottom = -100000;
  var shore = [],
    shoreIdx = [];
  var seen = {};
  for (var i = 0; i < win.length; i++) {
    if (win[i] !== id) continue;
    var cx = i % bw,
      cy = (i - cx) / bw;
    var hh = dimension.getIntHeightAt(x0 + cx, y0 + cy);
    if (hh > maxBottom) maxBottom = hh;
    for (var n = 0; n < 4; n++) {
      var nx = cx + DX[n],
        ny = cy + DY[n];
      if (nx < 0 || ny < 0 || nx >= bw || ny >= bh) continue;
      var j = ny * bw + nx;
      if (win[j] !== 0 || seen[j]) continue;
      seen[j] = true;
      shore.push(dimension.getIntHeightAt(x0 + nx, y0 + ny));
      shoreIdx.push(j);
    }
  }
  if (shore.length === 0) continue;

  var sorted = shore.slice().sort(function (a, c) {
    return a - c;
  });
  var pct =
    sorted[
      Math.min(sorted.length - 1, Math.floor((sorted.length * SHORE_PCT) / 100))
    ];
  var L = Math.min(maxBottom + 1, pct);

  // 3. odleglosc od brzegu wewnatrz jeziora (BFS od kolumn przy brzegu)
  var dist = new IntArray(win.length);
  var queue = new IntArray(win.length);
  var head = 0,
    tail = 0;
  for (var i = 0; i < win.length; i++) dist[i] = -1;
  for (var i = 0; i < win.length; i++) {
    if (win[i] !== id) continue;
    var cx = i % bw,
      cy = (i - cx) / bw;
    for (var n = 0; n < 4; n++) {
      var nx = cx + DX[n],
        ny = cy + DY[n];
      if (
        nx < 0 ||
        ny < 0 ||
        nx >= bw ||
        ny >= bh ||
        win[ny * bw + nx] !== id
      ) {
        dist[i] = 1;
        queue[tail++] = i;
        break;
      }
    }
  }
  while (head < tail) {
    var i = queue[head++];
    var cx = i % bw,
      cy = (i - cx) / bw;
    for (var n = 0; n < 4; n++) {
      var nx = cx + DX[n],
        ny = cy + DY[n];
      if (nx < 0 || ny < 0 || nx >= bw || ny >= bh) continue;
      var j = ny * bw + nx;
      if (win[j] === id && dist[j] === -1) {
        dist[j] = dist[i] + 1;
        queue[tail++] = j;
      }
    }
  }

  // 4. dno: lagodny profil od brzegu, glebszy srodek zostaje, zawsze min. 1 blok wody
  for (var i = 0; i < win.length; i++) {
    if (win[i] !== id) continue;
    var cx = i % bw,
      cy = (i - cx) / bw;
    var X = x0 + cx,
      Y = y0 + cy;
    var cur = dimension.getHeightAt(X, Y);
    var gentle = L - 1 - (dist[i] - 1) * SLOPE;
    var nh = Math.min(L - 1, Math.max(cur, gentle));
    if (nh !== cur) {
      dimension.setHeightAt(X, Y, nh);
      reshaped++;
    }
    dimension.setWaterLevelAt(X, Y, L);
    cols++;
  }

  // 5. pojedyncze dziury w brzegu ponizej wody -> do poziomu wody
  for (var s = 0; s < shoreIdx.length; s++) {
    if (shore[s] < L) {
      var j = shoreIdx[s];
      var cx = j % bw,
        cy = (j - cx) / bw;
      dimension.setHeightAt(x0 + cx, y0 + cy, L);
      filled++;
    }
  }
  lakes++;
}
