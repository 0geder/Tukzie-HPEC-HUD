// Position removed from the MQTT payload (firmware v0.7.5).
//
// The default broker is the public test.mosquitto.org, where anyone can
// subscribe to the topic, so the vehicle's position must not go there. The
// local log keeps the full record and the DASH line to the Pi keeps the
// position; only what is published is cleaned, live and replayed alike.
// Build with -D MQTT_INCLUDE_POSITION=1 (or define it in mqtt_secrets.h) to
// publish the position to a private broker.
//
// Pure C++, tested on the laptop by test_host/test_raw_stream.cpp.
#pragma once

#include <stddef.h>
#include <string.h>

// Copies the JSON text in into out without the members whose key is "lat",
// "lon" or "acc_m", wherever they are. Those members only ever hold a number
// or null in this firmware's record, so a member ends at the next ',' or '}'.
// Returns the length written, or 0 if out is too small (out is then "").
static inline size_t scrubPositionJson(const char* in, char* out, size_t cap) {
  static const char* const keys[] = {"\"lat\":", "\"lon\":", "\"acc_m\":"};
  if (cap == 0) return 0;
  size_t o = 0;
  const char* p = in;
  while (*p) {
    bool removed = false;
    if (*p == '"') {
      for (size_t k = 0; k < sizeof(keys) / sizeof(keys[0]); k++) {
        const size_t kl = strlen(keys[k]);
        if (strncmp(p, keys[k], kl) != 0) continue;
        const char* e = p + kl;
        while (*e && *e != ',' && *e != '}') e++;
        if (*e == ',') {
          e++;  // drop the member and the comma after it
        } else if (o > 0 && out[o - 1] == ',') {
          o--;  // last member of its object: drop the comma before it
        }
        p = e;
        removed = true;
        break;
      }
    }
    if (removed) continue;
    if (o + 1 >= cap) {
      out[0] = '\0';
      return 0;
    }
    out[o++] = *p++;
  }
  out[o] = '\0';
  return o;
}
