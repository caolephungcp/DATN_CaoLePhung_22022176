// ============================================================================
// CONFIGURATION
// ============================================================================

#ifndef CONFIG_H
#define CONFIG_H

// ==== pin map theo sơ đồ ====
const int POW_RS485 = 2;
const int BUTTON_PIN = 5;

const int LORA_RST = A1;
const int LORA_SS = 10;
const int LORA_DIO0 = A0;

const int RS485_DE1 = 7;
const int RS485_DE2 = 9;

const int RS485_1_TX = 6;
const int RS485_1_RX = 8;
const int RS485_2_TX = 0;
const int RS485_2_RX = 1;

const int PUMP_RELAY = 3;
const int VALVE_RELAY = 4;

// LoRa settings
const float LORA_FREQ = 433.0;

// Modbus settings
const uint8_t SLAVE_ID_1 = 1;
const uint8_t SLAVE_ID_2 = 2;

// Node settings
const String NODE_ID = "node01";
const String GATE_ID = "gate01";

// Timers
const unsigned long HEARTBEAT_INTERVAL = 10000; // 10 giây
const unsigned long TELEMETRY_INTERVAL = 3000; // 3 giây
const unsigned long ACK_TIMEOUT = 2000; // 2 giây
const int MAX_RETRY = 3;



#endif