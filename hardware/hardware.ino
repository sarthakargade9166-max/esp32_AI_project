#include "Adafruit_VL53L0X.h"
#include <Wire.h>


static const uint8_t PIN_XSHUT_A = 18;
static const uint8_t PIN_XSHUT_B = 19;
static const uint8_t PIN_SDA = 21;
static const uint8_t PIN_SCL = 22;
static const uint8_t ADDR_SENSOR_A = 0x30;
static const uint8_t ADDR_SENSOR_B = 0x29;

static const uint8_t DEBOUNCE_TO_BLOCKED = 3;
static const uint8_t DEBOUNCE_TO_CLEAR = 4;
static const uint8_t INVALID_TIMEOUT_COUNT = 15;
static const uint32_t CROSSING_TIMEOUT_MS = 2000;
static const uint32_t WAIT_CLEAR_TIMEOUT_MS = 5000;
static const uint32_t SENSOR_READ_INTERVAL_MS = 50;
static const uint16_t MAX_VALID_RANGE_MM = 2000;
static const uint32_t SERIAL_BAUD = 115200;
static const uint8_t BLOCK_THRESHOLD_PERCENT = 35;
static const uint8_t CLEAR_THRESHOLD_PERCENT = 50;
static const uint16_t MANUAL_BLOCK_THRESHOLD_MM = 250;
static const uint16_t MANUAL_CLEAR_THRESHOLD_MM = 350;
static const uint8_t CALIBRATION_SAMPLES = 30;
static const uint16_t MIN_THRESHOLD_MM = 80;

typedef enum { MEAS_VALID, MEAS_OUT_OF_RANGE, MEAS_INVALID } MeasClass_t;
typedef enum { BEAM_CLEAR, BEAM_BLOCKED } BeamState_t;
typedef enum { SEVT_NONE, SEVT_TRIGGERED, SEVT_CLEARED } SensorEvent_t;

typedef struct {
  Adafruit_VL53L0X *driver;
  BeamState_t beamState;
  uint8_t blockedCount;
  uint8_t clearCount;
  uint8_t invalidCount;
  uint16_t distanceMM;
  MeasClass_t lastMeasClass;
  uint16_t baselineMM;
  uint16_t thresholdBlockMM;
  uint16_t thresholdClearMM;
  const char *label;
} SensorData_t;

typedef enum {
  DIR_IDLE,
  DIR_WAITING_FOR_B,
  DIR_WAITING_FOR_A,
  DIR_WAIT_CLEAR
} DirectionState_t;

typedef enum {
  EVENT_NONE,
  EVENT_ENTER,
  EVENT_EXIT,
  EVENT_TIMEOUT
} SystemEvent_t;

Adafruit_VL53L0X driverA = Adafruit_VL53L0X();
Adafruit_VL53L0X driverB = Adafruit_VL53L0X();

SensorData_t sensorA = {&driverA,
                        BEAM_CLEAR,
                        0,
                        0,
                        0,
                        0,
                        MEAS_INVALID,
                        0,
                        MANUAL_BLOCK_THRESHOLD_MM,
                        MANUAL_CLEAR_THRESHOLD_MM,
                        "A"};
SensorData_t sensorB = {&driverB,
                        BEAM_CLEAR,
                        0,
                        0,
                        0,
                        0,
                        MEAS_INVALID,
                        0,
                        MANUAL_BLOCK_THRESHOLD_MM,
                        MANUAL_CLEAR_THRESHOLD_MM,
                        "B"};

DirectionState_t directionState = DIR_IDLE;
uint32_t stateEnteredAt = 0;
uint32_t lastReadTime = 0;
int32_t queueCount = 0;

void initializeSensors();
void calibrateSensor(SensorData_t *s);
MeasClass_t classifyReading(SensorData_t *s);
SensorEvent_t processSensorState(SensorData_t *s, bool clearOnly);
SystemEvent_t processDirection(SensorEvent_t evtA, SensorEvent_t evtB);
void resetDirectionFSM();
void handleEvent(SystemEvent_t evt);
void printDebug(SensorEvent_t evtA, SensorEvent_t evtB);
void printBanner(const char *message);
const char *measClassName(MeasClass_t c);
const char *beamStateName(BeamState_t b);
const char *dirStateName(DirectionState_t d);

