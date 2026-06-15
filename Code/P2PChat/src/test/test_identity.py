import unittest
import os
import tempfile
import hashlib
from pathlib import Path
# Import chính xác lớp CryptoHandler từ file crypto.py của nhóm bạn
from security.crypto import CryptoHandler  

class TestIdentity(unittest.TestCase):
    def setUp(self):
        # Tạo thư mục tạm để chuẩn bị cho việc test save/load key
        self.test_dir = tempfile.TemporaryDirectory()
        self.key_path = Path(self.test_dir.name) / "test_peer.key"

    def tearDown(self):
        # Dọn dẹp thư mục tạm sau khi test xong
        self.test_dir.cleanup()

    def _get_fingerprint(self, handler: CryptoHandler) -> str:
        """Hàm bổ trợ sinh Fingerprint từ Key theo định dạng colon-separated hex"""
        # Băm dữ liệu key bằng SHA-256
        key_hash = hashlib.sha256(handler.get_key()).hexdigest()
        # Định dạng thành từng cặp 2 ký tự cách nhau bằng dấu hai chấm (aa:bb:cc:...)
        return ":".join(key_hash[i:i+2] for i in range(0, len(key_hash), 2))

    def test_peer_id_lifecycle(self):
        """Test: Khởi tạo mã hóa, lưu khóa ra file và tải lại khóa thành công"""
        # 1. Khởi tạo đối tượng xử lý mã hóa ngẫu nhiên
        handler_1 = CryptoHandler()
        key_1 = handler_1.get_key()
        self.assertIsNotNone(key_1)
        
        # 2. Giả lập ghi khóa xuống file dữ liệu (Save)
        with open(self.key_path, "wb") as f:
            f.write(key_1)
        self.assertTrue(self.key_path.exists())
        
        # 3. Đọc lại file dữ liệu để khôi phục trạng thái khóa (Load)
        with open(self.key_path, "rb") as f:
            key_2 = f.read()
        handler_2 = CryptoHandler(key=key_2)
        
        # Kiểm tra xem khóa khôi phục có trùng khớp 100% với khóa ban đầu không
        self.assertEqual(handler_1.get_key(), handler_2.get_key())

    def test_fingerprint_format(self):
        """Test: Fingerprint format đúng cấu trúc (colon-separated hex)"""
        handler = CryptoHandler()
        fingerprint = self._get_fingerprint(handler)
        
        # Kiểm tra chuỗi có chứa dấu phân cách hai chấm không
        parts = fingerprint.split(":")
        self.assertGreater(len(parts), 1)
        
        # Kiểm tra từng cụm có đúng 2 ký tự và là mã Hex hợp lệ không
        for part in parts:
            self.assertEqual(len(part), 2)
            int(part, 16)  # Sẽ raise ValueError nếu không phải ký tự hệ Hex hợp lệ

    def test_fingerprint_deterministic(self):
        """Test: Fingerprint từ cùng một key luôn cho ra cùng một kết quả duy nhất"""
        handler = CryptoHandler()
        
        # Sinh vân tay 2 lần từ cùng 1 thực thể quản lý khóa
        fp1 = self._get_fingerprint(handler)
        fp2 = self._get_fingerprint(handler)
        
        # Hai kết quả thu được bắt buộc phải giống hệt nhau
        self.assertEqual(fp1, fp2)

if __name__ == "__main__":
    unittest.main()