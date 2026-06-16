#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <SoftwareSerial.h>
#include <ModbusMaster.h>

#include "config.h"
#include "sensor.h"
#include "lora_module.h"
#include "command.h"

// Phần mềm serial cho 2 kênh RS485
SoftwareSerial rs485_1(RS485_1_RX, RS485_1_TX);
// SoftwareSerial rs485_2(RS485_2_RX, RS485_2_TX);

ModbusMaster node;

volatile bool loraPacketReceived = false;
volatile bool loraCommandPending = false;
volatile uint8_t loraCommandLength = 0;
volatile char loraCommandBuffer[200] = {0};
volatile bool ackReceived = false;
volatile bool eventTriggered = false;

unsigned long manualOverrideTimer = 0;
unsigned long lastTelemetrySent = 28000;
unsigned long uplinkSendTime = 0;
int uplinkRetryCount = 0;
bool waitingAck = false;

bool pumpState = false;
bool valveState = false;

void onButtonPressed() {
  eventTriggered = true;
  manualOverrideTimer = 1800; // 30 phút
}

void loraISR() {
  loraPacketReceived = true;
}

void setup() {
  Serial.begin(9600);

  pinMode(PUMP_RELAY, OUTPUT);
  pinMode(VALVE_RELAY, OUTPUT);
  digitalWrite(PUMP_RELAY, LOW);
  digitalWrite(VALVE_RELAY, LOW);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(A0), loraISR, RISING); // Ngắt khi DIO0 của LoRa trigger

  sensor_setup();
  lora_setup();

  Serial.println("Node v2 setup done.");
}

void processLoRaPacket() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String receivedData = "";
    while (LoRa.available()) {
      char c = (char)LoRa.read();
      if (c >= 32 && c <= 126) {
        receivedData += c;
      }
    }
    Serial.print("LoRa RX: ");
    Serial.println(receivedData);


    LoRa.receive();

    // Lưu lệnh để xử lý
    noInterrupts();
    loraCommandLength = receivedData.length();
    if (loraCommandLength < sizeof(loraCommandBuffer)) {
      receivedData.toCharArray((char *)loraCommandBuffer, loraCommandLength + 1);
      loraCommandPending = true;
    }
    interrupts();
  }
}

void processPendingLoRaCommand() {
  if (!loraCommandPending) {
    return;
  }

  noInterrupts();
  uint8_t len = loraCommandLength;
  char localCommand[200] = {0};
  if (len > 0 && len < sizeof(localCommand)) {
    memcpy(localCommand, (const void *)loraCommandBuffer, len);
    localCommand[len] = '\0';
  }
  loraCommandPending = false;
  interrupts();

  if (len == 0) {
    return;
  }

  String commandString = String(localCommand);
  commandString.trim();

  // Check if it's ACK from gateway
  if (commandString.indexOf("ACK") >= 0 && commandString.indexOf(GATE_ID) >= 0 && commandString.indexOf(NODE_ID) >= 0) {
    ackReceived = true;
    Serial.println("ACK received from gateway");
  }
  // Otherwise, process as command
  else if (commandString.indexOf(GATE_ID) >= 0 && commandString.indexOf(NODE_ID) >= 0 && (commandString.indexOf("F1_P1") >= 0 || commandString.indexOf("F1_P2") >= 0)) {
    processCmd(commandString);
  }
}

void loop() {
  // Xử lý ngắt LoRa
  if (digitalRead(A0) == HIGH) {
    loraPacketReceived = false;
    processLoRaPacket();
  }

  // Xử lý lệnh pending
  processPendingLoRaCommand();
/*
  // Kiểm tra manual override timer
  if (manualOverrideTimer > 0) {
    manualOverrideTimer--;
    if (manualOverrideTimer == 0) {
      Serial.println("Manual override expired");
    }
  }
*/
  // uplink mỗi 30 giây
  if (millis() - lastTelemetrySent >= 30000) { 
    lastTelemetrySent = millis();

    // Đọc cảm biến
    sendUplink(false); 
    // ACK
    waitingAck = true;
    uplinkSendTime = millis();
    uplinkRetryCount = 0;
    ackReceived = false;
  }

  
  if (waitingAck) {
    if (ackReceived) {
      Serial.println("Uplink ACK received");
      waitingAck = false;
    } else if (millis() - uplinkSendTime >= 5000) {
      uplinkRetryCount++;
      if (uplinkRetryCount < 3) {
        Serial.println("ACK timeout, retrying uplink...");
        sendUplink(false);
        uplinkSendTime = millis();
      } else {
        Serial.println("ACK failed after 3 retries");
        waitingAck = false;
      }
    }
  }

  delay(100);
}