void setup() {
  Serial.begin(SERIAL_BAUD);
  while (!Serial) {
    delay(10);
  }

  Serial.println();
  Serial.println(F("========================================="));
  Serial.println(F("  AI-Based Smart Queue Prediction System"));
  Serial.println(F("  Firmware v4.3 (Event Generation Fix)"));
  Serial.println(F("========================================="));
  Serial.println();

  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(100000);

  initializeSensors();

  Serial.println(F("[CAL]  *** Ensure the corridor is CLEAR ***"));
  Serial.println(F("[CAL]  Calibrating in 1 second...\n"));
  delay(1000);

  calibrateSensor(&sensorA);
  calibrateSensor(&sensorB);

  sensorA.beamState = BEAM_CLEAR;
  sensorA.blockedCount = 0;
  sensorA.clearCount = 0;
  sensorA.invalidCount = 0;

  sensorB.beamState = BEAM_CLEAR;
  sensorB.blockedCount = 0;
  sensorB.clearCount = 0;
  sensorB.invalidCount = 0;

  Serial.println();
  Serial.print(F("[BOOT] A: baseline="));
  Serial.print(sensorA.baselineMM);
  Serial.print(F("mm  block<"));
  Serial.print(sensorA.thresholdBlockMM);
  Serial.print(F("mm  clear>"));
  Serial.print(sensorA.thresholdClearMM);
  Serial.println(F("mm"));
  Serial.print(F("[BOOT] B: baseline="));
  Serial.print(sensorB.baselineMM);
  Serial.print(F("mm  block<"));
  Serial.print(sensorB.thresholdBlockMM);
  Serial.print(F("mm  clear>"));
  Serial.print(sensorB.thresholdClearMM);
  Serial.println(F("mm"));
  Serial.println(F("[BOOT] System ready.\n"));
}

void loop() {
  uint32_t now = millis();
  if (now - lastReadTime < SENSOR_READ_INTERVAL_MS) {
    return;
  }
  lastReadTime = now;

  bool clearing = (directionState == DIR_WAIT_CLEAR);

  SensorEvent_t evtA = processSensorState(&sensorA, clearing);
  SensorEvent_t evtB = processSensorState(&sensorB, clearing);
  SystemEvent_t sysEvt = processDirection(evtA, evtB);
  handleEvent(sysEvt);
  printDebug(evtA, evtB);
}

void initializeSensors() {
  pinMode(PIN_XSHUT_A, OUTPUT);
  pinMode(PIN_XSHUT_B, OUTPUT);

  digitalWrite(PIN_XSHUT_A, LOW);
  digitalWrite(PIN_XSHUT_B, LOW);
  delay(100);

  digitalWrite(PIN_XSHUT_A, HIGH);
  delay(100);
  if (!sensorA.driver->begin(ADDR_SENSOR_A, false, &Wire,
                             Adafruit_VL53L0X::VL53L0X_SENSE_DEFAULT)) {
    Serial.println(F("[FATAL] Sensor A (0x30) FAILED. Retrying..."));
    delay(100);
    if (!sensorA.driver->begin(ADDR_SENSOR_A, false, &Wire,
                               Adafruit_VL53L0X::VL53L0X_SENSE_DEFAULT)) {
      Serial.println(F("[FATAL] Sensor A (0x30) FAILED permanently. Halting."));
      while (true) {
        delay(1000);
      }
    }
  }
  sensorA.driver->setMeasurementTimingBudgetMicroSeconds(33000);
  Serial.println(F("[INIT]  Sensor A online at 0x30"));

  digitalWrite(PIN_XSHUT_B, HIGH);
  delay(100);
  if (!sensorB.driver->begin(ADDR_SENSOR_B, false, &Wire,
                             Adafruit_VL53L0X::VL53L0X_SENSE_DEFAULT)) {
    Serial.println(F("[FATAL] Sensor B (0x29) FAILED. Retrying..."));
    delay(100);
    if (!sensorB.driver->begin(ADDR_SENSOR_B, false, &Wire,
                               Adafruit_VL53L0X::VL53L0X_SENSE_DEFAULT)) {
      Serial.println(F("[FATAL] Sensor B (0x29) FAILED permanently. Halting."));
      while (true) {
        delay(1000);
      }
    }
  }
  sensorB.driver->setMeasurementTimingBudgetMicroSeconds(33000);
  Serial.println(F("[INIT]  Sensor B online at 0x29\n"));
}

