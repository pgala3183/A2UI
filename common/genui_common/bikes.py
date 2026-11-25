"""The demo domain every codelab shares: a small bike-share network.

Using one domain everywhere makes the codelabs comparable: the same station
card, dashboard, calculator and simulator appear in A2UI, AG-UI, MCP Apps,
json-render, OpenUI Lang and the harness, so the differences you see are the
differences between the technologies.

The two HTML documents at the bottom are what a model writes in the
open-ended and mixed modes. They talk to their host only through the small
``window.genui`` bridge that the sandbox injects:

    genui.send(name, payload)   ask the host to perform a named action
    genui.onData(callback)      receive data the host pushes into the frame
"""

from __future__ import annotations

import copy
import itertools

STATIONS = [
    {"id": "market", "name": "Market St & 4th", "bikes": 3, "capacity": 22, "rides_today": 142, "ebikes": 1},
    {"id": "ferry", "name": "Ferry Building", "bikes": 21, "capacity": 23, "rides_today": 188, "ebikes": 6},
    {"id": "caltrain", "name": "Caltrain Depot", "bikes": 11, "capacity": 22, "rides_today": 96, "ebikes": 3},
    {"id": "mission", "name": "Mission & 16th", "bikes": 0, "capacity": 15, "rides_today": 77, "ebikes": 0},
    {"id": "sjsu", "name": "SJSU Student Union", "bikes": 14, "capacity": 18, "rides_today": 131, "ebikes": 4},
]

HOURS = ["6a", "7a", "8a", "9a", "10a", "11a", "12p", "1p", "2p", "3p", "4p", "5p", "6p"]
_PATTERN = [2, 9, 17, 12, 6, 5, 8, 7, 6, 8, 13, 18, 11]  # a commuter curve

PRICING = {"unlock": 1.0, "per_minute": 0.25, "ebike_per_minute": 0.15, "member_discount": 0.5}


def hourly(station_id: str) -> list[int]:
    """Rides per hour for a station: the commuter curve scaled by its volume."""
    s = station(station_id)
    scale = s["rides_today"] / sum(_PATTERN)
    return [round(v * scale) for v in _PATTERN]


def station(station_id: str) -> dict:
    for s in STATIONS:
        if s["id"] == station_id:
            return dict(s, docks=s["capacity"] - s["bikes"], fill=round(s["bikes"] / s["capacity"], 2))
    raise KeyError(station_id)


def status(s: dict) -> str:
    fill = s["bikes"] / s["capacity"]
    if fill <= 0.2:
        return "empty soon"
    if fill >= 0.85:
        return "full soon"
    return "balanced"


class Network:
    """Mutable network state for one server: actions change it, the UI shows it."""

    _tickets = itertools.count(4201)

    def __init__(self):
        self.stations = copy.deepcopy(STATIONS)
        self.tickets: list[dict] = []
        self.pricing = dict(PRICING)

    def get(self, station_id: str) -> dict:
        for s in self.stations:
            if s["id"] == station_id:
                return s
        raise KeyError(station_id)

    def view(self, station_id: str) -> dict:
        s = self.get(station_id)
        return {**s, "docks": s["capacity"] - s["bikes"], "status": status(s), "hourly": hourly(station_id)}

    def summary(self) -> dict:
        bikes = sum(s["bikes"] for s in self.stations)
        capacity = sum(s["capacity"] for s in self.stations)
        return {"stations": len(self.stations), "bikes": bikes, "capacity": capacity,
                "rides_today": sum(s["rides_today"] for s in self.stations),
                "needs_attention": [s["id"] for s in self.stations if status(s) != "balanced"]}

    def table(self) -> list[list]:
        return [[s["name"], s["bikes"], s["capacity"] - s["bikes"], status(s)] for s in self.stations]

    def rebalance(self, source: str, target: str, count: int) -> dict:
        """Move ``count`` bikes; refuses moves that break capacity. Returns a result dict."""
        a, b = self.get(source), self.get(target)
        count = int(count)
        if count <= 0:
            return {"ok": False, "error": "count must be positive"}
        if count > a["bikes"]:
            return {"ok": False, "error": f"{a['name']} has only {a['bikes']} bikes"}
        if b["bikes"] + count > b["capacity"]:
            return {"ok": False, "error": f"{b['name']} has only {b['capacity'] - b['bikes']} free docks"}
        a["bikes"] -= count
        b["bikes"] += count
        return {"ok": True, "moved": count, "from": a["name"], "to": b["name"],
                "from_bikes": a["bikes"], "to_bikes": b["bikes"]}

    def report(self, station_id: str, bike: str, issue: str) -> dict:
        ticket = {"ticket": f"BK-{next(self._tickets)}", "station": self.get(station_id)["name"],
                  "bike": bike, "issue": issue}
        self.tickets.append(ticket)
        return ticket

    def ride_cost(self, minutes: float, ebike: bool, member: bool) -> float:
        p = self.pricing
        cost = p["unlock"] + minutes * (p["per_minute"] + (p["ebike_per_minute"] if ebike else 0))
        return round(cost * (1 - p["member_discount"]) if member else cost, 2)


def as_text(network: Network) -> str:
    """The plain-text answer a host shows when it cannot render UI."""
    lines = [f"{s['name']}: {s['bikes']}/{s['capacity']} bikes ({status(s)})" for s in network.stations]
    return "Bike-share network\n" + "\n".join(lines)


# --- what a model writes in open-ended mode ---------------------------------

