#include "Lib_CAN_Analyzer.h"
#include "Lib_USB_Command.h"

#include <stdio.h>

#define CAN_ANALYZER_TX_LMO          (CAN_NODE_0.lmobj_ptr[0])
#define CAN_ANALYZER_RX_LMO          (CAN_NODE_0.lmobj_ptr[1])
#define CAN_ANALYZER_RX_QUEUE_SIZE   (32U)
#define CAN_ANALYZER_STD_ID_MAX      (0x7FFU)
#define CAN_ANALYZER_NO_SEQUENCE     (0xFFFFU)

static volatile CAN_ANALYZER_Frame_t can_rx_queue[CAN_ANALYZER_RX_QUEUE_SIZE];
static volatile uint8_t can_rx_head;
static volatile uint8_t can_rx_tail;
static volatile uint32_t can_rx_dropped;
static volatile uint32_t can_rx_count;
static volatile uint32_t can_tx_count;
static volatile uint32_t can_message_lost;
static volatile uint32_t can_uptime_ms;
static volatile uint8_t can_tx_confirm_pending;
static volatile uint8_t can_tx_protocol_v2;
static volatile uint16_t can_tx_sequence;
static volatile uint16_t can_tx_id;
static volatile uint32_t can_tx_started_ms;
static volatile uint8_t can_tx_error_pending;
static volatile uint8_t can_listen_only;

static void CAN_Analyzer_CopyRxFrame(void);

/*============================================================================
Name    :    CAN_Analyzer_Init
------------------------------------------------------------------------------
Purpose :    Prepara os objetos CAN usados pelo analisador.
Input   :    None
Output  :    None
Notes   :    Ajusta a mascara RX em runtime para aceitar IDs standard.
============================================================================*/
void CAN_Analyzer_Init(void)
{
  XMC_CAN_MO_SetAcceptanceMask(CAN_ANALYZER_RX_LMO->mo_ptr, 0x000U);
  CAN_NODE_MO_ClearStatus(CAN_ANALYZER_RX_LMO,
                          XMC_CAN_MO_RESET_STATUS_RX_PENDING |
                          XMC_CAN_MO_RESET_STATUS_NEW_DATA |
                          XMC_CAN_MO_RESET_STATUS_MESSAGE_LOST);
  CAN_NODE_MO_ClearStatus(CAN_ANALYZER_TX_LMO,
                          XMC_CAN_MO_RESET_STATUS_TX_PENDING |
                          XMC_CAN_MO_RESET_STATUS_TX_REQUEST);
  can_tx_sequence = CAN_ANALYZER_NO_SEQUENCE;
  (void)SysTick_Config(SystemCoreClock / 1000U);
}

/*============================================================================
Name    :    CAN_Analyzer_SendFrame
------------------------------------------------------------------------------
Purpose :    Transmite um frame CAN standard usando o objeto TX principal.
Input   :    id  - Identificador standard 11-bit.
             dlc - Quantidade de bytes do frame.
             data - Ponteiro para os dados do frame.
Output  :    CAN_NODE_STATUS_SUCCESS em caso de sucesso.
Notes   :    Bytes acima do DLC sao transmitidos como zero no buffer local.
============================================================================*/
CAN_NODE_STATUS_t CAN_Analyzer_SendFrame(uint16_t id, uint8_t dlc, uint8_t *data)
{
  return CAN_Analyzer_SendFrameEx(id, dlc, data, CAN_ANALYZER_NO_SEQUENCE, 0U);
}

