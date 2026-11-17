/*
  Solar Panel Cleaning Robot - ESP32 + Blynk IoT
  --------------------------------------------------------------
  - 2 x DC gear motors via L298N (differential / tank drive)
  - Brush roller motor via a transistor / MOSFET (PWM)
  - HC-SR04 ultrasonic (points DOWN at the glass) -> edge detection
  - IR obstacle sensor (points FORWARD)           -> obstacle avoidance
  - Blynk IoT app: joystick, auto mode, brush switch, speed slider

  Blynk datastreams (create these in your template):
    V0  Joystick (Merge mode, range -100..100 for X and Y, auto-return ON)
    V1  Auto mode switch       (Integer 0..1)
    V2  Brush switch           (Integer 0..1)
    V3  Speed slider           (Integer 100..255, default 180)
    V4  Status label           (String)

  Libraries: "Blynk" by Volodymyr Shymanskyy
  Board:     ESP32 Dev Module (esp32 by Espressif)
*/

// ====== BLYNK CREDENTIALS (paste yours) ======
#define BLYNK_TEMPLATE_ID "TMPL2OVx7Yecb"
#define BLYNK_TEMPLATE_NAME "solar cleaner"
#define BLYNK_AUTH_TOKEN "3pxxyje_kUnrgxhjnd9Npl6E_ygZazoR"
#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>

char ssid[] = "E36 M52B28";
char pass[] = "MULTIVALVE";

// ====== PIN MAP ======
// L298N
const int ENA = 25;   // left motor speed (PWM)  - remove ENA jumper on L298N
const int IN1 = 26;
const int IN2 = 27;
const int IN3 = 14;
const int IN4 = 13;
const int ENB = 33;   // right motor speed (PWM) - remove ENB jumper on L298N

// Brush motor driver (transistor / MOSFET gate)
const int BRUSH_PIN = 19;

// HC-SR04 (ECHO must go through a voltage divider!)
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;

// IR obstacle sensor (OUT goes LOW when an obstacle is detected)
const int IR_PIN = 34;

// ====== PWM SETTINGS ======
const int PWM_FREQ = 2000;
const int PWM_RES  = 8;      // 0..255
const int CH_ENA = 0, CH_ENB = 1, CH_BRUSH = 2;   // used by older ESP32 cores

// ====== TUNING ======
const bool INVERT_LEFT  = false;   // set true if left wheel spins the wrong way
const bool INVERT_RIGHT = false;   // set true if right wheel spins the wrong way
const float EDGE_MARGIN_CM = 3.0;  // reading above (ground + margin) = edge
const int   DEADZONE       = 15;   // joystick deadzone (of 100)
const unsigned long REVERSE_MS       = 500;
const unsigned long TURN_OBSTACLE_MS = 450;
const unsigned long TURN_EDGE_MS     = 700;
const int BRUSH_DUTY = 220;        // brush motor speed 0..255

// ====== STATE ======
BlynkTimer timer;

int  joyX = 0, joyY = 0;
int  driveSpeed = 180;
bool autoMode = false;
bool brushOn  = false;
bool needCalibrate = true;

float groundCm    = 4.0;   // measured distance to glass (auto-calibrated)
float edgeLimitCm = 7.0;
float distanceCm  = 0;
int   edgeCount   = 0;
bool  edgeDetected     = false;
bool  obstacleDetected = false;

enum AutoState { A_FORWARD, A_REVERSE, A_TURN };
AutoState autoState = A_FORWARD;
unsigned long stateStart = 0;
unsigned long turnDuration = 0;
int  turnDir = 1;            // +1 = right, -1 = left (alternates)
bool lastWasEdge = false;

// ====== PWM HELPERS (work on ESP32 core 2.x and 3.x) ======
void pwmSetup(int pin, int ch) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(pin, PWM_FREQ, PWM_RES);
#else
  ledcSetup(ch, PWM_FREQ, PWM_RES);
  ledcAttachPin(pin, ch);
#endif
}

void pwmWrite(int pin, int ch, int duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(pin, duty);
#else
  ledcWrite(ch, duty);
#endif
}

// ====== MOTOR CONTROL ======
void driveMotor(int inA, int inB, int en, int ch, int speed) {
  if (speed > 0)      { digitalWrite(inA, HIGH); digitalWrite(inB, LOW);  }
  else if (speed < 0) { digitalWrite(inA, LOW);  digitalWrite(inB, HIGH); }
  else                { digitalWrite(inA, LOW);  digitalWrite(inB, LOW);  }
  pwmWrite(en, ch, constrain(abs(speed), 0, 255));
}

// speeds: -255..255 (negative = reverse)
void setMotors(int left, int right) {
  if (INVERT_LEFT)  left  = -left;
  if (INVERT_RIGHT) right = -right;
  driveMotor(IN1, IN2, ENA, CH_ENA, left);
  driveMotor(IN3, IN4, ENB, CH_ENB, right);
}

void stopMotors() { setMotors(0, 0); }