void calibrateSensor(SensorData_t *s) {
  uint32_t sum = 0;
  uint8_t valid = 0;

  Serial.print(F("[CAL]  Sensor "));
  Serial.print(s->label);
  Serial.println(F(": warming up and sampling..."));

  for (uint8_t i = 0; i < 5; i++) {
    classifyReading(s);
    delay(40);
  }

  for (uint8_t i = 0; i < CALIBRATION_SAMPLES; i++) {
    MeasClass_t cls = classifyReading(s);
    if ((cls == MEAS_VALID || cls == MEAS_OUT_OF_RANGE) && s->distanceMM > 0) {
      sum += s->distanceMM;
      valid++;
    }
    delay(40);
  }

  if (valid >= 5) {
    uint16_t baseline = (uint16_t)(sum / valid);
    s->baselineMM = baseline;

    uint16_t blk =
        (uint16_t)((uint32_t)baseline * BLOCK_THRESHOLD_PERCENT / 100);
    uint16_t clr =
        (uint16_t)((uint32_t)baseline * CLEAR_THRESHOLD_PERCENT / 100);

    s->thresholdBlockMM = (blk >= MIN_THRESHOLD_MM) ? blk : MIN_THRESHOLD_MM;
    s->thresholdClearMM = (clr >= MIN_THRESHOLD_MM) ? clr : MIN_THRESHOLD_MM;

    if (s->thresholdClearMM <= s->thresholdBlockMM) {
      s->thresholdClearMM = s->thresholdBlockMM + 50;
    }

    Serial.print(F("[CAL]  Sensor "));
    Serial.print(s->label);
    Serial.print(F(": OK ("));
    Serial.print(valid);
    Serial.print(F("/"));
    Serial.print(CALIBRATION_SAMPLES);
    Serial.print(F(" valid) baseline="));
    Serial.print(baseline);
    Serial.print(F("mm  block<"));
    Serial.print(s->thresholdBlockMM);
    Serial.print(F("mm  clear>"));
    Serial.print(s->thresholdClearMM);
    Serial.println(F("mm"));
  } else {
    s->baselineMM = 0;
    s->thresholdBlockMM = MANUAL_BLOCK_THRESHOLD_MM;
    s->thresholdClearMM = MANUAL_CLEAR_THRESHOLD_MM;
    Serial.print(F("[CAL]  Sensor "));
    Serial.print(s->label);
    Serial.print(F(": FAILED ("));
    Serial.print(valid);
    Serial.print(F(" valid). Fallback block<"));
    Serial.print(MANUAL_BLOCK_THRESHOLD_MM);
    Serial.print(F("mm clear>"));
    Serial.print(MANUAL_CLEAR_THRESHOLD_MM);
    Serial.println(F("mm"));
  }
}

MeasClass_t classifyReading(SensorData_t *s) {
  VL53L0X_RangingMeasurementData_t measure;
  s->driver->rangingTest(&measure, false);

  if (measure.RangeStatus != 0) {
    if (measure.RangeStatus == 4 || measure.RangeStatus == 2) {
      s->distanceMM = 8190;
      s->lastMeasClass = MEAS_OUT_OF_RANGE;
      return MEAS_OUT_OF_RANGE;
    }
    s->distanceMM = 0;
    s->lastMeasClass = MEAS_INVALID;
    return MEAS_INVALID;
  }

  uint16_t range = measure.RangeMilliMeter;
  if (range == 0) {
    s->distanceMM = 0;
    s->lastMeasClass = MEAS_INVALID;
    return MEAS_INVALID;
  }

  s->distanceMM = range;

  if (range > MAX_VALID_RANGE_MM || range >= 8000) {
    s->lastMeasClass = MEAS_OUT_OF_RANGE;
    return MEAS_OUT_OF_RANGE;
  }

  s->lastMeasClass = MEAS_VALID;
  return MEAS_VALID;
}