/*============================================================================
Name    :    CAN_Analyzer_SendFrameEx
------------------------------------------------------------------------------
Purpose :    Transmite um frame e associa metadados da requisicao USB.
Input   :    id - Identificador standard; dlc/data - payload CAN.
             sequence - Sequencia do protocolo v2; protocol_v2 - formato usado.
Output  :    Status retornado pelo CAN_NODE.
Notes   :    A confirmacao USB e enviada somente apos o evento TX real.
============================================================================*/
CAN_NODE_STATUS_t CAN_Analyzer_SendFrameEx(uint16_t id, uint8_t dlc, uint8_t *data,
                                          uint16_t sequence, uint8_t protocol_v2)
{
  uint8_t index;
  uint8_t tx_data[8] = {0U};
  CAN_NODE_STATUS_t status;

  if ((id > CAN_ANALYZER_STD_ID_MAX) || (dlc > 8U) || (data == 0) ||
      (can_listen_only != 0U))
  {
    return CAN_NODE_STATUS_FAILURE;
  }

  if (can_tx_confirm_pending != 0U)
  {
    return CAN_NODE_STATUS_BUSY;
  }

  for (index = 0U; index < dlc; index++)
  {
    tx_data[index] = data[index];
  }

  CAN_NODE_MO_UpdateID(CAN_ANALYZER_TX_LMO, (uint32_t)id);
  XMC_CAN_MO_SetDataLengthCode(CAN_ANALYZER_TX_LMO->mo_ptr, dlc);

  status = CAN_NODE_MO_UpdateData(CAN_ANALYZER_TX_LMO, tx_data);
  if (status == CAN_NODE_STATUS_SUCCESS)
  {
    CAN_NODE_MO_ClearStatus(CAN_ANALYZER_TX_LMO, XMC_CAN_MO_RESET_STATUS_TX_PENDING);
    can_tx_sequence = sequence;
    can_tx_protocol_v2 = protocol_v2;
    can_tx_id = id;
    can_tx_started_ms = can_uptime_ms;
    can_tx_confirm_pending = 1U;
    status = CAN_NODE_MO_Transmit(CAN_ANALYZER_TX_LMO);
    if (status != CAN_NODE_STATUS_SUCCESS)
    {
      can_tx_confirm_pending = 0U;
    }
  }

  return status;
}

/*============================================================================
Name    :    CAN_Analyzer_ParseRx
------------------------------------------------------------------------------
Purpose :    Envia pela USB serial os frames CAN pendentes na fila RX.
Input   :    None
Output  :    None
Notes   :    Executar no loop principal, fora da interrupcao.
============================================================================*/
void CAN_Analyzer_ParseRx(void)
{
  CAN_ANALYZER_Frame_t frame;
  char text[96];
  uint8_t tail;

  while (can_rx_tail != can_rx_head)
  {
    tail = can_rx_tail;
    frame = (CAN_ANALYZER_Frame_t)can_rx_queue[tail];
    can_rx_tail = (uint8_t)((tail + 1U) % CAN_ANALYZER_RX_QUEUE_SIZE);

    snprintf(text,
             sizeof(text),
             "RX2,%lu,%03X,%u,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X\r\n",
             (unsigned long)frame.timestamp_ms,
             frame.id,
             frame.dlc,
             frame.data[0],
             frame.data[1],
             frame.data[2],
             frame.data[3],
             frame.data[4],
             frame.data[5],
             frame.data[6],
             frame.data[7]);
    USB_Send_Text(text);
  }

  if (can_tx_confirm_pending == 2U)
  {
    if (can_tx_protocol_v2 != 0U)
    {
      snprintf(text, sizeof(text), "OK,TX,%u,%03X\r\n", can_tx_sequence, can_tx_id);
    }
    else
    {
      snprintf(text, sizeof(text), "OK,TX,%03X\r\n", can_tx_id);
    }
    can_tx_confirm_pending = 0U;
    USB_Send_Text(text);
  }
  else if ((can_tx_confirm_pending == 1U) &&
           ((uint32_t)(can_uptime_ms - can_tx_started_ms) >= 1000U))
  {
    CAN_NODE_MO_ClearStatus(CAN_ANALYZER_TX_LMO,
                            XMC_CAN_MO_RESET_STATUS_TX_REQUEST |
                            XMC_CAN_MO_RESET_STATUS_TX_PENDING);
    can_tx_confirm_pending = 0U;
    can_tx_error_pending = 1U;
  }

  if (can_tx_error_pending != 0U)
  {
    if (can_tx_protocol_v2 != 0U)
    {
      snprintf(text, sizeof(text), "ERR,CAN,%u\r\n", can_tx_sequence);
    }
    else
    {
      snprintf(text, sizeof(text), "ERR,CAN\r\n");
    }
    can_tx_error_pending = 0U;
    USB_Send_Text(text);
  }
}