void applyBrush() {
  pwmWrite(BRUSH_PIN, CH_BRUSH, brushOn ? BRUSH_DUTY : 0);
}

// ====== SENSORS ======
float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long dur = pulseIn(ECHO_PIN, HIGH, 12000UL);  // ~2 m timeout
  if (dur == 0) return 999.0;                            // no echo = nothing below = edge
  return dur * 0.0343 / 2.0;
}

void calibrateGround() {
  float sum = 0;
  int n = 0;
  for (int i = 0; i < 10; i++) {
    float d = readDistanceCm();
    if (d < 40.0) { sum += d; n++; }
    delay(60);
  }
  if (n >= 5) {
    groundCm = sum / n;
    edgeLimitCm = groundCm + EDGE_MARGIN_CM;
    Serial.printf("Calibrated: ground = %.1f cm, edge limit = %.1f cm\n", groundCm, edgeLimitCm);
  } else {
    Serial.println("Calibration FAILED - check ultrasonic angle/height. Keeping old values.");
  }
  edgeCount = 0;
}

void updateSensors() {
  static unsigned long last = 0;
  if (millis() - last >= 50) {
    last = millis();
    distanceCm = readDistanceCm();
    if (distanceCm > edgeLimitCm) edgeCount++; else edgeCount = 0;
    edgeDetected = (edgeCount >= 2);          // 2 readings in a row = real edge
  }
  obstacleDetected = (digitalRead(IR_PIN) == LOW);
}

// ====== MANUAL MODE (joystick tank mixing) ======
void runManual() {
  int x = joyX, y = joyY;
  if (abs(x) < DEADZONE) x = 0;
  if (abs(y) < DEADZONE) y = 0;

  if (edgeDetected && y > 0) y = 0;           // safety: never drive forward off the edge

  int left  = constrain(y + x, -100, 100);
  int right = constrain(y - x, -100, 100);
  setMotors(left * driveSpeed / 100, right * driveSpeed / 100);
}

// ====== AUTO MODE ======
void runAuto() {
  switch (autoState) {

    case A_FORWARD:
      if (edgeDetected || obstacleDetected) {
        lastWasEdge = edgeDetected;
        stateStart = millis();
        autoState = A_REVERSE;
      } else {
        setMotors(driveSpeed, driveSpeed);
      }
      break;

    case A_REVERSE:
      setMotors(-driveSpeed, -driveSpeed);
      if (millis() - stateStart >= REVERSE_MS) {
        turnDir = -turnDir;                    // alternate left / right
        turnDuration = lastWasEdge ? TURN_EDGE_MS : TURN_OBSTACLE_MS;
        stateStart = millis();
        autoState = A_TURN;
      }
      break;

    case A_TURN:
      setMotors(turnDir * driveSpeed, -turnDir * driveSpeed);
      if (millis() - stateStart >= turnDuration) {
        autoState = A_FORWARD;
      }
      break;
  }
}

void setAutoMode(bool on) {
  stopMotors();
  autoMode = on;
  autoState = A_FORWARD;
  joyX = joyY = 0;
  if (on) needCalibrate = true;               // re-measure glass distance on the panel
}

// ====== BLYNK ======
BLYNK_CONNECTED() {
  Blynk.virtualWrite(V1, 0);                  // app switches start OFF (safe)
  Blynk.virtualWrite(V2, 0);
  Blynk.syncVirtual(V3);
}

BLYNK_WRITE(V0) { joyX = param[0].asInt(); joyY = param[1].asInt(); }
BLYNK_WRITE(V1) { setAutoMode(param.asInt() == 1); }
BLYNK_WRITE(V2) { brushOn = (param.asInt() == 1); applyBrush(); }
BLYNK_WRITE(V3) { driveSpeed = constrain(param.asInt(), 0, 255); }

void sendStatus() {
  String s = autoMode ? "AUTO" : "MANUAL";
  s += " | Dist ";
  s += (distanceCm > 100) ? String("--") : String(distanceCm, 1);
  s += "cm | ";
  if (edgeDetected)          s += "EDGE!";
  else if (obstacleDetected) s += "OBSTACLE";
  else                       s += "OK";
  Blynk.virtualWrite(V4, s);

  Serial.println(s);
}

// ====== SETUP / LOOP ======
void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(IR_PIN, INPUT);

  pwmSetup(ENA, CH_ENA);
  pwmSetup(ENB, CH_ENB);
  pwmSetup(BRUSH_PIN, CH_BRUSH);
  stopMotors();
  applyBrush();

  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);   // blocks until Wi-Fi + Blynk connect
  timer.setInterval(1000L, sendStatus);
}

void loop() {
  Blynk.run();
  timer.run();

  if (needCalibrate) {
    stopMotors();
    calibrateGround();
    needCalibrate = false;
  }

  updateSensors();

  if (autoMode)               runAuto();
  else if (Blynk.connected()) runManual();
  else                        stopMotors();   // lost connection in manual = stop
}
