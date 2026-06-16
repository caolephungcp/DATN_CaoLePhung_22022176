// ============================================================================
// SENSOR HANDLER
// ============================================================================

#ifndef SENSOR_H
#define SENSOR_H

#include <Arduino.h>
#include <SoftwareSerial.h>
#include <ModbusMaster.h>

extern SoftwareSerial rs485_1;
// extern SoftwareSerial rs485_2;
extern ModbusMaster node;

void sensor_setup();   
void preTransmission();
void postTransmission();
void readSensorData(uint8_t slaveID, float &humi, float &temp, float &ph);

#endif