/*============================================================================
Name    :    CAN_Analyzer_ProcessInterrupt
------------------------------------------------------------------------------
Purpose :    Trata eventos CAN mantendo a interrupcao curta.
Input   :    None
Output  :    None
Notes   :    Copia frames RX para uma fila e limpa flags de RX/TX.
============================================================================*/
void CAN_Analyzer_ProcessInterrupt(void)
{
  uint32_t rx_status;
  uint32_t tx_status;
  uint32_t node_status;

  rx_status = CAN_NODE_MO_GetStatus(CAN_ANALYZER_RX_LMO);
  if ((rx_status & XMC_CAN_MO_STATUS_MESSAGE_LOST) != 0U)
  {
    can_message_lost++;
  }
  if ((rx_status & XMC_CAN_MO_STATUS_RX_PENDING) != 0U)
  {
    CAN_Analyzer_CopyRxFrame();
    CAN_NODE_MO_ClearStatus(CAN_ANALYZER_RX_LMO,
                            XMC_CAN_MO_RESET_STATUS_RX_PENDING |
                            XMC_CAN_MO_RESET_STATUS_NEW_DATA |
                            XMC_CAN_MO_RESET_STATUS_MESSAGE_LOST);
  }

  tx_status = CAN_NODE_MO_GetStatus(CAN_ANALYZER_TX_LMO);
  if ((tx_status & XMC_CAN_MO_STATUS_TX_PENDING) != 0U)
  {
    CAN_NODE_MO_ClearStatus(CAN_ANALYZER_TX_LMO, XMC_CAN_MO_RESET_STATUS_TX_PENDING);
    can_tx_count++;
    if (can_tx_confirm_pending == 1U)
    {
      can_tx_confirm_pending = 2U;
    }
  }

  node_status = CAN_NODE_GetStatus(&CAN_NODE_0);
  if (((node_status & XMC_CAN_NODE_STATUS_BUS_OFF) != 0U) &&
      (can_tx_confirm_pending == 1U))
  {
    can_tx_confirm_pending = 0U;
    can_tx_error_pending = 1U;
  }
  if ((node_status & XMC_CAN_NODE_STATUS_ALERT_WARNING) != 0U)
  {
    CAN_NODE_ClearStatus(&CAN_NODE_0, XMC_CAN_NODE_STATUS_ALERT_WARNING);
  }
}

/*============================================================================
Name    :    IRQ_CAN_INTERRUPT
------------------------------------------------------------------------------
Purpose :    ISR conectada ao service request CAN configurado no DAVE.
Input   :    None
Output  :    None
Notes   :    Encaminha o trabalho minimo para a rotina da biblioteca.
============================================================================*/
void IRQ_CAN_INTERRUPT(void)
{
  CAN_Analyzer_ProcessInterrupt();
}

/*============================================================================
Name    :    CAN_Analyzer_CopyRxFrame
------------------------------------------------------------------------------
Purpose :    Copia o ultimo frame RX do objeto CAN para a fila local.
Input   :    None
Output  :    None
Notes   :    Chamado somente pela interrupcao CAN.
============================================================================*/
static void CAN_Analyzer_CopyRxFrame(void)
{
  uint8_t index;
  uint8_t next_head;
  CAN_ANALYZER_Frame_t frame;

  if (CAN_NODE_MO_Receive(CAN_ANALYZER_RX_LMO) != CAN_NODE_STATUS_SUCCESS)
  {
    return;
  }

  frame.timestamp_ms = can_uptime_ms;
  frame.id = (uint16_t)(CAN_ANALYZER_RX_LMO->mo_ptr->can_identifier & CAN_ANALYZER_STD_ID_MAX);
  frame.dlc = CAN_ANALYZER_RX_LMO->mo_ptr->can_data_length;
  if (frame.dlc > 8U)
  {
    frame.dlc = 8U;
  }

  for (index = 0U; index < 8U; index++)
  {
    frame.data[index] = 0U;
  }
  for (index = 0U; index < frame.dlc; index++)
  {
    frame.data[index] = CAN_ANALYZER_RX_LMO->mo_ptr->can_data_byte[index];
  }

  next_head = (uint8_t)((can_rx_head + 1U) % CAN_ANALYZER_RX_QUEUE_SIZE);
  if (next_head == can_rx_tail)
  {
    can_rx_dropped++;
    return;
  }

  can_rx_queue[can_rx_head] = frame;
  can_rx_head = next_head;
  can_rx_count++;
}

