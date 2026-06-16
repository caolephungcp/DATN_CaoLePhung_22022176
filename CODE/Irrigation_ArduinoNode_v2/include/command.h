// ============================================================================
// COMMAND HANDLER
// ============================================================================

#ifndef COMMAND_H
#define COMMAND_H

#include <Arduino.h>

void processCmd(const String &cmd);
void setPump(bool on);
void setValve(bool on);

#endif