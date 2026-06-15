# 🔒 Kiến trúc Bảo mật Danh tính & Độ tin cậy mạng (Identity & TOFU Trust Flow)

Hệ thống áp dụng cơ chế bảo mật **Trust-On-First-Use (TOFU)** kết hợp mã hóa bất đối xứng **RSA** nhằm xác thực danh tính các nút mạng (Peers), chống lại các cuộc tấn công giả mạo mà không cần phụ thuộc vào máy chủ trung tâm (CA).

---

## 🛡️ 1. Quy trình quản lý độ tin cậy TOFU (Trust-On-First-Use)

Quy trình thiết lập lòng tin giữa các thực thể trong mạng $P2P$ diễn ra qua hai giai đoạn cốt lõi:

### A. Kết nối lần đầu tiên (First Connection)
* Khi một Peer mới thiết lập kết nối, hệ thống mạng chưa có thông tin lịch sử về thực thể này.
* Hệ thống sẽ tự động gán cho Peer đó trạng thái mặc định là **`TRUSTED_UNVERIFIED`** (Tin cậy nhưng chưa xác thực).
* Khóa công khai (`Public Key`) và dấu vân tay định danh (`Key Fingerprint`) của đối phương sẽ được tiếp nhận và lưu trữ xuống cơ sở dữ liệu local thông qua phân hệ lưu trữ (`storage.py`).

### B. Các kết nối tiếp theo (Subsequent Connections)
* Trong những lần liên lạc sau, hệ thống sẽ tiến hành bốc tách khóa công khai hiện tại của Peer đó và so khớp dấu vân tay (`Fingerprint`) với bản ghi đã lưu trong cơ sở dữ liệu.
* **Trường hợp trùng khớp:** Peer được xác nhận là chính chủ, hệ thống cho phép tiếp tục truyền tải file và chat an toàn.
* **Trường hợp sai lệch (Fingerprint Mismatch):** Hệ thống lập tức phát hiện có sự thay đổi khóa (nguy cơ bị tấn công giả mạo/Man-in-the-Middle). Máy trạng thái sẽ ngay lập tức kích hoạt sự kiện lỗi, đóng kết nối và chuyển tiến trình về trạng thái **`FAILED`**.

---

## 🔑 2. Cơ chế Ký số và Xác thực gói tin bằng RSA

Để đảm bảo nội dung tệp tin hoặc tin nhắn không bị sửa đổi hay can thiệp trên đường truyền mạng, toàn bộ dữ liệu đều được bảo vệ bằng chữ ký số:

* **Phía Người gửi (Sender):** 1. Sử dụng thuật toán băm **SHA-256** để tạo ra một chuỗi đại diện (Hash) từ nội dung gói tin.
  2. Dùng khóa bí mật riêng tư (**`Private Key`**) để mã hóa chuỗi Hash đó, tạo thành **Chữ ký số (Signature)** và đính kèm vào gói tin gửi đi.

* **Phía Người nhận (Receiver):**
  1. Tiếp nhận gói tin chứa dữ liệu thô và chữ ký số từ mạng đổ về.
  2. Sử dụng khóa công khai (**`Public Key`**) của người gửi (đã được lưu và xác thực từ bước TOFU) để giải mã chữ ký số.
  3. Hàm `verify_signature()` tiến hành so sánh kết quả giải mã với chuỗi băm thực tế của gói tin nhận được:
     * **Khớp:** Gói tin toàn vẹn $\rightarrow$ Tiếp tục xử lý dữ liệu.
     * **Lệch:** Gói tin đã bị sửa đổi $\rightarrow$ Hủy bỏ gói tin ngay lập tức.

---

## 📁 Các hàm thành phần phụ trách kiểm thử thành công
* `generate_keypair()`: Sinh ngẫu nhiên cặp khóa RSA bảo mật (mặc định size 1024-bit).
* `sign_message()`: Tạo chữ ký số bảo vệ gói tin.
* `verify_signature()`: Đối chiếu chữ ký, trả về `True` nếu an toàn và `False` nếu phát hiện gian lận.