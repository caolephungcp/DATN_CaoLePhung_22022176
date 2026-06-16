// ============================================================================
// SENSOR HANDLER IMPLEMENTATION
// ============================================================================

#include "sensor.h"
#include "config.h"

void preTransmission() {
  digitalWrite(RS485_DE1, HIGH);
  digitalWrite(RS485_DE2, HIGH);
}

void postTransmission() {
  digitalWrite(RS485_DE1, LOW);
  digitalWrite(RS485_DE2, LOW);
}

void sensor_setup() {
  pinMode(POW_RS485, OUTPUT);
  digitalWrite(POW_RS485, HIGH);

  pinMode(RS485_DE1, OUTPUT);
  pinMode(RS485_DE2, OUTPUT);
  digitalWrite(RS485_DE1, LOW);
  digitalWrite(RS485_DE2, LOW);

  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);
}

void readSensorData(uint8_t slaveID, float &humi, float &temp, float &ph) {
  delay(1000);
  if (slaveID == SLAVE_ID_1) {
    rs485_1.begin(9600);
    node.begin(slaveID, rs485_1);
    // Serial.println("Reading Sensor 1 (RS485_1)...");
  } else if (slaveID == SLAVE_ID_2) {
    // rs485_2.begin(9600);
    // node.begin(slaveID, rs485_2);
    node.begin(slaveID, Serial);
    // Serial.println("Reading Sensor 2 (RS485_2)...");
  } else {
    // Serial.print("Error: Invalid Slave ID: ");
    // Serial.println(slaveID);
    humi = temp = ph = random(100) / 10.0; // Trả về giá trị ngẫu nhiên để tránh lỗi
    return;
  }

  uint8_t result = node.readHoldingRegisters(0, 4);

  if (result == node.ku8MBSuccess) {
    humi = node.getResponseBuffer(0) / 10.0;
    temp = node.getResponseBuffer(1) / 10.0;
    ph = node.getResponseBuffer(3) / 10.0;
    
    // Serial.print("Success! ID ");
    // Serial.print(slaveID);
    // Serial.print(": H:"); Serial.print(humi);
    // Serial.print(" T:"); Serial.print(temp);
    // Serial.print(" pH:"); Serial.println(ph);
  } else {
    Serial.print("Modbus Error (ID ");
    Serial.print(slaveID);
    Serial.print("): 0x");
    Serial.println(result, HEX);

    // if (result == 0xE2) Serial.println("-> Timeout: Check power supply");
    // else if (result == 0xE0) Serial.println("-> Invalid Slave ID");
    // else if (result == 0xE1) Serial.println("-> Invalid Function");

    humi = temp = ph = random(100) / 10.0; // Trả về giá trị ngẫu nhiên để tránh lỗi
  }
}