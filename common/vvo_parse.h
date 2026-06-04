#pragma once
// ════════════════════════════════════════════════════════════════════
// common/vvo_parse.h — VVO DepartureMonitor JSON → LVGL-Zeilen
// ────────────────────────────────────────────────────────────────────
// Eine freie Funktion, von beiden Stop-Intervals in cortex-vvo.yaml
// aufgerufen (DRY statt doppelter Inline-Lambda). Kein ArduinoJson:
// der Body wird wie im FEED-Parser per String-Suche zerlegt — robust
// gegen die Microsoft-JSON-Datumsschreibweise "\/Date(ms+tz)\/".
// ════════════════════════════════════════════════════════════════════
#include <string>
#include <cstdio>
#include "esphome/components/time/real_time_clock.h"
#include "esphome/core/log.h"

namespace vvo {

// String-Wert zu "key":"..." aus einem Departures-Objekt ziehen.
inline std::string str_field(const std::string &obj, const char *key) {
  std::string needle = std::string("\"") + key + "\":\"";
  size_t p = obj.find(needle);
  if (p == std::string::npos) return "";
  p += needle.size();
  size_t e = obj.find('"', p);
  return (e != std::string::npos) ? obj.substr(p, e - p) : "";
}

// Epoch-Millis aus "key":"\/Date(1780606680000-0000)\/". 0 = nicht da.
inline long long date_ms(const std::string &obj, const char *key) {
  std::string k = std::string("\"") + key + "\":\"";
  size_t p = obj.find(k);
  if (p == std::string::npos) return 0;
  p = obj.find("Date(", p);
  if (p == std::string::npos) return 0;
  p += 5;
  long long v = 0;
  while (p < obj.size() && obj[p] >= '0' && obj[p] <= '9') { v = v * 10 + (obj[p] - '0'); p++; }
  return v;
}

// S-Bahn nur Richtung Neustadt: suedwaerts gehende Endpunkte verwerfen.
inline bool sbahn_southbound(const std::string &dir) {
  static const char *deny[] = {"Schandau", "Pirna", "Heidenau", "Schöna",
                               "Nationalpark", "Tharandt", "Freiberg"};
  for (auto d : deny) if (dir.find(d) != std::string::npos) return true;
  return false;
}

// Body parsen, bis zu `max_rows` Zeilen "LINIE  ZIEL  N'" ins Label setzen.
inline void render(const std::string &body, lv_obj_t *label,
                   esphome::time::RealTimeClock *clk, int max_rows) {
  auto now = clk->now();
  long long now_s = now.is_valid() ? (long long) now.timestamp : 0;

  std::string out;
  int rows = 0;
  size_t arr = body.find("\"Departures\":");
  if (arr != std::string::npos) {
    size_t i = body.find('[', arr);
    while (i != std::string::npos && rows < max_rows) {
      // Nächstes Top-Level-Objekt im Array; ']' = Array-Ende.
      while (i < body.size() && body[i] != '{' && body[i] != ']') i++;
      if (i >= body.size() || body[i] == ']') break;

      // Klammer-Matching: das schliessende '}' DIESES Departures finden und
      // verschachtelte Platform{}/Diva{} mitzaehlen. Naives find('}') brach
      // sonst am Ende von "Platform":{...} ab → Mot/RealTime lagen dahinter
      // und wurden nie gelesen (ms=0 → keine Zeit). Strings inkl. Escapes
      // ("\/Date(...)\/") werden uebersprungen.
      size_t start = i;
      int depth = 0;
      bool in_str = false;
      for (; i < body.size(); i++) {
        char c = body[i];
        if (in_str) {
          if (c == '\\') { i++; continue; }
          if (c == '"') in_str = false;
          continue;
        }
        if (c == '"') in_str = true;
        else if (c == '{') depth++;
        else if (c == '}') { if (--depth == 0) { i++; break; } }
      }
      std::string obj = body.substr(start, i - start);

      std::string line = str_field(obj, "LineName");
      std::string dir  = str_field(obj, "Direction");
      std::string mot  = str_field(obj, "Mot");
      if (line.empty()) continue;
      if (mot == "SuburbanRailway" && sbahn_southbound(dir)) continue;

      long long ms = date_ms(obj, "RealTime");
      if (ms == 0) ms = date_ms(obj, "ScheduledTime");
      int mins = (now_s > 0 && ms > 0) ? (int) (ms / 1000 - now_s) / 60 : 0;
      if (mins < 0) mins = 0;

      // Schmal fuer Zwei-Spalten-Layout (je ~150px): Linie, gekuerztes Ziel, Min.
      char row[32];
      snprintf(row, sizeof(row), "%-3.3s%-9.9s%2d'", line.c_str(), dir.c_str(), mins);
      if (!out.empty()) out += "\n";
      out += row;
      rows++;
    }
  }
  if (out.empty()) out = "-- keine Daten --";
  ESP_LOGD("vvo", "render %d rows, now_s=%lld:\n%s", rows, now_s, out.c_str());
  lv_label_set_text(label, out.c_str());
}

}  // namespace vvo
