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

  bool requestSeen = FALSE;
  uint16_t lastRequestSeq = 0;
  uint16_t lastReplySeqByOrigin[REQUEST_REPLY_MAX_NODE_ID];

  bool requestForwardPending = FALSE;
  uint16_t requestForwardSeq = 0;
  am_addr_t requestForwardDest = 0;
  uint8_t requestForwardHopCount = 0;

  bool replyPending = FALSE;
  uint16_t replyOrigin = 0;
  uint16_t replySeq = 0;
  am_addr_t replyNextHop = 0;
  uint8_t replyHopCount = 0;
  bool replyIsForward = FALSE;

  am_addr_t routeNextHopToSink() {
    if (TOS_NODE_ID == 4) {
      return 2;
    }
    if (TOS_NODE_ID == 5) {
      return 3;
    }
    return REQUEST_REPLY_SINK;
  }

  am_addr_t requestForwardTarget() {
    if (TOS_NODE_ID == 2) {
      return 4;
    }
    if (TOS_NODE_ID == 3) {
      return 5;
    }
    return 0;
  }

  bool replyIsDuplicate(uint16_t origin, uint16_t seq) {
    if (origin >= REQUEST_REPLY_MAX_NODE_ID) {
      return FALSE;
    }

    if (lastReplySeqByOrigin[origin] == seq) {
      return TRUE;
    }

    lastReplySeqByOrigin[origin] = seq;
    return FALSE;
  }

  void armPendingSend() {
    if (requestForwardPending) {
      call ReplyTimer.startOneShot(50);
    } else if (replyPending) {
      if (replyIsForward) {
        call ReplyTimer.startOneShot(50);
      } else {
        call ReplyTimer.startOneShot(100 * TOS_NODE_ID);
      }
    }
  }

  void sendPendingRequestForward() {
    request_reply_msg_t *msg;

    if (!requestForwardPending) {
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

    msg->msg_type = MSG_TYPE_REQUEST;
    msg->origin = REQUEST_REPLY_SINK;
    msg->src = TOS_NODE_ID;
    msg->dest = requestForwardDest;
    msg->seq = requestForwardSeq;
    msg->hop_count = requestForwardHopCount;

    if (call AMSend.send(requestForwardDest, &packet, sizeof(request_reply_msg_t)) == SUCCESS) {
      busy = TRUE;
      requestForwardPending = FALSE;

      dbg("RequestReply", "FORWARD node=%hu type=REQUEST origin=%hu to=%hu next_hop=%hu seq=%hu hop_count=%hu time=%lu\n",
          (uint16_t)TOS_NODE_ID,
          (uint16_t)REQUEST_REPLY_SINK,
          (uint16_t)requestForwardDest,
          (uint16_t)requestForwardDest,
          requestForwardSeq,
          (uint16_t)requestForwardHopCount,
          (unsigned long)call RequestTimer.getNow());
    } else {
      call ReplyTimer.startOneShot(50);
    }
  }

  void sendPendingReply() {
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
    msg->origin = replyOrigin;
    msg->src = TOS_NODE_ID;
    msg->dest = REQUEST_REPLY_SINK;
    msg->seq = replySeq;
    msg->hop_count = replyHopCount;

    if (call AMSend.send(replyNextHop, &packet, sizeof(request_reply_msg_t)) == SUCCESS) {
      busy = TRUE;
      replyPending = FALSE;

      if (replyIsForward) {
        dbg("RequestReply", "FORWARD node=%hu type=REPLY origin=%hu to=%hu next_hop=%hu seq=%hu hop_count=%hu time=%lu\n",
            (uint16_t)TOS_NODE_ID,
            replyOrigin,
            (uint16_t)REQUEST_REPLY_SINK,
            (uint16_t)replyNextHop,
            replySeq,
            (uint16_t)replyHopCount,
            (unsigned long)call RequestTimer.getNow());
      } else {
        dbg("RequestReply", "SEND_REPLY node=%hu to=%hu origin=%hu seq=%hu hop_count=%hu time=%lu\n",
            (uint16_t)TOS_NODE_ID,
            (uint16_t)replyNextHop,
            replyOrigin,
            replySeq,
            (uint16_t)replyHopCount,
            (unsigned long)call RequestTimer.getNow());
      }
    } else {
      call ReplyTimer.startOneShot(50);
    }
  }

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

      if (TOS_NODE_ID == REQUEST_REPLY_SINK) {
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

    if (TOS_NODE_ID != REQUEST_REPLY_SINK) {
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
    msg->origin = REQUEST_REPLY_SINK;
    msg->src = TOS_NODE_ID;
    msg->dest = AM_BROADCAST_ADDR;
    msg->seq = seqNo;
    msg->hop_count = 0;

    if (call AMSend.send(AM_BROADCAST_ADDR, &packet, sizeof(request_reply_msg_t)) == SUCCESS) {
      busy = TRUE;

      dbg("RequestReply", "SEND_REQ node=%hu seq=%hu time=%lu origin=%hu hop_count=%hu\n",
          (uint16_t)TOS_NODE_ID,
          seqNo,
          (unsigned long)call RequestTimer.getNow(),
          (uint16_t)REQUEST_REPLY_SINK,
          (uint16_t)0);
    } else {
      seqNo--;

      dbg("RequestReply", "SEND_REQ_FAIL node=%hu time=%lu\n",
          (uint16_t)TOS_NODE_ID,
          (unsigned long)call RequestTimer.getNow());
    }
  }

  event void ReplyTimer.fired() {
    if (requestForwardPending) {
      sendPendingRequestForward();
    } else if (replyPending) {
      sendPendingReply();
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

      armPendingSend();
    }
  }

  event message_t *Receive.receive(message_t *msg, void *payload, uint8_t len) {
    request_reply_msg_t *rcv;
    am_addr_t forwardTarget;

    if (len != sizeof(request_reply_msg_t)) {
      return msg;
    }

    rcv = (request_reply_msg_t *)payload;

    if (rcv->msg_type == MSG_TYPE_REQUEST) {
      dbg("RequestReply", "RECV_REQ node=%hu from=%hu seq=%hu time=%lu origin=%hu hop_count=%hu\n",
          (uint16_t)TOS_NODE_ID,
          (uint16_t)rcv->src,
          (uint16_t)rcv->seq,
          (unsigned long)call RequestTimer.getNow(),
          (uint16_t)rcv->origin,
          (uint16_t)rcv->hop_count);

      if (TOS_NODE_ID == REQUEST_REPLY_SINK) {
        return msg;
      }

      if (rcv->dest != AM_BROADCAST_ADDR && rcv->dest != TOS_NODE_ID) {
        return msg;
      }

      if (requestSeen && lastRequestSeq == rcv->seq) {
        dbg("RequestReply", "DROP_DUP node=%hu type=REQUEST origin=%hu seq=%hu time=%lu\n",
            (uint16_t)TOS_NODE_ID,
            (uint16_t)rcv->origin,
            (uint16_t)rcv->seq,
            (unsigned long)call RequestTimer.getNow());
        return msg;
      }

      requestSeen = TRUE;
      lastRequestSeq = rcv->seq;

      forwardTarget = requestForwardTarget();
      if (forwardTarget != 0) {
        requestForwardPending = TRUE;
        requestForwardSeq = rcv->seq;
        requestForwardDest = forwardTarget;
        requestForwardHopCount = rcv->hop_count + 1;
      }

      if (!replyPending) {
        replyPending = TRUE;
        replyOrigin = TOS_NODE_ID;
        replySeq = rcv->seq;
        replyNextHop = routeNextHopToSink();
        replyHopCount = 1;
        replyIsForward = FALSE;
      }

      armPendingSend();
    } else if (rcv->msg_type == MSG_TYPE_REPLY) {
      if (TOS_NODE_ID == REQUEST_REPLY_SINK) {
        dbg("RequestReply", "RECV_REPLY node=%hu from=%hu seq=%hu time=%lu hop_count=%hu last_hop=%hu\n",
            (uint16_t)TOS_NODE_ID,
            (uint16_t)rcv->origin,
            (uint16_t)rcv->seq,
            (unsigned long)call RequestTimer.getNow(),
            (uint16_t)rcv->hop_count,
            (uint16_t)rcv->src);

        dbg("RequestReply", "RECV_AT_SINK node=%hu origin=%hu from=%hu seq=%hu hop_count=%hu time=%lu\n",
            (uint16_t)TOS_NODE_ID,
            (uint16_t)rcv->origin,
            (uint16_t)rcv->src,
            (uint16_t)rcv->seq,
            (uint16_t)rcv->hop_count,
            (unsigned long)call RequestTimer.getNow());
      } else {
        if (rcv->dest != REQUEST_REPLY_SINK) {
          return msg;
        }

        if (replyIsDuplicate(rcv->origin, rcv->seq)) {
          dbg("RequestReply", "DROP_DUP node=%hu type=REPLY origin=%hu seq=%hu time=%lu\n",
              (uint16_t)TOS_NODE_ID,
              (uint16_t)rcv->origin,
              (uint16_t)rcv->seq,
              (unsigned long)call RequestTimer.getNow());
          return msg;
        }

        if (!replyPending) {
          replyPending = TRUE;
          replyOrigin = rcv->origin;
          replySeq = rcv->seq;
          replyNextHop = routeNextHopToSink();
          replyHopCount = rcv->hop_count + 1;
          replyIsForward = TRUE;
          armPendingSend();
        }
      }
    }

    return msg;
  }
}
