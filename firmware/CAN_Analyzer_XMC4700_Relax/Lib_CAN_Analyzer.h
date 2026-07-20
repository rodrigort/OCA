#ifndef LIB_CAN_ANALYZER_H_
#define LIB_CAN_ANALYZER_H_

#include <stdint.h>
#include "DAVE.h"

typedef struct
{
  uint32_t timestamp_ms;
  uint16_t id;
  uint8_t dlc;
  uint8_t data[8];
} CAN_ANALYZER_Frame_t;

void CAN_Analyzer_Init(void);
CAN_NODE_STATUS_t CAN_Analyzer_SendFrame(uint16_t id, uint8_t dlc, uint8_t *data);
CAN_NODE_STATUS_t CAN_Analyzer_SendFrameEx(uint16_t id, uint8_t dlc, uint8_t *data,
                                          uint16_t sequence, uint8_t protocol_v2);
void CAN_Analyzer_ParseRx(void);
void CAN_Analyzer_ProcessInterrupt(void);
void CAN_Analyzer_SendStatus(void);
void CAN_Analyzer_SendHello(void);
void CAN_Analyzer_SetListenOnly(uint8_t enabled);

#endif
