// Host-side test of the local command line assembly and the run-now or
// defer decision (TelemetryUnit/include/cmd_link.h, firmware v0.7.8).
// No ESP32 needed.
//
// Build and run on the laptop, from TelemetryUnit/:
//   g++ -std=c++11 -O1 -Wall -Iinclude test_host/test_cmd_link.cpp -o test_host/test_cmd_link
// Or: python test_host/run.py
#include <stdio.h>
#include <string>
#include <vector>

#include "cmd_link.h"

static int failures = 0;
static int checks = 0;
#define CHECK(cond)                                                       \
  do {                                                                    \
    checks++;                                                             \
    if (!(cond)) {                                                        \
      failures++;                                                         \
      printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);              \
    }                                                                     \
  } while (0)

// Feeds a byte string in link mode; returns the lines produced.
static std::vector<std::string> feedLink(const std::string& in) {
  CmdLineAssembler a;
  cmdAssemblerInit(a);
  std::vector<std::string> out;
  for (char c : in) {
    if (cmdFeedLink(a, c) == CMD_FEED_LINE) {
      out.push_back(std::string(a.buf, a.len));
      cmdAssemblerClear(a);
    }
  }
  return out;
}

// Console mode: lines produced, and the bytes forwarded to the modem.
static void feedConsole(const std::string& in, std::vector<std::string>* lines, std::string* fwd) {
  CmdLineAssembler a;
  cmdAssemblerInit(a);
  for (char c : in) {
    CmdFeed r = cmdFeedConsole(a, c);
    if (r == CMD_FEED_LINE) {
      lines->push_back(std::string(a.buf, a.len));
      cmdAssemblerClear(a);
    } else if (r == CMD_FEED_FORWARD) {
      fwd->push_back(c);
    }
  }
}

static std::string norm(const char* s) {
  char b[CMD_LINE_MAX + 8];
  snprintf(b, sizeof(b), "%s", s);
  cmdNormalize(b);
  return b;
}

int main() {
  // Link mode: the Pi sends "!raw off\n" (os.write), sometimes CRLF.
  {
    auto l = feedLink("!raw off\n");
    CHECK(l.size() == 1 && l[0] == "!raw off");
    l = feedLink("!raw off\r\n!raw on\r\n");
    CHECK(l.size() == 2 && l[0] == "!raw off" && l[1] == "!raw on");
    l = feedLink("noise\n!status\n");  // non-command lines dropped
    CHECK(l.size() == 1 && l[0] == "!status");
    l = feedLink("!\n");  // a lone '!' is ignored on the link (as in v0.7.7)
    CHECK(l.empty());
    l = feedLink("!raw o");  // no terminator yet: nothing
    CHECK(l.empty());
    l = feedLink("x!raw off\n");  // '!' not first
    CHECK(l.empty());
    l = feedLink("\n\n\r\r");
    CHECK(l.empty());
    // Over-long line: kept to CMD_LINE_MAX characters, still returned.
    std::string longCmd = "!" + std::string(100, 'a');
    l = feedLink(longCmd + "\n!dash on\n");
    CHECK(l.size() == 2 && l[0].size() == CMD_LINE_MAX && l[1] == "!dash on");
    // Split across reads (the task polls every 10 ms): same result.
    CmdLineAssembler a;
    cmdAssemblerInit(a);
    int got = 0;
    const char* parts[] = {"!ra", "w o", "ff", "\n"};
    for (const char* p : parts)
      for (const char* q = p; *q; q++)
        if (cmdFeedLink(a, *q) == CMD_FEED_LINE) {
          got++;
          CHECK(std::string(a.buf) == "!raw off");
          cmdAssemblerClear(a);
        }
    CHECK(got == 1);
  }

  // Console mode: AT pass-through unchanged, '!' lines local.
  {
    std::vector<std::string> lines;
    std::string fwd;
    feedConsole("AT+CSQ\r\n", &lines, &fwd);
    CHECK(lines.empty() && fwd == "AT+CSQ\r\n");

    lines.clear(); fwd.clear();
    feedConsole("!status\r\nAT\r\n", &lines, &fwd);
    CHECK(lines.size() == 1 && lines[0] == "!status");
    CHECK(fwd == "\nAT\r\n");  // the LF after the command's CR goes on, as in v0.7.7

    lines.clear(); fwd.clear();
    feedConsole("AT+X=\"!a\"\r\n", &lines, &fwd);  // '!' mid-line goes to the modem
    CHECK(lines.empty() && fwd == "AT+X=\"!a\"\r\n");

    lines.clear(); fwd.clear();
    feedConsole("!\n", &lines, &fwd);  // lone '!' reaches the handler (unknown command)
    CHECK(lines.size() == 1 && lines[0] == "!" && fwd.empty());

    lines.clear(); fwd.clear();
    feedConsole("!mqtt\n!modem off\n", &lines, &fwd);
    CHECK(lines.size() == 2 && lines[0] == "!mqtt" && lines[1] == "!modem off" && fwd.empty());

    lines.clear(); fwd.clear();
    feedConsole("!" + std::string(80, 'b') + "\n", &lines, &fwd);
    CHECK(lines.size() == 1 && lines[0].size() == CMD_LINE_MAX && fwd.empty());
  }

  // Normalize: trim and lowercase, like String::trim and toLowerCase.
  CHECK(norm("  !RAW Off \r") == "!raw off");
  CHECK(norm("!status") == "!status");
  CHECK(norm("") == "");
  CHECK(norm("   ") == "");
  CHECK(norm("\t!Dash ON\t") == "!dash on");

  // Classifier: the modem, MQTT, log and ledger commands are deferred.
  const char* deferred[] = {"!modem off", "!modem on", "!mqtt", "!agps", "!cellpos", "!log off",
                            "!log flush", "!log dump", "!log clear", "!sync drop", "!recal"};
  for (const char* d : deferred) CHECK(cmdIsDeferred(d));
  const char* now[] = {"!help", "!status", "!raw on", "!raw off", "!dash on", "!dash off", "!log on",
                       "!sync", "!gnssraw", "!", "!unknown", "!modem", "!log", "!mqtt now", "!recalx"};
  for (const char* n : now) CHECK(!cmdIsDeferred(n));
  // After normalizing, a shouted or padded deferred command is still deferred.
  {
    char b[32];
    snprintf(b, sizeof(b), "  !MODEM OFF\r");
    cmdNormalize(b);
    CHECK(cmdIsDeferred(b));
  }

  printf("test_cmd_link: %d checks, %d failures\n", checks, failures);
  return failures ? 1 : 0;
}
