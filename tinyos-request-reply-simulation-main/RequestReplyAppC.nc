#include "RequestReply.h"

configuration RequestReplyAppC {
}

implementation {
  components MainC;
  components RequestReplyC as App;
  components ActiveMessageC;

  components new TimerMilliC() as RequestTimer;
  components new TimerMilliC() as ReplyTimer;

  components new AMSenderC(AM_REQUEST_REPLY_MSG) as Sender;
  components new AMReceiverC(AM_REQUEST_REPLY_MSG) as Receiver;

  App.Boot -> MainC.Boot;

  App.AMControl -> ActiveMessageC;

  App.RequestTimer -> RequestTimer;
  App.ReplyTimer -> ReplyTimer;

  App.AMSend -> Sender;
  App.Receive -> Receiver;
  App.Packet -> Sender.Packet;
}
