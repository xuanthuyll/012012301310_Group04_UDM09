# 🔄 Kiến trúc Luồng Dữ liệu Truyền tải Tệp tin (P2P File Transfer Flow)

Tài liệu này mô tả chi tiết cách thức lớp `FileReceiver` phối hợp với `TransferStateMachine` để tiếp nhận, xử lý các mảnh byte lộn xộn (out-of-order chunks) và lắp ráp thành file hoàn chỉnh.

## 📝 1. Sơ đồ tuần tự các bước (Sequence Diagram)

```text
[Sender (Peer A)]                       [Network Layer]                     [Receiver (Peer B)]
       |                                       |                                     |
       |----- 1. Gửi gói tin FILE_OFFER ------>|                                     |
       |                                       |----- 2. Chuyển trạng thái --------->| [IDLE -> OFFERED]
       |                                       |                                     |
       |                                       |<---- 3. Người dùng bấm ACCEPT ------| [OFFERED -> ACCEPTED]
       |<---- 4. Phản hồi đồng ý (RESPONSE) ---|                                     |
       |                                       |                                     |
       |===== 5. Truyền các mảnh CHUNKS ======>|                                     |
       |      (Thứ tự ngẫu nhiên / Out-of-order)  |===== 6. Đổ dữ liệu vào bộ đệm RAM =>| [ACCEPTED -> RECEIVING]
       |                                       |        (Tích lũy & tính tiến độ)     |
       |                                       |                                     |
       |----- 7. Gửi thông báo FILE_DONE ----->|                                     |
       |                                       |----- 8. Khóa luồng mạng ------------>| [RECEIVING -> ASSEMBLING]
       |                                       |                                     |
       |                                       |----- 9. Kiểm tra Checksum MD5 ------>|
       |                                       |        |-- Khớp: Ghi xuống đĩa ----->| [ASSEMBLING -> DONE]
       |                                       |        |-- Lỗi: Hủy bỏ bộ đệm ------->| [ASSEMBLING -> FAILED]
       