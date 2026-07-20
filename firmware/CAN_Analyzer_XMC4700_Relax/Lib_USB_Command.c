#include "Lib_USB_Command.h"
#include "Lib_CAN_Analyzer.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define USB_COMMAND_BUFFER_SIZE   (96U)

static char usb_command_buffer[USB_COMMAND_BUFFER_SIZE];
static uint8_t usb_command_index;

static void USB_Parse_Line(char *line);
static bool USB_Read_Hex_Token(char **cursor, uint32_t *value);
static bool USB_Read_Decimal_Token(char **cursor, uint32_t *value);
static bool USB_Consume_Comma(char **cursor);
static bool USB_Is_Hex_Digit(char character);
static uint8_t USB_Hex_Value(char character);

/*============================================================================
Name    :    USB_Send_Text
------------------------------------------------------------------------------
Purpose :    Envia texto pela USB Virtual COM.
Input   :    text - String terminada em zero.
Output  :    None
Notes   :    Ignora envio enquanto a USB ainda nao estiver enumerada.
============================================================================*/
void USB_Send_Text(char *text)
{
  if ((text != 0) && (USBD_VCOM_IsEnumDone() != 0U))
  {
    USBD_VCOM_SendString((const int8_t *)text);
  }
}

/*============================================================================
Name    :    USB_Process_Command
------------------------------------------------------------------------------
Purpose :    Recebe e processa comandos vindos da USB Virtual COM.
Input   :    None
Output  :    None
Notes   :    Comandos sao finalizados por LF ou CR.
============================================================================*/
void USB_Process_Command(void)
{
  int8_t received;
  uint16_t bytes;

  CDC_Device_USBTask(&USBD_VCOM_cdc_interface);

  if (USBD_VCOM_IsEnumDone() == 0U)
  {
    usb_command_index = 0U;
    return;
  }

  bytes = USBD_VCOM_BytesReceived();
  while (bytes > 0U)
  {
    if (USBD_VCOM_ReceiveByte(&received) == USBD_VCOM_STATUS_SUCCESS)
    {
      if ((received == '\n') || (received == '\r'))
      {
        if (usb_command_index > 0U)
        {
          usb_command_buffer[usb_command_index] = '\0';
          USB_Parse_Line(usb_command_buffer);
          usb_command_index = 0U;
        }
      }
      else if (usb_command_index < (USB_COMMAND_BUFFER_SIZE - 1U))
      {
        usb_command_buffer[usb_command_index] = (char)received;
        usb_command_index++;
      }
      else
      {
        usb_command_index = 0U;
        USB_Send_Text("ERR,CMD\r\n");
      }
    }
    bytes--;
  }
}

/*============================================================================
Name    :    USB_Parse_Line
------------------------------------------------------------------------------
Purpose :    Interpreta um comando TX recebido do PC.
Input   :    line - Linha de comando recebida.
Output  :    None
Notes   :    Formato: TX,ID,DLC,B0,B1,B2,B3,B4,B5,B6,B7.
============================================================================*/
static void USB_Parse_Line(char *line)
{
  char *cursor = line;
  uint32_t id;
  uint32_t dlc;
  uint32_t value;
  uint8_t index;
  uint8_t data[8] = {0U};
  uint16_t sequence = 0xFFFFU;
  uint8_t protocol_v2 = 0U;
  CAN_NODE_STATUS_t tx_status;

  if (strcmp(line, "HELLO?") == 0)
  {
    CAN_Analyzer_SendHello();
    return;
  }
  if (strcmp(line, "GET,STATUS") == 0)
  {
    CAN_Analyzer_SendStatus();
    return;
  }
  if (strcmp(line, "SET,LISTEN,1") == 0)
  {
    CAN_Analyzer_SetListenOnly(1U);
    USB_Send_Text("OK,LISTEN,1\r\n");
    return;
  }
  if (strcmp(line, "SET,LISTEN,0") == 0)
  {
    CAN_Analyzer_SetListenOnly(0U);
    USB_Send_Text("OK,LISTEN,0\r\n");
    return;
  }

  if ((cursor[0] == 'T') && (cursor[1] == 'X') && (cursor[2] == '2') && (cursor[3] == ','))
  {
    cursor += 4;
    if ((USB_Read_Decimal_Token(&cursor, &value) == false) || (value > 0xFFFFU))
    {
      USB_Send_Text("ERR,SEQ\r\n");
      return;
    }
    sequence = (uint16_t)value;
    protocol_v2 = 1U;
    if (USB_Consume_Comma(&cursor) == false)
    {
      USB_Send_Text("ERR,CMD\r\n");
      return;
    }
  }
  else if ((cursor[0] == 'T') && (cursor[1] == 'X') && (cursor[2] == ','))
  {
    cursor += 3;
  }
  else
  {
    USB_Send_Text("ERR,CMD\r\n");
    return;
  }

  if (USB_Read_Hex_Token(&cursor, &id) == false)
  {
    USB_Send_Text("ERR,ID\r\n");
    return;
  }
  if (id > 0x7FFU)
  {
    USB_Send_Text("ERR,ID\r\n");
    return;
  }

  if (USB_Consume_Comma(&cursor) == false)
  {
    USB_Send_Text("ERR,CMD\r\n");
    return;
  }
  if (USB_Read_Hex_Token(&cursor, &dlc) == false)
  {
    USB_Send_Text("ERR,DLC\r\n");
    return;
  }
  if (dlc > 8U)
  {
    USB_Send_Text("ERR,DLC\r\n");
    return;
  }

  for (index = 0U; index < 8U; index++)
  {
    if (USB_Consume_Comma(&cursor) == false)
    {
      USB_Send_Text("ERR,CMD\r\n");
      return;
    }
    if (USB_Read_Hex_Token(&cursor, &value) == false)
    {
      USB_Send_Text("ERR,CMD\r\n");
      return;
    }
    if (value > 0xFFU)
    {
      USB_Send_Text("ERR,CMD\r\n");
      return;
    }
    data[index] = (uint8_t)value;
  }

  if (*cursor != '\0')
  {
    USB_Send_Text("ERR,CMD\r\n");
    return;
  }

  tx_status = CAN_Analyzer_SendFrameEx((uint16_t)id, (uint8_t)dlc, data,
                                      sequence, protocol_v2);
  if (tx_status == CAN_NODE_STATUS_SUCCESS)
  {
    /* A confirmacao OK e emitida no loop principal apos o evento TX. */
  }
  else if (tx_status == CAN_NODE_STATUS_BUSY)
  {
    if (protocol_v2 != 0U)
    {
      char response[32];
      snprintf(response, sizeof(response), "ERR,CAN,%u\r\n", sequence);
      USB_Send_Text(response);
    }
    else
    {
      USB_Send_Text("ERR,CAN\r\n");
    }
  }
  else
  {
    USB_Send_Text("ERR,CAN\r\n");
  }
}

