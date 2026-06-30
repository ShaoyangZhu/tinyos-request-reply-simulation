#ifndef REQUEST_REPLY_H
#define REQUEST_REPLY_H

enum {
  AM_REQUEST_REPLY_MSG = 6,

  MSG_TYPE_REQUEST = 1,
  MSG_TYPE_REPLY = 2,

  REQUEST_REPLY_SINK = 1,
  REQUEST_REPLY_MAX_NODE_ID = 16
};

typedef nx_struct request_reply_msg {
  nx_uint8_t msg_type;
  nx_uint16_t origin;
  nx_uint16_t src;
  nx_uint16_t dest;
  nx_uint16_t seq;
  nx_uint8_t hop_count;
} request_reply_msg_t;

#endif
