// ============================================================================
// LORA MODULE HANDLER
// ============================================================================

#ifndef LORA_MODULE_H
#define LORA_MODULE_H

#include <Arduino.h>
#include <LoRa.h>

void lora_setup();
void sendUplink(bool includeOverrides = false);
void lora_send(String payload);

#endif