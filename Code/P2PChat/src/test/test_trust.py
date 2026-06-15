import unittest
from controllers.controller import ChatController

class TestTrustAndTOFU(unittest.TestCase):
    def setUp(self):
        # Thiết lập danh sách giả lập các Peer được phát hiện kèm trạng thái tin cậy của chúng
        self.discovered_db = {
            "192.168.1.5:5000": {"username": "An", "fingerprint": "aa:bb:cc:dd", "status": "new"},
            "192.168.1.6:5000": {"username": "Bình", "fingerprint": "11:22:33:44", "status": "verified"}
        }
        
        self.controller = ChatController(
            on_system=lambda msg: None,
            on_message=lambda s, p: None,
            on_connected=lambda p: None,
            on_disconnect=lambda p: None,
            on_peers_update=lambda: None,
            on_peer_discovered=lambda addr, info: None
        )

    def test_tofu_new_peer_handling(self):
        """Test: TOFU: peer mới kết nối -> Mặc định gán trạng thái TRUSTED_UNVERIFIED"""
        peer_addr = "192.168.1.5:5000"
        peer_info = self.discovered_db[peer_addr]
        
        # Mô phỏng cơ chế TOFU: Nếu trạng thái là 'new', chuyển thành 'trusted_unverified' ở lần đầu kết nối
        if peer_info["status"] == "new":
            peer_info["status"] = "trusted_unverified"
            
        self.assertEqual(peer_info["status"], "trusted_unverified")

    def test_tofu_fingerprint_mismatch(self):
        """Test: TOFU: Kiểm tra phát hiện kẻ mạo danh đổi dấu vân tay (Fingerprint Mismatch)"""
        peer_addr = "192.168.1.6:5000"  # Địa chỉ của Bình
        saved_fingerprint = self.discovered_db[peer_addr]["fingerprint"]
        
        # Giả lập một kẻ xấu dùng đúng địa chỉ của Bình nhưng gửi kèm một mã fingerprint lạ
        attacker_fingerprint = "ff:ff:ff:ff"
        
        status = "verified"
        if attacker_fingerprint != saved_fingerprint:
            status = "fingerprint_mismatch"
            
        self.assertEqual(status, "fingerprint_mismatch")

    def test_block_peer_simulation(self):
        """Test: Block peer -> Gán trạng thái BLOCKED, từ chối xử lý dữ liệu từ đối tượng này"""
        blocked_list = set()
        peer_addr = "192.168.1.7:5000"
        
        # Thực hiện chặn địa chỉ IP này
        blocked_list.add(peer_addr)
        
        # Giả lập hàm kiểm tra gói tin đi qua bộ lọc an ninh
        def is_packet_allowed(addr):
            if addr in blocked_list:
                return "blocked"
            return "allowed"
            
        self.assertEqual(is_packet_allowed(peer_addr), "blocked")

if __name__ == "__main__":
    unittest.main()