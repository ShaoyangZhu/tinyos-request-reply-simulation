from __future__ import print_function
import re

send_req_pattern = re.compile(r"SEND_REQ node=1 seq=(\d+) time=(\d+)")
recv_reply_pattern = re.compile(r"RECV_REPLY node=1 from=(\d+) seq=(\d+) time=(\d+)")

send_times = {}
received_replies = set()
delays = []

with open("log.txt", "r") as f:
    for line in f:
        m = send_req_pattern.search(line)
        if m:
            seq = int(m.group(1))
            send_time = int(m.group(2))
            send_times[seq] = send_time

        m = recv_reply_pattern.search(line)
        if m:
            src = int(m.group(1))
            seq = int(m.group(2))
            recv_time = int(m.group(3))

            key = (src, seq)

            if key in received_replies:
                continue

            received_replies.add(key)

            if seq in send_times:
                delay = recv_time - send_times[seq]
                delays.append(delay)

request_count = len(send_times)

# For each request from node 1, node 2 and node 3 should each send one reply.
expected_reply_count = request_count * 2

actual_reply_count = len(received_replies)

if expected_reply_count > 0:
    packet_reception_rate = float(actual_reply_count) / float(expected_reply_count)
else:
    packet_reception_rate = 0.0

if len(delays) > 0:
    average_delay = sum(delays) / float(len(delays))
else:
    average_delay = 0.0

reply_from_node2 = len([x for x in received_replies if x[0] == 2])
reply_from_node3 = len([x for x in received_replies if x[0] == 3])

print("===== Simulation Log Analysis =====")
print("Request packets sent by node 1: %d" % request_count)
print("Expected reply packets: %d" % expected_reply_count)
print("Actual reply packets received by node 1: %d" % actual_reply_count)
print("Reply packets from node 2: %d" % reply_from_node2)
print("Reply packets from node 3: %d" % reply_from_node3)
print("Packet reception rate: %.2f%%" % (packet_reception_rate * 100.0))
print("Average delay: %.2f ms" % average_delay)
