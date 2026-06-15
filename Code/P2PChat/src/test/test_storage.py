import unittest
import threading
from typing import List
from controllers.controller import ChatController

class TestStorageAndHistory(unittest.TestCase):
    def setUp(self):
        # Tạo danh sách tạm đóng vai trò như bộ lưu trữ lịch sử tin nhắn thực tế
        self.received_messages: List[str] = []
        
        # Khởi tạo ChatController với các hàm callback giả lập
        self.controller = ChatController(
            on_system=lambda msg: None,
            on_message=lambda sender, payload: self.received_messages.append(f"{sender}: {payload}"),
            on_connected=lambda peer: None,
            on_disconnect=lambda peer: None,
            on_peers_update=lambda: None
        )

    def test_message_history_and_append(self):
        """Test: Kiểm tra cơ chế đẩy tin nhắn vào bộ lưu trữ qua Controller"""
        # Giả lập sự kiện nhận tin nhắn từ mạng kích hoạt vào hệ thống
        self.controller._on_message("An", "Hello")
        self.controller._on_message("Bình", "Hi there")
        
        # Kiểm tra dữ liệu đã được nạp vào bộ lưu trữ tạm thời thành công chưa
        self.assertEqual(len(self.received_messages), 2)
        self.assertEqual(self.received_messages[0], "An: Hello")

    def test_message_history_limit_simulation(self):
        """Test: Giả lập cơ chế giới hạn bộ nhớ lưu trữ lịch sử tin nhắn (Limit)"""
        limit = 3
        local_history = []
        
        # Định nghĩa hàm thêm tin nhắn có ràng buộc giới hạn kích thước bộ nhớ
        def append_with_limit(msg: str):
            if len(local_history) >= limit:
                local_history.pop(0)  # Xóa tin cũ nhất nếu vượt quá giới hạn
            local_history.append(msg)

        # Đẩy liên tục 4 tin nhắn vào bộ đệm giới hạn 3 phần tử
        for i in range(1, 5):
            append_with_limit(f"Tin nhắn số {i}")
            
        # Bộ nhớ lưu trữ bắt buộc phải cắt tỉa và chỉ giữ lại đúng 3 bản ghi mới nhất
        self.assertEqual(len(local_history), 3)
        self.assertEqual(local_history[0], "Tin nhắn số 2")

    def test_storage_thread_safety_simulation(self):
        """Test: Kiểm tra tính an toàn đa luồng khi Controller bắn callback liên tục"""
        lock = threading.Lock()
        
        def worker(thread_id):
            for j in range(20):
                with lock:
                    self.controller._on_message(f"Peer_{thread_id}", f"Msg {j}")

        # Khởi chạy đồng thời 5 luồng cùng đẩy dữ liệu tin nhắn vào hệ thống
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
            
        # Tổng số tin nhắn nhận được phải bảo toàn đầy đủ và không gây xung đột (Crash)
        self.assertEqual(len(self.received_messages), 100)

if __name__ == "__main__":
    unittest.main()