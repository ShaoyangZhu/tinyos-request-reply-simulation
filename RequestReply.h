#ifndef REQUEST_REPLY_H
#define REQUEST_REPLY_H

enum {
  AM_REQUEST_REPLY_MSG = 6,

  MSG_TYPE_REQUEST = 1,
  MSG_TYPE_REPLY = 2
};

typedef nx_struct request_reply_msg {
  nx_uint8_t msg_type;
  nx_uint16_t src;
  nx_uint16_t seq;
} request_reply_msg_t;

#endif
