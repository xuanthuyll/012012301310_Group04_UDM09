
import os
from pathlib import Path
from typing import Callable, Dict, Optional, List
from .state_machine import TransferStateMachine

class DownloadManager:
    def __init__(self, download_dir: Optional[Path] = None):
        # Nếu không truyền thư mục lưu, mặc định lưu vào ~/Downloads/p2pchat/
        if download_dir is None:
            self.download_dir = Path.home() / "Downloads" / "p2pchat"
        else:
            self.download_dir = Path(download_dir)
            
        # Tự động tạo thư mục tải xuống nếu chưa tồn tại trên máy tính
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Bộ lưu trữ quản lý các tiến trình transfer: dict[transfer_id, TransferStateMachine]
        self.transfers: Dict[str, TransferStateMachine] = {}
        
        # Các callback hooks kết nối với giao diện GUI để hiển thị cho người dùng
        self.on_offer: Optional[Callable[[str, dict], None]] = None
        self.on_progress: Optional[Callable[[str, float], None]] = None
        self.on_done: Optional[Callable[[str, Path], None]] = None
        self.on_failed: Optional[Callable[[str, str], None]] = None

    def register(self, transfer_id: str, meta: dict) -> TransferStateMachine:
        """Đăng ký một tiến trình nhận file mới vào hệ thống quản lý"""
        if transfer_id in self.transfers:
            return self.transfers[transfer_id]
            
        sm = TransferStateMachine(transfer_id)
        sm.on_offer(meta)
        
        # Cài đặt các hàm lắng nghe sự thay đổi từ State Machine để báo lên GUI quản lý tổng
        def handle_state_change(state):
            if state.value == "done":
                save_path = self.get_save_path(transfer_id)
                if self.on_done:
                    self.on_done(transfer_id, save_path)
            elif state.value == "failed":
                if self.on_failed:
                    self.on_failed(transfer_id, "Checksum verification failed or timeout.")
            elif state.value == "cancelled":
                if self.on_failed:
                    self.on_failed(transfer_id, "Transfer cancelled by user or peer.")

        def handle_progress_update(progress_val):
            if self.on_progress:
                self.on_progress(transfer_id, progress_val)

        sm.on_state_change = handle_state_change
        sm.on_progress_update = handle_progress_update
        
        self.transfers[transfer_id] = sm
        
        # Kích hoạt sự kiện có lời mời nhận file lên giao diện GUI
        if self.on_offer:
            self.on_offer(transfer_id, meta)
            
        return sm

    def get(self, transfer_id: str) -> Optional[TransferStateMachine]:
        """Lấy thông tin tiến trình transfer theo ID"""
        return self.transfers.get(transfer_id)

    def remove(self, transfer_id: str) -> None:
        """Xóa tiến trình transfer ra khỏi danh sách quản lý khi hoàn thành hoặc hủy"""
        if transfer_id in self.transfers:
            del self.transfers[transfer_id]

    def active_transfers(self) -> List[dict]:
        """Trả về danh sách các tiến trình tải file đang hoạt động để hiển thị lên bảng điều khiển"""
        active_list = []
        for tid, sm in self.transfers.items():
            if not sm.is_terminal:
                active_list.append({
                    "transfer_id": tid,
                    "filename": sm.meta.get("filename", "Unknown") if sm.meta else "Unknown",
                    "progress": sm.progress,
                    "state": sm.state.value
                })
        return active_list

    def get_save_path(self, transfer_id: str) -> Path:
        """Xử lý nghiệp vụ trùng tên file: Tự động đổi tên thành file.1, file.2 nếu file đã tồn tại"""
        sm = self.transfers.get(transfer_id)
        if not sm or not sm.meta:
            return self.download_dir / f"unknown_{transfer_id}"
            
        filename = sm.meta.get("filename", "unnamed_file")
        base_path = self.download_dir / filename
        
        # Nếu chưa tồn tại file trùng tên thì trả về đường dẫn gốc luôn
        if not base_path.exists():
            return base_path
            
        # Tách tên file và phần mở rộng (đuôi file) để xử lý đổi tên đánh số tăng dần (.1, .2)
        name, ext = os.path.splitext(filename)
        counter = 1
        while True:
            new_filename = f"{name}.{counter}{ext}"
            new_path = self.download_dir / new_filename
            if not new_path.exists():
                return new_path
            counter += 1