/*
  ESP32 HTTP controller (Arduino)
  Endpoints:
    POST /up
    POST /down
    POST /stop
    GET  /state
    GET  /health

  Optional Basic Auth: set USE_BASIC_AUTH to 1
*/

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>


// WiFi credentials: prefer build-time macros supplied via PlatformIO build_flags.
#ifndef WIFI_SSID_STR
const char* WIFI_SSID = "MOVISTAR_5443";
#else
const char* WIFI_SSID = WIFI_SSID_STR;
#endif

#ifndef WIFI_PASS_STR
const char* WIFI_PASS = "jEwaCtcWpzSwdKDbErxH";
#else
const char* WIFI_PASS = WIFI_PASS_STR;
#endif

ESP8266WebServer server(80);

// ---- Optional Basic Auth ----
#ifndef USE_BASIC_AUTH
#define USE_BASIC_AUTH 0
#endif

#ifndef BASIC_USER_STR
const char* BASIC_USER = "admin";
#else
const char* BASIC_USER = BASIC_USER_STR;
#endif

#ifndef BASIC_PASS_STR
const char* BASIC_PASS = "changeme";
#else
const char* BASIC_PASS = BASIC_PASS_STR;
#endif

// ---- GPIO (change to your wiring) ----
static const int PIN_RELAY_UP   = D1;
static const int PIN_RELAY_DOWN = D2;

// Relay logic: some relay boards are ACTIVE LOW.
// If your relays trigger when writing LOW, set RELAY_ACTIVE_LOW = true.
static const bool RELAY_ACTIVE_LOW = true;
const int RELAY_ON  = RELAY_ACTIVE_LOW ? LOW  : HIGH;
const int RELAY_OFF = RELAY_ACTIVE_LOW ? HIGH : LOW;

enum class MotionState { Stopped, MovingUp, MovingDown };
volatile MotionState g_state = MotionState::Stopped;

void relayWrite(int pin, bool on) {
  digitalWrite(pin, on ? RELAY_ON : RELAY_OFF);
}

static void stopAll() {
  relayWrite(PIN_RELAY_UP, false);
  relayWrite(PIN_RELAY_DOWN, false);
  g_state = MotionState::Stopped;
}

static void moveUp() {
  // avoid both relays on
  relayWrite(PIN_RELAY_DOWN, false);
  relayWrite(PIN_RELAY_UP, true);
  g_state = MotionState::MovingUp;
}

static void moveDown() {
  relayWrite(PIN_RELAY_UP, false);
  relayWrite(PIN_RELAY_DOWN, true);
  g_state = MotionState::MovingDown;
}

static String stateToString(MotionState s) {
  switch (s) {
    case MotionState::MovingUp: return "up";
    case MotionState::MovingDown: return "down";
    default: return "stopped";
  }
}

static bool checkAuth() {
#if USE_BASIC_AUTH
  if (!server.authenticate(BASIC_USER, BASIC_PASS)) {
    server.requestAuthentication(); // 401 + WWW-Authenticate
    return false;
  }
#endif
  return true;
}

// Simple JSON response helper
static void sendJson(int code, const String& json) {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  server.send(code, "application/json", json);
}

// Handle preflight CORS
static void handleOptions() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  server.send(204);
}

void setupRoutes() {
  server.on("/health", HTTP_GET, []() {
    if (!checkAuth()) return;
    sendJson(200, "{\"ok\":true}");
  });

  server.on("/state", HTTP_GET, []() {
    if (!checkAuth()) return;
    // Report each relay independently (considering active-low logic)
    bool upOn = (digitalRead(PIN_RELAY_UP) == RELAY_ON);
    bool downOn = (digitalRead(PIN_RELAY_DOWN) == RELAY_ON);
    String json = String("{\"up\":") + (upOn ? "true" : "false") +
                  String(",\"down\":") + (downOn ? "true" : "false") + String("}");
    sendJson(200, json);
  });

  // turn UP on (does not touch DOWN)
  server.on("/up", HTTP_POST, []() {
    if (!checkAuth()) return;
    relayWrite(PIN_RELAY_UP, true);
    sendJson(200, "{\"ok\":true,\"action\":\"up_on\"}");
  });

  // turn DOWN on (does not touch UP)
  server.on("/down", HTTP_POST, []() {
    if (!checkAuth()) return;
    relayWrite(PIN_RELAY_DOWN, true);
    sendJson(200, "{\"ok\":true,\"action\":\"down_on\"}");
  });

  // stop — optional query param: relay=up|down|both (default both)
  server.on("/stop", HTTP_POST, []() {
    if (!checkAuth()) return;
    String which = server.arg("relay");
    if (which == "up") {
      relayWrite(PIN_RELAY_UP, false);
    } else if (which == "down") {
      relayWrite(PIN_RELAY_DOWN, false);
    } else {
      relayWrite(PIN_RELAY_UP, false);
      relayWrite(PIN_RELAY_DOWN, false);
    }
    sendJson(200, "{\"ok\":true,\"action\":\"stop\",\"which\":\"" + which + "\"}");
  });

  // CORS preflight for all endpoints (minimal)
  server.onNotFound([]() {
    if (server.method() == HTTP_OPTIONS) {
      handleOptions();
      return;
    }
    sendJson(404, "{\"error\":\"not_found\"}");
  });
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_RELAY_UP, OUTPUT);
  pinMode(PIN_RELAY_DOWN, OUTPUT);
  stopAll(); // ensure OFF at boot

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  setupRoutes();
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
}