SensorEvent_t processSensorState(SensorData_t *s, bool clearOnly) {
  MeasClass_t cls = classifyReading(s);

  if (cls == MEAS_INVALID) {
    if (s->beamState == BEAM_BLOCKED) {
      s->invalidCount++;
      if (s->invalidCount >= INVALID_TIMEOUT_COUNT) {
        s->beamState = BEAM_CLEAR;
        s->blockedCount = 0;
        s->clearCount = 0;
        s->invalidCount = 0;
        return SEVT_CLEARED;
      }
    }
    return SEVT_NONE;
  }

  s->invalidCount = 0;

  bool objectPresent = false;

  if (clearOnly) {
    objectPresent = false;
  } else if (cls == MEAS_VALID) {
    if (s->beamState == BEAM_CLEAR) {
      objectPresent = (s->distanceMM < s->thresholdBlockMM);
    } else {
      objectPresent = (s->distanceMM < s->thresholdClearMM);
    }
  } else if (cls == MEAS_OUT_OF_RANGE) {
    objectPresent = false;
  }

  switch (s->beamState) {

  case BEAM_CLEAR:
    if (objectPresent) {
      s->blockedCount++;
      s->clearCount = 0;
      if (s->blockedCount >= DEBOUNCE_TO_BLOCKED) {
        s->beamState = BEAM_BLOCKED;
        s->blockedCount = 0;
        s->clearCount = 0;
        return SEVT_TRIGGERED;
      }
    } else {
      s->blockedCount = 0;
    }
    break;

  case BEAM_BLOCKED:
    if (!objectPresent) {
      s->clearCount++;
      s->blockedCount = 0;
      if (s->clearCount >= DEBOUNCE_TO_CLEAR) {
        s->beamState = BEAM_CLEAR;
        s->clearCount = 0;
        s->blockedCount = 0;
        return SEVT_CLEARED;
      }
    } else {
      s->clearCount = 0;
    }
    break;
  }

  return SEVT_NONE;
}

SystemEvent_t processDirection(SensorEvent_t evtA, SensorEvent_t evtB) {
  uint32_t now = millis();

  switch (directionState) {

  case DIR_IDLE:
    if (evtA == SEVT_TRIGGERED && evtB != SEVT_TRIGGERED) {
      directionState = DIR_WAITING_FOR_B;
      stateEnteredAt = now;
      Serial.println(F("\n>> Sensor A TRIGGERED -> waiting for B...\n"));
      return EVENT_NONE;
    }
    if (evtB == SEVT_TRIGGERED && evtA != SEVT_TRIGGERED) {
      directionState = DIR_WAITING_FOR_A;
      stateEnteredAt = now;
      Serial.println(F("\n>> Sensor B TRIGGERED -> waiting for A...\n"));
      return EVENT_NONE;
    }
    return EVENT_NONE;

  case DIR_WAITING_FOR_B:
    if (evtB == SEVT_TRIGGERED) {
      directionState = DIR_WAIT_CLEAR;
      stateEnteredAt = now;
      return EVENT_ENTER;
    }
    if (now - stateEnteredAt >= CROSSING_TIMEOUT_MS) {
      resetDirectionFSM();
      return EVENT_TIMEOUT;
    }
    return EVENT_NONE;

  case DIR_WAITING_FOR_A:
    if (evtA == SEVT_TRIGGERED) {
      directionState = DIR_WAIT_CLEAR;
      stateEnteredAt = now;
      return EVENT_EXIT;
    }
    if (now - stateEnteredAt >= CROSSING_TIMEOUT_MS) {
      resetDirectionFSM();
      return EVENT_TIMEOUT;
    }
    return EVENT_NONE;

  case DIR_WAIT_CLEAR:
    if (sensorA.beamState == BEAM_CLEAR && sensorB.beamState == BEAM_CLEAR) {
      Serial.println(F(">> Both CLEAR -> IDLE\n"));
      resetDirectionFSM();
      return EVENT_NONE;
    }
    if (now - stateEnteredAt >= WAIT_CLEAR_TIMEOUT_MS) {
      Serial.println(F(">> WAIT_CLEAR timeout -> forcing IDLE\n"));
      sensorA.beamState = BEAM_CLEAR;
      sensorA.blockedCount = 0;
      sensorA.clearCount = 0;
      sensorA.invalidCount = 0;
      sensorB.beamState = BEAM_CLEAR;
      sensorB.blockedCount = 0;
      sensorB.clearCount = 0;
      sensorB.invalidCount = 0;
      resetDirectionFSM();
      return EVENT_NONE;
    }
    return EVENT_NONE;

  default:
    resetDirectionFSM();
    return EVENT_NONE;
  }
}

void resetDirectionFSM() {
  directionState = DIR_IDLE;
  stateEnteredAt = 0;
}

