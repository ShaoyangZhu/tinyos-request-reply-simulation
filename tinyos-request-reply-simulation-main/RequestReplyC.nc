#include "Timer.h"
#include "RequestReply.h"

module RequestReplyC {
  uses interface Boot;
  uses interface SplitControl as AMControl;

  uses interface Timer<TMilli> as RequestTimer;
  uses interface Timer<TMilli> as ReplyTimer;

  uses interface AMSend;
  uses interface Receive;
  uses interface Packet;
}

implementation {
  message_t packet;

  bool busy = FALSE;

  uint16_t seqNo = 0;

  bool replyPending = FALSE;
  uint16_t replySeq = 0;
  am_addr_t replyDest = 0;

  event void Boot.booted() {
    dbg("RequestReply", "BOOT node=%hu time=%lu\n",
        (uint16_t)TOS_NODE_ID,
        (unsigned long)call RequestTimer.getNow());

    call AMControl.start();
  }

  event void AMControl.startDone(error_t err) {
    if (err == SUCCESS) {
      dbg("RequestReply", "RADIO_STARTED node=%hu time=%lu\n",
          (uint16_t)TOS_NODE_ID,
          (unsigned long)call RequestTimer.getNow());

      if (TOS_NODE_ID == 1) {
        call RequestTimer.startPeriodic(1000);
      }
    } else {
      call AMControl.start();
    }
  }

  event void AMControl.stopDone(error_t err) {
  }

  event void RequestTimer.fired() {
    request_reply_msg_t *msg;

    if (TOS_NODE_ID != 1) {
      return;
    }

    if (busy) {
      return;
    }

    msg = (request_reply_msg_t *)call Packet.getPayload(&packet, sizeof(request_reply_msg_t));

    if (msg == NULL) {
      return;
    }

    seqNo++;

    msg->msg_type = MSG_TYPE_REQUEST;
    msg->src = TOS_NODE_ID;
    msg->seq = seqNo;

    if (call AMSend.send(AM_BROADCAST_ADDR, &packet, sizeof(request_reply_msg_t)) == SUCCESS) {
      busy = TRUE;

      dbg("RequestReply", "SEND_REQ node=%hu seq=%hu time=%lu\n",
          (uint16_t)TOS_NODE_ID,
          seqNo,
          (unsigned long)call RequestTimer.getNow());
    } else {
      seqNo--;

      dbg("RequestReply", "SEND_REQ_FAIL node=%hu time=%lu\n",
          (uint16_t)TOS_NODE_ID,
          (unsigned long)call RequestTimer.getNow());
    }
  }

  event void ReplyTimer.fired() {
    request_reply_msg_t *msg;

    if (!replyPending) {
      return;
    }

    if (busy) {
      call ReplyTimer.startOneShot(50);
      return;
    }

    msg = (request_reply_msg_t *)call Packet.getPayload(&packet, sizeof(request_reply_msg_t));

    if (msg == NULL) {
      return;
    }

    msg->msg_type = MSG_TYPE_REPLY;
    msg->src = TOS_NODE_ID;
    msg->seq = replySeq;

    if (call AMSend.send(replyDest, &packet, sizeof(request_reply_msg_t)) == SUCCESS) {
      busy = TRUE;
      replyPending = FALSE;

      dbg("RequestReply", "SEND_REPLY node=%hu to=%hu seq=%hu time=%lu\n",
          (uint16_t)TOS_NODE_ID,
          (uint16_t)replyDest,
          replySeq,
          (unsigned long)call RequestTimer.getNow());
    } else {
      call ReplyTimer.startOneShot(50);
    }
  }

  event void AMSend.sendDone(message_t *msg, error_t err) {
    if (msg == &packet) {
      busy = FALSE;

      if (err != SUCCESS) {
        dbg("RequestReply", "SEND_DONE_FAIL node=%hu time=%lu\n",
            (uint16_t)TOS_NODE_ID,
            (unsigned long)call RequestTimer.getNow());
      }
    }
  }

  event message_t *Receive.receive(message_t *msg, void *payload, uint8_t len) {
    request_reply_msg_t *rcv;

    if (len != sizeof(request_reply_msg_t)) {
      return msg;
    }

    rcv = (request_reply_msg_t *)payload;

    if (rcv->msg_type == MSG_TYPE_REQUEST) {
      dbg("RequestReply", "RECV_REQ node=%hu from=%hu seq=%hu time=%lu\n",
          (uint16_t)TOS_NODE_ID,
          (uint16_t)rcv->src,
          (uint16_t)rcv->seq,
          (unsigned long)call RequestTimer.getNow());

      if (TOS_NODE_ID != 1 && rcv->src == 1) {
        if (!replyPending) {
          replyPending = TRUE;
          replySeq = rcv->seq;
          replyDest = rcv->src;

          /*
           * Each responder waits for a node-specific delay before replying.
           * This reduces reply collisions when the simulation uses more nodes.
           */
          call ReplyTimer.startOneShot(100 * TOS_NODE_ID);
        }
      }
    }

    else if (rcv->msg_type == MSG_TYPE_REPLY) {
      if (TOS_NODE_ID == 1) {
        dbg("RequestReply", "RECV_REPLY node=%hu from=%hu seq=%hu time=%lu\n",
            (uint16_t)TOS_NODE_ID,
            (uint16_t)rcv->src,
            (uint16_t)rcv->seq,
            (unsigned long)call RequestTimer.getNow());
      }
    }

    return msg;
  }
}
