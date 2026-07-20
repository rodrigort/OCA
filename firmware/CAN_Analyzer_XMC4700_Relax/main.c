/*
 * main.c
 *
 *  Created on: 2026 Jul 17 17:00:49
 *  Author: Open CAN Analyzer contributors
 */




#include "DAVE.h"                 //Declarations from DAVE Code Generation (includes SFR declaration)
#include "Lib_CAN_Analyzer.h"
#include "Lib_USB_Command.h"

#define APP_LED_HEARTBEAT_COUNT  (250000U)

static void App_UpdateLeds(void);

/**

 * @brief main() - Application entry point
 *
 * <b>Details of function</b><br>
 * This routine is the application entry point. It is invoked by the device startup code. It is responsible for
 * invoking the APP initialization dispatcher routine - DAVE_Init() and hosting the place-holder for user application
 * code.
 */

int main(void)
{
  DAVE_STATUS_t status;

  status = DAVE_Init();           /* Initialization of DAVE APPs  */

  if (status != DAVE_STATUS_SUCCESS)
  {
    /* Placeholder for error handler code. The while loop below can be replaced with an user error handler. */
    XMC_DEBUG("DAVE APPs initialization failed\n");

    while(1U)
    {

    }
  }

  CAN_Analyzer_Init();
  USBD_VCOM_Connect();

  while(1U)
  {
    USB_Process_Command();
    CAN_Analyzer_ParseRx();
    App_UpdateLeds();
  }
}

/*============================================================================
Name    :    App_UpdateLeds
------------------------------------------------------------------------------
Purpose :    Atualiza LEDs de status da aplicacao.
Input   :    None
Output  :    None
Notes   :    LED_1 pisca para indicar MCU rodando. LED_2 liga com USB enumerada.
============================================================================*/
static void App_UpdateLeds(void)
{
  static uint32_t heartbeat_count;

  heartbeat_count++;
  if (heartbeat_count >= APP_LED_HEARTBEAT_COUNT)
  {
    heartbeat_count = 0U;
    DIGITAL_IO_ToggleOutput(&LED_1);
  }

  if (USBD_VCOM_IsEnumDone() != 0U)
  {
    DIGITAL_IO_SetOutputHigh(&LED_2);
  }
  else
  {
    DIGITAL_IO_SetOutputLow(&LED_2);
  }
}
