
import unittest
import tempfile
import shutil
from pathlib import Path
from transfer.state_machine import TransferStateMachine, TransferState
from transfer.download_manager import DownloadManager
from transfer.receiver import FileReceiver

class TestFileTransferIntegration(unittest.TestCase):
    def setUp(self):
        # Tạo thư mục tạm để giả lập lưu file tải xuống
        self.test_dir = tempfile.TemporaryDirectory()
        self.download_path = Path(self.test_dir.name)
        
        self.dm = DownloadManager(download_dir=self.download_path)
        self.receiver = FileReceiver(download_manager=self.dm)
        
        self.transfer_id = "tx_12345"
        self.meta = {
            "filename": "test_document.txt",
            "file_size": 15,
            "total_chunks": 3,
            "checksum": "dummy"} # MD5 tương ứng với b"Hello World P2P"

    def tearDown(self):
        self.test_dir.cleanup()

    def test_state_machine_valid_transitions(self):
        """Test: State machine transitions đầy đủ: IDLE → OFFERED → ACCEPTED → RECEIVING → DONE"""
        sm = TransferStateMachine(self.transfer_id)
        self.assertEqual(sm.state, TransferState.IDLE)
        
        sm.on_offer(self.meta)
        self.assertEqual(sm.state, TransferState.OFFERED)
        
        sm.on_accept()
        self.assertEqual(sm.state, TransferState.ACCEPTED)
        
        sm.on_chunk(0, 3)
        self.assertEqual(sm.state, TransferState.RECEIVING)
        self.assertAlmostEqual(sm.progress, 1/3)
        
        sm.on_assembling()
        self.assertEqual(sm.state, TransferState.ASSEMBLING)
        
        sm.on_done(is_verified=True)
        self.assertEqual(sm.state, TransferState.DONE)
        self.assertEqual(sm.progress, 1.0)

    def test_download_manager_lifecycle(self):
        """Test: DownloadManager: register, get, active_transfers"""
        sm = self.dm.register(self.transfer_id, self.meta)
        self.assertIsNotNone(sm)
        
        fetched_sm = self.dm.get(self.transfer_id)
        self.assertEqual(fetched_sm, sm)
        
        active = self.dm.active_transfers()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["filename"], "test_document.txt")

    def test_receiver_reassemble_in_order(self):
        """Test: FileReceiver: reassemble từ chunks đúng thứ tự và verify checksum đúng"""
        # Giả lập gói tin trọn vẹn cắt nhỏ từ chuỗi b"Hello World P2P"
        chunks = [b"Hello ", b"World ", b"P2P"]
        
        # 1. Nhận lời mời
        self.receiver.handle_offer("127.0.0.1", {"transfer_id": self.transfer_id, "meta": self.meta})
        self.receiver.accept(self.transfer_id)
        
        # 2. Nhận tuần tự từng chunk đúng thứ tự
        for i, chunk_bytes in enumerate(chunks):
            packet = {
                "transfer_id": self.transfer_id,
                "index": i,
                "total_chunks": 3,
                "data": chunk_bytes.hex()
            }
            self.receiver.handle_chunk("127.0.0.1", packet)
            
        # 3. Báo hoàn thành và lắp ghép
        done_packet = {
            "transfer_id": self.transfer_id,
            "checksum": self.meta["checksum"]
        }
        self.receiver.handle_done("127.0.0.1", done_packet)
        
        # Kiểm tra xem file đã được lưu thành công ra đĩa cứng và trạng thái đạt DONE chưa
        sm = self.dm.get(self.transfer_id)
        self.assertEqual(sm.state, TransferState.DONE)
        
        expected_file = self.download_path / "test_document.txt"
        self.assertTrue(expected_file.exists())
        self.assertEqual(expected_file.read_bytes(), b"Hello World P2P")

    def test_receiver_reassemble_out_of_order(self):
        """Test: FileReceiver: reassemble từ chunks ngẫu nhiên thứ tự (out-of-order)"""
        chunks = {
            0: b"Hello ",
            1: b"World ",
            2: b"P2P"
        }
        
        self.receiver.handle_offer("127.0.0.1", {"transfer_id": self.transfer_id, "meta": self.meta})
        self.receiver.accept(self.transfer_id)
        
        # Giả lập mạng lỗi truyền mảnh số 2 trước, rồi đến mảnh 0, cuối cùng là mảnh 1
        for index in [2, 0, 1]:
            packet = {
                "transfer_id": self.transfer_id,
                "index": index,
                "total_chunks": 3,
                "data": chunks[index].hex()
            }
            self.receiver.handle_chunk("127.0.0.1", packet)
            
        done_packet = {"transfer_id": self.transfer_id, "checksum": self.meta["checksum"]}
        self.receiver.handle_done("127.0.0.1", done_packet)
        
        # Hệ thống buộc phải tự sắp xếp và gộp thành công file hoàn chỉnh không bị lỗi dữ liệu
        sm = self.dm.get(self.transfer_id)
        self.assertEqual(sm.state, TransferState.DONE)

    def test_duplicate_filename_rename(self):
        """Test: Trùng tên file -> Tự động kích hoạt cơ chế đổi tên đánh số tăng dần (.1, .2)"""
        # Tạo sẵn một file trùng tên "test_document.txt" nằm ở thư mục tải xuống trước
        existing_file = self.download_path / "test_document.txt"
        existing_file.write_bytes(b"Old Data")
        
        # Đăng ký một file transfer mới trùng tên hoàn toàn
        self.dm.register(self.transfer_id, self.meta)
        
        # Đường dẫn tính toán tiếp theo bắt buộc phải tự nhảy thành test_document.1.txt
        calculated_path = self.dm.get_save_path(self.transfer_id)
        self.assertEqual(calculated_path.name, "test_document.1.txt")

if __name__ == "__main__":
    unittest.main()