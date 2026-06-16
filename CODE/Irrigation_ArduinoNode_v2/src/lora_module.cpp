// ============================================================================
// LORA MODULE HANDLER IMPLEMENTATION
// ============================================================================

#include "lora_module.h"
#include <LoRa.h>
#include "config.h"
#include "sensor.h"

extern bool pumpState;
extern bool valveState;
extern unsigned long manualOverrideTimer;

void lora_setup(){
  pinMode(A0, INPUT);

  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(LORA_FREQ * 1E6)) {
    Serial.println("LoRa init failed");
    while (1);
  }

  LoRa.setSyncWord(0x12);           
  LoRa.setSpreadingFactor(7);       
  LoRa.setSignalBandwidth(125E3);   
  LoRa.setCodingRate4(5);           
  LoRa.setPreambleLength(8); 
  LoRa.enableCrc();

  LoRa.receive();
}

void sendUplink(bool includeOverrides) {
  float h1, t1, p1, h2, t2, p2;
  readSensorData(SLAVE_ID_1, h1, t1, p1);
  readSensorData(SLAVE_ID_2, h2, t2, p2);
  String data = "F1_P1:" + String(pumpState ? 1 : 0);
  data += "-F1_P2:" + String(valveState ? 1 : 0);
  data += "-HUMI1:" + String(h1, 1) + "-TEMP1:" + String(t1, 1) + "-PH1:" + String(p1, 1);
  data += "-HUMI2:" + String(h2, 1) + "-TEMP2:" + String(t2, 1) + "-PH2:" + String(p2, 1);

  if (includeOverrides && manualOverrideTimer > 0) {
    data += "-MANUAL_OVERRIDE:" + String(manualOverrideTimer);
  }

  lora_send(data);
}

void lora_send(String payload) {
  LoRa.idle(); 
  LoRa.beginPacket();
  
  // Phần Header chung: GATE_ID-NODE_ID-
  LoRa.print("     ");
  LoRa.print(GATE_ID); 
  LoRa.print(F("-")); 
  LoRa.print(NODE_ID);
  LoRa.print(F("-"));
  LoRa.print(payload);
  
  if (LoRa.endPacket()) {
    Serial.println(F("lora_send: Success"));
    Serial.println(payload);
  } else {
    Serial.println(F("lora_send: Failed"));
  }

  LoRa.receive();
}