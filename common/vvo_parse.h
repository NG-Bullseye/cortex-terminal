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

// Display-Breite in MONOSPACE-Zellen = Anzahl UTF-8-Codepoints (Umlaut ü/ä/ö/ß
// ist 2 Bytes aber 1 Zelle). Byte-basiertes %-Ns verschob sonst die Spalte.
inline int disp_len(const std::string &s) {
  int n = 0;
  for (unsigned char c : s) if ((c & 0xC0) != 0x80) n++;
  return n;
}

// Auf max. n Codepoints kuerzen (schneidet nie mitten in ein UTF-8-Zeichen).
inline std::string trunc_disp(const std::string &s, int n) {
  int cp = 0; size_t i = 0;
  for (; i < s.size() && cp < n; i++) if ((s[i] & 0xC0) != 0x80) cp++;
  // i steht jetzt am ersten Byte nach n Codepoints (Continuation-Bytes mitnehmen)
  while (i < s.size() && (s[i] & 0xC0) == 0x80) i++;
  return s.substr(0, i);
}

// Whitelist-Eintrag: nur diese Linie in diese Richtung zeigen.
// `dir` ist ein Substring des VVO-"Direction"-Feldes (z.B. "Bühlau").
struct Allow { const char *line; const char *dir; };

// Body parsen, bis zu `max_rows` Zeilen "LINIE  ZIEL  N'" ins Label setzen.
// Nur Abfahrten die zu einem allow[]-Eintrag passen werden angezeigt.
inline void render(const std::string &body, lv_obj_t *label,
                   esphome::time::RealTimeClock *clk, int max_rows,
                   const Allow *allow, int n_allow) {
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
      if (line.empty()) continue;

      // Strikte Whitelist: nur exakt-Linie + Richtungs-Substring durchlassen.
      bool ok = false;
      for (int a = 0; a < n_allow; a++)
        if (line == allow[a].line && dir.find(allow[a].dir) != std::string::npos) {
          ok = true;
          break;
        }
      if (!ok) continue;

      long long ms = date_ms(obj, "RealTime");
      if (ms == 0) ms = date_ms(obj, "ScheduledTime");
      int mins = (now_s > 0 && ms > 0) ? (int) (ms / 1000 - now_s) / 60 : 0;
      // Nicht mehr erreichbar (≤3 min) gar nicht erst anzeigen.
      if (mins <= 3) continue;

      // Zeile = "LINIE ZIEL ........ MM'" mit RECHTSBUENDIGER Minutenzahl.
      // Monospace-Spaltenbreite W; Padding ueber disp_len (Codepoints, nicht
      // Bytes) damit Umlaute die Ausrichtung nicht zerschieben.
      const int W = 20;
      char minbuf[8];
      snprintf(minbuf, sizeof(minbuf), "%d'", mins);
      int rl = disp_len(minbuf);

      std::string lpad = trunc_disp(line, 3);
      while (disp_len(lpad) < 3) lpad += " ";       // Linie auf 3 Zellen
      std::string left = lpad + " " + dir;          // + Ziel
      int maxleft = W - rl - 1;                      // min. 1 Zelle Abstand
      if (disp_len(left) > maxleft) left = trunc_disp(left, maxleft);
      int gap = W - disp_len(left) - rl;
      if (gap < 1) gap = 1;

      if (!out.empty()) out += "\n";
      out += left;
      out.append(gap, ' ');
      out += minbuf;
      rows++;
    }
  }
  if (out.empty()) out = "-- keine Daten --";
  ESP_LOGD("vvo", "render %d rows, now_s=%lld:\n%s", rows, now_s, out.c_str());
  lv_label_set_text(label, out.c_str());
}

}  // namespace vvo