/*============================================================================
Name    :    CAN_Analyzer_SendHello
------------------------------------------------------------------------------
Purpose :    Informa identidade e versao do protocolo do firmware.
Input   :    None
Output  :    None
Notes   :    Resposta ao comando HELLO?.
============================================================================*/
void CAN_Analyzer_SendHello(void)
{
  USB_Send_Text("HELLO,2,OCA-XMC4700,0.2.0\r\n");
}

/*============================================================================
Name    :    CAN_Analyzer_SendStatus
------------------------------------------------------------------------------
Purpose :    Envia contadores e diagnostico atual do controlador CAN.
Input   :    None
Output  :    None
Notes   :    STATUS,RX,TX,DROPPED,MLOST,STATE,TEC,REC.
============================================================================*/
void CAN_Analyzer_SendStatus(void)
{
  uint32_t status = CAN_NODE_GetStatus(&CAN_NODE_0);
  uint8_t tec = XMC_CAN_NODE_GetTransmitErrorCounter(CAN_NODE_0.node_ptr);
  uint8_t rec = XMC_CAN_NODE_GetReceiveErrorCounter(CAN_NODE_0.node_ptr);
  const char *state = "OK";
  char text[96];

  if ((status & XMC_CAN_NODE_STATUS_BUS_OFF) != 0U)
  {
    state = "BUS_OFF";
  }
  else if ((tec >= 128U) || (rec >= 128U))
  {
    state = "ERROR_PASSIVE";
  }
  else if ((status & XMC_CAN_NODE_STATUS_ERROR_WARNING_STATUS) != 0U)
  {
    state = "ERROR_WARNING";
  }

  snprintf(text, sizeof(text), "STATUS,%lu,%lu,%lu,%lu,%s,%u,%u,%s\r\n",
           (unsigned long)can_rx_count,
           (unsigned long)can_tx_count,
           (unsigned long)can_rx_dropped,
           (unsigned long)can_message_lost,
           state,
           tec,
           rec,
           (can_listen_only != 0U) ? "LISTEN" : "ACTIVE");
  USB_Send_Text(text);
}

/*============================================================================
Name    :    CAN_Analyzer_SetListenOnly
------------------------------------------------------------------------------
Purpose :    Ativa ou desativa o modo analisador silencioso do no CAN.
Input   :    enabled - Diferente de zero para receber sem ACK/transmissao.
Output  :    None
Notes   :    O no e colocado em INIT somente durante a alteracao do modo.
============================================================================*/
void CAN_Analyzer_SetListenOnly(uint8_t enabled)
{
  XMC_CAN_NODE_SetInitBit(CAN_NODE_0.node_ptr);
  if (enabled != 0U)
  {
    XMC_CAN_NODE_SetAnalyzerMode(CAN_NODE_0.node_ptr);
    can_listen_only = 1U;
  }
  else
  {
    XMC_CAN_NODE_ReSetAnalyzerMode(CAN_NODE_0.node_ptr);
    can_listen_only = 0U;
  }
  XMC_CAN_NODE_ResetInitBit(CAN_NODE_0.node_ptr);
}

/*============================================================================
Name    :    SysTick_Handler
------------------------------------------------------------------------------
Purpose :    Mantem a base de tempo de 1 ms usada nos timestamps CAN.
Input   :    None
Output  :    None
Notes   :    Configurado por CAN_Analyzer_Init.
============================================================================*/
void SysTick_Handler(void)
{
  can_uptime_ms++;
}