TRIP_CALCULATOR_HTML = """<!doctype html>
<html><head><style>
  body{font:14px system-ui,sans-serif;margin:0;padding:14px;color:#1d2433;background:#f7fafc}
  h2{margin:0 0 10px;font-size:17px}.row{display:flex;gap:12px;align-items:center;margin:8px 0}
  input[type=range]{flex:1}.cost{font-size:34px;font-weight:700;color:#0b7a53;margin:10px 0}
  .muted{color:#667;font-size:12px}.msg{margin-top:8px;color:#0b7a53;font-weight:600}button{background:#1f6feb;color:#fff;border:0;border-radius:8px;padding:8px 14px;cursor:pointer}
</style></head><body>
  <h2>Trip cost calculator</h2>
  <div class="row"><label for="min">Minutes</label><input id="min" type="range" min="5" max="90" value="25"><b id="minv">25</b></div>
  <div class="row"><label><input id="ebike" type="checkbox"> E-bike</label><label><input id="member" type="checkbox"> Member</label></div>
  <div class="cost" id="cost">$0.00</div>
  <div class="muted" id="rule"></div>
  <div class="row"><button id="book">Book this ride</button></div>
  <div class="msg" id="msg"></div>
<script>
  let pricing = {unlock: 1, per_minute: 0.25, ebike_per_minute: 0.15, member_discount: 0.5};
  const $ = (id) => document.getElementById(id);
  function cost() {
    const m = +$("min").value, e = $("ebike").checked, mem = $("member").checked;
    let c = pricing.unlock + m * (pricing.per_minute + (e ? pricing.ebike_per_minute : 0));
    if (mem) c = c * (1 - pricing.member_discount);
    return Math.round(c * 100) / 100;
  }
  function draw() {
    $("minv").textContent = $("min").value;
    $("cost").textContent = "$" + cost().toFixed(2);
    $("rule").textContent = "$" + pricing.unlock.toFixed(2) + " unlock + $" + pricing.per_minute.toFixed(2) + "/min";
  }
  ["min", "ebike", "member"].forEach((id) => $(id).addEventListener("input", draw));
  $("book").addEventListener("click", () => genui.send("book_ride",
    {minutes: +$("min").value, ebike: $("ebike").checked, member: $("member").checked, cost: cost()}));
  genui.onData((data) => {
    if (data && data.pricing) { pricing = data.pricing; draw(); }
    if (data && data.message) $("msg").textContent = data.message;
  });
  draw();
</script></body></html>"""

REBALANCE_SIMULATOR_HTML = """<!doctype html>
<html><head><style>
  body{font:13px system-ui,sans-serif;margin:0;padding:12px;color:#1d2433;background:#fbfaf6}
  h3{margin:0 0 8px;font-size:15px}.bar{display:flex;align-items:center;gap:8px;margin:4px 0}
  .name{width:140px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .track{flex:1;height:14px;background:#e6e9ef;border-radius:7px;overflow:hidden}
  .fill{height:100%;background:#2f9e6e;transition:width .3s}.low{background:#d9534f}.high{background:#e8a33d}
  .ctl{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
  select,input{font:inherit}button{background:#1f6feb;color:#fff;border:0;border-radius:7px;padding:6px 12px;cursor:pointer}
  .msg{margin-top:8px;color:#0b7a53;font-weight:600}
</style></head><body>
  <h3>Rebalancing simulator</h3>
  <div id="bars"></div>
  <div class="ctl">Move <input id="n" type="number" min="1" max="20" value="6" style="width:52px"> bikes from
    <select id="from"></select> to <select id="to"></select> <button id="apply">Apply plan</button></div>
  <div class="msg" id="msg"></div>
<script>
  let stations = [], previewing = false;
  const $ = (id) => document.getElementById(id);
  function preview() {
    if (!previewing) return stations;
    const n = +$("n").value, f = $("from").value, t = $("to").value;
    return stations.map((s) => ({...s, bikes: s.bikes + (s.id === t ? n : 0) - (s.id === f ? n : 0)}));
  }
  function draw() {
    $("bars").innerHTML = "";
    for (const s of preview()) {
      const pct = Math.max(0, Math.min(100, Math.round(100 * s.bikes / s.capacity)));
      const tone = pct <= 20 ? "low" : pct >= 85 ? "high" : "";
      const row = document.createElement("div");
      row.className = "bar";
      row.innerHTML = '<span class="name"></span><span class="track"><span class="fill ' + tone + '" style="width:' + pct + '%;display:block"></span></span><b>' + s.bikes + "/" + s.capacity + "</b>";
      row.querySelector(".name").textContent = s.name;
      $("bars").appendChild(row);
    }
  }
  function options() {
    for (const id of ["from", "to"]) {
      const keep = $(id).value;
      $(id).innerHTML = "";
      for (const s of stations) { const o = document.createElement("option"); o.value = s.id; o.textContent = s.name; $(id).appendChild(o); }
      if (keep) $(id).value = keep;
    }
    if (!$("from").value || $("from").value === $("to").value) {
      const full = [...stations].sort((a, b) => b.bikes / b.capacity - a.bikes / a.capacity);
      $("from").value = full[0].id; $("to").value = full[full.length - 1].id;
    }
  }
  ["n", "from", "to"].forEach((id) => $(id).addEventListener("input", () => { previewing = true; draw(); }));
  $("apply").addEventListener("click", () => genui.send("rebalance", {from: $("from").value, to: $("to").value, count: +$("n").value}));
  genui.onData((data) => {
    if (data && data.stations) { stations = data.stations; previewing = false; options(); draw(); }
    if (data && data.message) $("msg").textContent = data.message;
  });
</script></body></html>"""
