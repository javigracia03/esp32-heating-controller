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

#include <WiFi.h>
#include <WebServer.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASS";

WebServer server(80);

// ---- Optional Basic Auth ----
#define USE_BASIC_AUTH 0
const char* BASIC_USER = "admin";
const char* BASIC_PASS = "changeme";

// ---- GPIO (change to your wiring) ----
static const int PIN_RELAY_UP   = 26;
static const int PIN_RELAY_DOWN = 27;

// Relay logic: some relay boards are ACTIVE LOW.
// If your relays trigger when writing LOW, set RELAY_ACTIVE_LOW = true.
static const bool RELAY_ACTIVE_LOW = true;

enum class MotionState { Stopped, MovingUp, MovingDown };
volatile MotionState g_state = MotionState::Stopped;

static inline void relayWrite(int pin, bool on) {
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(pin, on ? LOW : HIGH);
  } else {
    digitalWrite(pin, on ? HIGH : LOW);
  }
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
    String s = stateToString(g_state);
    sendJson(200, String("{\"state\":\"") + s + "\"}");
  });

  server.on("/up", HTTP_POST, []() {
    if (!checkAuth()) return;
    moveUp();
    sendJson(200, "{\"ok\":true,\"action\":\"up\"}");
  });

  server.on("/down", HTTP_POST, []() {
    if (!checkAuth()) return;
    moveDown();
    sendJson(200, "{\"ok\":true,\"action\":\"down\"}");
  });

  server.on("/stop", HTTP_POST, []() {
    if (!checkAuth()) return;
    stopAll();
    sendJson(200, "{\"ok\":true,\"action\":\"stop\"}");
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