/*============================================================================
Name    :    USB_Read_Decimal_Token
------------------------------------------------------------------------------
Purpose :    Le um valor decimal do comando serial.
Input   :    cursor - Ponteiro para a posicao atual da linha.
Output  :    value - Valor convertido.
Notes   :    Usado para a sequencia TX do protocolo v2.
============================================================================*/
static bool USB_Read_Decimal_Token(char **cursor, uint32_t *value)
{
  uint8_t digits = 0U;
  uint32_t parsed = 0U;

  while ((**cursor >= '0') && (**cursor <= '9'))
  {
    parsed = (parsed * 10U) + (uint32_t)(**cursor - '0');
    (*cursor)++;
    digits++;
  }
  if (digits == 0U)
  {
    return false;
  }
  *value = parsed;
  return true;
}

/*============================================================================
Name    :    USB_Read_Hex_Token
------------------------------------------------------------------------------
Purpose :    Le um valor hexadecimal do comando serial.
Input   :    cursor - Ponteiro para a posicao atual da linha.
Output  :    value - Valor convertido.
Notes   :    Aceita opcionalmente prefixo 0x.
============================================================================*/
static bool USB_Read_Hex_Token(char **cursor, uint32_t *value)
{
  uint8_t digits = 0U;
  uint32_t parsed = 0U;

  if (((*cursor)[0] == '0') && (((*cursor)[1] == 'x') || ((*cursor)[1] == 'X')))
  {
    *cursor += 2;
  }

  while (USB_Is_Hex_Digit(**cursor) != false)
  {
    parsed = (parsed << 4U) | USB_Hex_Value(**cursor);
    (*cursor)++;
    digits++;
  }

  if (digits == 0U)
  {
    return false;
  }

  *value = parsed;
  return true;
}

/*============================================================================
Name    :    USB_Consume_Comma
------------------------------------------------------------------------------
Purpose :    Consome uma virgula do comando serial.
Input   :    cursor - Ponteiro para a posicao atual da linha.
Output  :    true se havia virgula.
Notes   :
============================================================================*/
static bool USB_Consume_Comma(char **cursor)
{
  if (**cursor != ',')
  {
    return false;
  }

  (*cursor)++;
  return true;
}

/*============================================================================
Name    :    USB_Is_Hex_Digit
------------------------------------------------------------------------------
Purpose :    Verifica se um caractere pertence ao conjunto hexadecimal.
Input   :    character - Caractere analisado.
Output  :    true se for digito hexadecimal.
Notes   :
============================================================================*/
static bool USB_Is_Hex_Digit(char character)
{
  return (((character >= '0') && (character <= '9')) ||
          ((character >= 'A') && (character <= 'F')) ||
          ((character >= 'a') && (character <= 'f')));
}

/*============================================================================
Name    :    USB_Hex_Value
------------------------------------------------------------------------------
Purpose :    Converte um caractere hexadecimal para valor numerico.
Input   :    character - Caractere hexadecimal.
Output  :    Valor de 0 a 15.
Notes   :    Chamador garante que o caractere e valido.
============================================================================*/
static uint8_t USB_Hex_Value(char character)
{
  if ((character >= '0') && (character <= '9'))
  {
    return (uint8_t)(character - '0');
  }
  if ((character >= 'A') && (character <= 'F'))
  {
    return (uint8_t)(character - 'A' + 10);
  }

  return (uint8_t)(character - 'a' + 10);
}
