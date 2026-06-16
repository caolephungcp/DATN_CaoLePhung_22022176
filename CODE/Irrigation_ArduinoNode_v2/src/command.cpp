// ============================================================================
// COMMAND HANDLER IMPLEMENTATION
// ============================================================================

#include "command.h"
#include "config.h"
#include "lora_module.h"
#include <LoRa.h>

extern bool pumpState;
extern bool valveState;
extern unsigned long manualOverrideTimer;

void processCmd(const String &cmd) {
  Serial.println("Processing command: " + cmd);

  // Check for manual override
  if (manualOverrideTimer > 0) {
    String msg = GATE_ID + "-" + NODE_ID + "-MANUAL_OVERRIDE_ACTIVE-" + String(manualOverrideTimer);
    LoRa.beginPacket();
    LoRa.print(msg);
    LoRa.endPacket();
    Serial.println("Cmd reject (manual override):" + msg);
    LoRa.receive();
    return;
  }

  if (cmd.indexOf("F1_P1") >= 0) {
    int val = cmd.substring(cmd.lastIndexOf('-') + 1).toInt();
    if(val == 1) {
      setPump(true);
    } else {
      setPump(false);
    }
    delay(1000); 
    lora_send("ACK_F1_P1");
  }
  if (cmd.indexOf("F1_P2") >= 0) {
    int val = cmd.substring(cmd.lastIndexOf('-') + 1).toInt();
    if(val == 1) {
      setValve(true);
    } else {
      setValve(false);
    }
    delay(1000);
    lora_send("ACK_F1_P2");
  }
}

void setPump(bool on) {
  pumpState = on;
  digitalWrite(PUMP_RELAY, on ? HIGH : LOW);
  Serial.println("Pump set to: " + String(on ? "ON" : "OFF"));
}

void setValve(bool on) {
  valveState = on;
  digitalWrite(VALVE_RELAY, on ? HIGH : LOW);
  Serial.println("Valve set to: " + String(on ? "ON" : "OFF"));
}