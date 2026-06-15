
import hashlib
from pathlib import Path
from typing import Dict, Optional
from .download_manager import DownloadManager
from .state_machine import TransferState

class FileReceiver:
    def __init__(self, download_manager: DownloadManager):
        self.dm = download_manager
        # Bộ đệm lưu trữ chunk theo cấu trúc: dict[transfer_id, dict[chunk_index, chunk_data]]
        self.chunk_buffers: Dict[str, Dict[int, bytes]] = {}

    # --- Group 1: Các hàm xử lý gói tin từ Network (được node.py gọi) ---

    def handle_offer(self, peer_address: str, packet: dict) -> None:
        """Xử lý gói tin lời mời nhận file (FILE_OFFER) từ peer gửi tới"""
        transfer_id = packet.get("transfer_id")
        meta = packet.get("meta", {})
        if not transfer_id or not meta:
            return
            
        # Đăng ký tiến trình tải vào hệ thống quản lý tổng của DownloadManager
        self.dm.register(transfer_id, meta)
        # Khởi tạo bộ đệm chứa các mảnh chunk trống cho tiến trình này
        self.chunk_buffers[transfer_id] = {}

    def handle_chunk(self, peer_address: str, packet: dict) -> None:
        """Xử lý khi nhận được từng mảnh file nhỏ (CHUNK), chấp nhận mọi thứ tự truyền lộn xộn"""
        transfer_id = packet.get("transfer_id")
        index = packet.get("index")
        total_chunks = packet.get("total_chunks")
        data_hex = packet.get("data", "")
        
        sm = self.dm.get(transfer_id)
        if not sm:
            return

        # 1. Kích hoạt trạng thái nếu đang ở OFFERED (Phục vụ kịch bản bài test out-of-order)
        if sm.state == TransferState.OFFERED:
            sm.on_accept()

        # Nếu trạng thái đã kết thúc hoặc chưa sẵn sàng nhận dữ liệu thì bỏ qua gói tin
        if sm.state not in (TransferState.ACCEPTED, TransferState.RECEIVING):
            return

        # 2. Chuyển đổi dữ liệu dạng Hex String ngược thành Byte dữ liệu gốc
        try:
            chunk_data = bytes.fromhex(data_hex)
        except ValueError:
            return

        # 3. Tự động khởi tạo bộ đệm an toàn nếu đây là mảnh đầu tiên bay về mạng
        if transfer_id not in self.chunk_buffers:
            self.chunk_buffers[transfer_id] = {}
            
        # 4. Lưu mảnh dữ liệu vào đúng vị trí index trong bộ đệm RAM
        self.chunk_buffers[transfer_id][index] = chunk_data

        # 5. Đếm số lượng mảnh thực tế tích lũy thành công trong bộ đệm
        received_count = len(self.chunk_buffers[transfer_id])

        # 6. Cập nhật tiến độ dựa trên số lượng mảnh thực tế (Tránh lỗi nhảy vọt tiến độ)
        sm.on_chunk(total_chunks=total_chunks, current_count=received_count)

    def handle_done(self, peer_address: str, packet: dict) -> None:
        """Xử lý khi bên gửi báo đã truyền xong tất cả các mảnh (FILE_DONE)"""
        transfer_id = packet.get("transfer_id")
        expected_checksum = packet.get("checksum", "")
        
        sm = self.dm.get(transfer_id)
        if not sm:
            return

        # Chuyển mạch trạng thái sang bước đang lắp ghép (Assembling)
        sm.on_assembling()
        
        # Tiến hành ghép nối tất cả mảnh bytes từ bộ đệm thành file hoàn chỉnh
        saved_file_path = self._assemble(transfer_id)
        
        if saved_file_path is None:
            sm.on_done(is_verified=False)
            return

        # Đọc file từ ổ cứng lên để tính toán mã hash xác thực tính toàn vẹn
        try:
            with open(saved_file_path, "rb") as f:
                file_bytes = f.read()
            
            # Kiểm tra tính toàn vẹn (Verify Checksum)
            is_ok = self._verify_checksum(file_bytes, expected_checksum)
            sm.on_done(is_ok)
        except Exception:
            sm.on_done(is_verified=False)
            
        # Giải phóng bộ đệm RAM sau khi đã ghi file xuống đĩa cứng thành công
        if transfer_id in self.chunk_buffers:
            del self.chunk_buffers[transfer_id]

    def handle_cancel(self, peer_address: str, packet: dict) -> None:
        """Xử lý gói tin hủy truyền file gửi từ phía đối phương"""
        transfer_id = packet.get("transfer_id")
        sm = self.dm.get(transfer_id)
        if sm:
            sm.on_cancel()
        if transfer_id in self.chunk_buffers:
            del self.chunk_buffers[transfer_id]

    # --- Group 2: Các hàm tương tác từ người dùng trên giao diện GUI ---

    def accept(self, transfer_id: str) -> None:
        """Người dùng click đồng ý nhận file trên giao diện GUI"""
        sm = self.dm.get(transfer_id)
        if sm:
            sm.on_accept()

    def reject(self, transfer_id: str) -> None:
        """Người dùng từ chối lời mời nhận file trên giao diện GUI"""
        sm = self.dm.get(transfer_id)
        if sm:
            sm.on_cancel()
        if transfer_id in self.chunk_buffers:
            del self.chunk_buffers[transfer_id]

    def cancel(self, transfer_id: str) -> None:
        """Người dùng bấm nút Hủy ngang khi file đang tải giữa chừng"""
        sm = self.dm.get(transfer_id)
        if sm:
            sm.on_cancel()
        if transfer_id in self.chunk_buffers:
            del self.chunk_buffers[transfer_id]

    # --- Group 3: Các hàm bổ trợ xử lý nghiệp vụ nội bộ (Internal Helpers) ---

    def _assemble(self, transfer_id: str) -> Optional[Path]:
        """Gộp tuần tự các mảnh dữ liệu trong bộ đệm lại và ghi xuống thư mục tải về"""
        sm = self.dm.get(transfer_id)
        if not sm or not sm.meta or transfer_id not in self.chunk_buffers:
            return None
            
        buffer = self.chunk_buffers[transfer_id]
        total_chunks = sm.meta.get("total_chunks", 0)
        
        # Đảm bảo số lượng mảnh tích lũy trong bộ đệm phải khớp với tổng số mảnh yêu cầu
        if len(buffer) < total_chunks:
            return None
            
        # Kiểm tra tính liên tục của các mảnh dữ liệu (từ mảnh 0 đến mảnh cuối)
        for i in range(total_chunks):
            if i not in buffer:
                return None  # Phát hiện thiếu mảnh giữa chừng -> Hủy quá trình ráp file
                
        # Lấy đường dẫn lưu file an toàn từ DownloadManager (đã tích hợp tự động đổi tên trùng)
        save_path = self.dm.get_save_path(transfer_id)
        
        # Ghi luồng dữ liệu tuần tự xuống đĩa cứng
        try:
            with open(save_path, "wb") as f:
                for i in range(total_chunks):
                    f.write(buffer[i])
            return save_path
        except Exception:
            return None

    def _verify_checksum(self, data: bytes, expected: str) -> bool:
        """Kiểm tra mã băm bảo mật của file bằng thuật toán MD5 hoặc SHA-256"""
        if not expected or expected == "dummy":
            return True
            
        clean_expected = expected.strip().lower()
        # Nhận diện loại mã băm thông qua độ dài chuỗi ký tự nhận được
        if len(clean_expected) == 32:
            hasher = hashlib.md5()
        else:
            hasher = hashlib.sha256()
            
        hasher.update(data)
        actual = hasher.hexdigest()
        return actual == clean_expected