void handleEvent(SystemEvent_t evt) {
  switch (evt) {
  case EVENT_ENTER:
    queueCount++;
    printBanner("ENTER DETECTED");
    Serial.print(F("   Queue Count: "));
    Serial.println(queueCount);
    Serial.println();
    break;

  case EVENT_EXIT:
    if (queueCount > 0)
      queueCount--;
    printBanner("EXIT DETECTED");
    Serial.print(F("   Queue Count: "));
    Serial.println(queueCount);
    Serial.println();
    break;

  case EVENT_TIMEOUT:
    Serial.println(F("\n!! Timeout - incomplete crossing.\n"));
    break;

  case EVENT_NONE:
  default:
    break;
  }
}

void printBanner(const char *message) {
  Serial.println();
  Serial.println(F("========================="));
  Serial.print(F("  "));
  Serial.println(message);
  Serial.println(F("========================="));
}

void printDebug(SensorEvent_t evtA, SensorEvent_t evtB) {
  Serial.print(F("A:"));
  if (sensorA.distanceMM > 0) {
    if (sensorA.distanceMM < 1000)
      Serial.print(' ');
    if (sensorA.distanceMM < 100)
      Serial.print(' ');
    Serial.print(sensorA.distanceMM);
    Serial.print(F("mm"));
  } else {
    Serial.print(F("  ---"));
  }
  Serial.print(' ');
  Serial.print(measClassName(sensorA.lastMeasClass));
  Serial.print(F(" ["));
  Serial.print(beamStateName(sensorA.beamState));
  Serial.print(']');
  if (sensorA.beamState == BEAM_CLEAR && sensorA.blockedCount > 0) {
    Serial.print('(');
    Serial.print(sensorA.blockedCount);
    Serial.print(F("/3)"));
  } else if (sensorA.beamState == BEAM_BLOCKED && sensorA.clearCount > 0) {
    Serial.print('(');
    Serial.print(sensorA.clearCount);
    Serial.print(F("/4)"));
  }
  if (evtA == SEVT_TRIGGERED)
    Serial.print(F(" ^TRIG"));
  else if (evtA == SEVT_CLEARED)
    Serial.print(F(" vCLR"));

  Serial.print(F(" | B:"));
  if (sensorB.distanceMM > 0) {
    if (sensorB.distanceMM < 1000)
      Serial.print(' ');
    if (sensorB.distanceMM < 100)
      Serial.print(' ');
    Serial.print(sensorB.distanceMM);
    Serial.print(F("mm"));
  } else {
    Serial.print(F("  ---"));
  }
  Serial.print(' ');
  Serial.print(measClassName(sensorB.lastMeasClass));
  Serial.print(F(" ["));
  Serial.print(beamStateName(sensorB.beamState));
  Serial.print(']');
  if (sensorB.beamState == BEAM_CLEAR && sensorB.blockedCount > 0) {
    Serial.print('(');
    Serial.print(sensorB.blockedCount);
    Serial.print(F("/3)"));
  } else if (sensorB.beamState == BEAM_BLOCKED && sensorB.clearCount > 0) {
    Serial.print('(');
    Serial.print(sensorB.clearCount);
    Serial.print(F("/4)"));
  }
  if (evtB == SEVT_TRIGGERED)
    Serial.print(F(" ^TRIG"));
  else if (evtB == SEVT_CLEARED)
    Serial.print(F(" vCLR"));

  Serial.print(F(" | "));
  Serial.println(dirStateName(directionState));
}

const char *measClassName(MeasClass_t c) {
  switch (c) {
  case MEAS_VALID:
    return "VALID";
  case MEAS_OUT_OF_RANGE:
    return "OOR  ";
  case MEAS_INVALID:
    return "INVAL";
  default:
    return "?    ";
  }
}

const char *beamStateName(BeamState_t b) {
  switch (b) {
  case BEAM_CLEAR:
    return "CLEAR  ";
  case BEAM_BLOCKED:
    return "BLOCKED";
  default:
    return "?      ";
  }
}

const char *dirStateName(DirectionState_t d) {
  switch (d) {
  case DIR_IDLE:
    return "IDLE";
  case DIR_WAITING_FOR_B:
    return "WAIT_B";
  case DIR_WAITING_FOR_A:
    return "WAIT_A";
  case DIR_WAIT_CLEAR:
    return "WAIT_CLEAR";
  default:
    return "?";
  }
}
