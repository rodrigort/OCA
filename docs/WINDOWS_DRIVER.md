# XMC4700 Relax Kit USB Driver on Windows

## Português do Brasil

No macOS e no Linux, o J-Link usa o driver USB genérico fornecido pelo sistema. No Windows,
o manual oficial do XMC4700/XMC4800 Relax Kit informa que a depuração SWD e a comunicação
UART pelo debugger integrado requerem o driver SEGGER J-Link. Esse driver também acompanha o
ModusToolbox da Infineon.

Fontes oficiais:

- [Manual do XMC4700/XMC4800 Relax Kit](https://www.infineon.com/assets/row/public/documents/30/44/infineon-board-user-manual-xmc4700-xmc4800-relax-kit-series-usermanual-en.pdf)
- [Página oficial do KIT-XMC47-RELAX-V1](https://www.infineon.com/evaluation-board/KIT-XMC47-RELAX-V1)
- [Download oficial do J-Link](https://www.segger.com/downloads/jlink/)
- [Documentação SEGGER sobre Virtual COM Port](https://kb.segger.com/J-Link_-_Virtual_COM_Port)

### Instalação

1. Desconecte a placa do USB.
2. Baixe o **J-Link Software and Documentation Pack** somente no site oficial da SEGGER, ou
   instale o ModusToolbox pelo site oficial da Infineon.
3. Execute o instalador com uma conta autorizada e mantenha o suporte USB/J-Link selecionado.
4. Reinicie o Windows se o instalador solicitar.
5. Conecte o cabo ao conector USB do debugger integrado da Relax Kit.
6. Abra **Gerenciador de Dispositivos → Portas (COM e LPT)** e anote a porta atribuída ao
   dispositivo serial/J-Link VCOM.
7. Abra o OCA, clique em **Atualizar** e escolha essa porta. O número COM pode mudar; nunca
   configure COM6 ou qualquer outro número como obrigatório.

### Se a porta não aparecer

- Troque o cabo por um cabo USB de dados e teste outra porta USB.
- Feche IDEs, terminais e depuradores que possam estar usando a porta.
- Confirme se o debugger aparece no **J-Link Configurator**.
- Quando a opção estiver disponível, confirme que **Virtual COM-Port** está habilitada e
  desligue/ligue a placa após a alteração.
- Atualize o firmware do debugger somente pelas ferramentas oficiais da SEGGER.
- Remova no Gerenciador de Dispositivos apenas a entrada problemática e repita a instalação.

Versões modernas do Windows e alguns J-Links podem usar WinUSB automaticamente, mas placas ou
configurações antigas ainda podem precisar do driver SEGGER. Não baixe drivers de sites de
terceiros e não use ferramentas genéricas para substituir o driver do dispositivo.

## English

The official XMC4700/XMC4800 Relax Kit manual states that the on-board probe's SWD and UART
features require the SEGGER J-Link driver on Windows. Install the official J-Link Software and
Documentation Pack—or Infineon ModusToolbox, which includes it—then reconnect the board and
locate its assigned port under **Device Manager → Ports (COM & LPT)**. Refresh OCA and select
the detected port; Windows does not guarantee a stable COM number.

Linux and macOS use the operating system's generic USB driver for J-Link. If Windows does not
show a virtual port, check the cable, close applications holding the device, inspect it with
J-Link Configurator, enable VCOM when supported, and power-cycle the board. Use only official
Infineon and SEGGER downloads.
