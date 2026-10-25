// Local '!' command input: line assembly and the run-now or defer decision
// (firmware v0.7.8).
//
// Pure C++ with no Arduino or FreeRTOS dependency, so the same code is
// compiled into the firmware and into the host-side test
// (TelemetryUnit/test_host/test_cmd_link.cpp).
//
// Why (field finding of 22 Oct 2026): '!' commands from the Pi over the UART
// link were read in ModemTask's loop, which also runs the MQTT reconnect.
// With the modem attached but without network (CSQ 99), each reconnect step
// waits for its timeout, so a command was acted on only 20 to 25 s later.
// From v0.7.8 a small CommandTask reads the lines and runs at once every
// command that does not use the modem UART, the MQTT state, the flash log or
// the sync ledger; the rest go on a queue that ModemTask runs between its
// steps.
#pragma once
#include <stdint.h>
#include <string.h>

#define CMD_LINE_MAX 64  // characters kept per line; the rest of a longer line is dropped

struct CmdLineAssembler {
  char buf[CMD_LINE_MAX + 1];  // NUL-terminated
  uint8_t len;
  bool inCommand;   // console mode: a '!' line is being collected
  bool forwarding;  // console mode: mid-way through a line going to the modem
};

enum CmdFeed {
  CMD_FEED_NONE = 0,  // byte used (or dropped), nothing to do
  CMD_FEED_LINE,      // a complete command line is in buf (len characters)
  CMD_FEED_FORWARD,   // console mode: pass this byte on to the modem
};

inline void cmdAssemblerInit(CmdLineAssembler& a) {
  a.buf[0] = '\0';
  a.len = 0;
  a.inCommand = false;
  a.forwarding = false;
}

// Link mode (the Pi UART, and the front node's USB console): every line is
// collected; at CR or LF a line of 2 or more characters starting with '!' is
// returned, anything else is dropped. The same rule as v0.7.7's loops.
inline CmdFeed cmdFeedLink(CmdLineAssembler& a, char c) {
  if (c == '\n' || c == '\r') {
    const bool isCmd = a.len > 1 && a.buf[0] == '!';
    if (!isCmd) a.len = 0;
    a.buf[a.len] = '\0';
    return isCmd ? CMD_FEED_LINE : CMD_FEED_NONE;
  }
  if (a.len < CMD_LINE_MAX) {
    a.buf[a.len++] = c;
    a.buf[a.len] = '\0';
  }
  return CMD_FEED_NONE;
}

// Console mode (the rear unit's USB serial, which also carries AT
// pass-through): a '!' at the start of a line starts a local command, which
// ends at CR or LF and is returned whatever its length (a lone "!" gets the
// unknown-command reply, as before). Every other byte is forwarded to the
// modem. The same rule as v0.7.7's loop.
inline CmdFeed cmdFeedConsole(CmdLineAssembler& a, char c) {
  if (!a.forwarding && !a.inCommand && c == '!') {
    a.inCommand = true;
    a.buf[0] = '!';
    a.len = 1;
    a.buf[1] = '\0';
    return CMD_FEED_NONE;
  }
  if (a.inCommand) {
    if (c == '\n' || c == '\r') {
      a.inCommand = false;
      return CMD_FEED_LINE;
    }
    if (a.len < CMD_LINE_MAX) {
      a.buf[a.len++] = c;
      a.buf[a.len] = '\0';
    }
    return CMD_FEED_NONE;
  }
  a.forwarding = !(c == '\n' || c == '\r');
  return CMD_FEED_FORWARD;
}

// Call after handling a CMD_FEED_LINE, before the next byte.
inline void cmdAssemblerClear(CmdLineAssembler& a) {
  a.len = 0;
  a.buf[0] = '\0';
}

// Trims spaces and control characters at both ends and lowercases ASCII,
// in place (what the handler did with String::trim and toLowerCase).
inline void cmdNormalize(char* s) {
  size_t n = strlen(s);
  while (n > 0 && (unsigned char)s[n - 1] <= ' ') s[--n] = '\0';
  size_t start = 0;
  while (start < n && (unsigned char)s[start] <= ' ') start++;
  if (start > 0) memmove(s, s + start, n - start + 1);
  for (char* p = s; *p; p++) {
    if (*p >= 'A' && *p <= 'Z') *p = (char)(*p - 'A' + 'a');
  }
}

// Rear unit: true if the (normalized) command must run in ModemTask, because
// its handler uses the modem UART (Serial1), the MQTT or GNSS timers that
// ModemTask also writes, the flash log buffer or the sync ledger (written by
// ModemTask without a lock). Everything else, unknown commands included,
// only reads state or sets a single flag and runs at once in CommandTask.
//   !modem off / !modem on   Serial1 (AT+CPOF, AT probe, power key)
//   !mqtt, !mqtt off/on      mqttConnected and mqttNextAttemptMs; off tears the session down (Serial1)
//   !agps / !cellpos         agpsNextMs / cellLocNextMs (ModemTask writes them too)
//   !log off / !log flush    flushLocalLog (log buffer, ledger save)
//   !log dump                flushLocalLog, then a long paced file print
//   !log clear / !sync drop  ledger and replay offset
//   !recal                   flushLocalLog before the restart
inline bool cmdIsDeferred(const char* line) {
  static const char* const kDeferred[] = {
      "!modem off", "!modem on", "!mqtt",      "!mqtt off",  "!mqtt on",  "!agps",      "!cellpos", "!log off",
      "!log flush", "!log dump", "!log clear", "!sync drop", "!recal",
  };
  for (size_t i = 0; i < sizeof(kDeferred) / sizeof(kDeferred[0]); i++) {
    if (strcmp(line, kDeferred[i]) == 0) return true;
  }
  return false;
}
