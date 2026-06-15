from enum import Enum
import threading

class TransferState(Enum):
    IDLE = "idle"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    RECEIVING = "receiving"
    ASSEMBLING = "assembling"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TransferStateMachine:
    def __init__(self, transfer_id: str, meta: dict = None, is_sender: bool = False):
        self.transfer_id = transfer_id
        self.meta = meta if meta is not None else {}
        self.is_sender = is_sender
        
        # Trạng thái ban đầu của tiến trình
        self._state = TransferState.IDLE
        self._progress = 0.0
        self._lock = threading.Lock()
        
        # Danh sách các callback để cập nhật thời gian thực lên giao diện GUI
        self._state_callbacks = []
        self._progress_callbacks = []

    def on_offer(self, meta: dict = None) -> None:
        """Kích hoạt khi có lời mời nhận file, chuyển từ IDLE lên OFFERED"""
        with self._lock:
            if self._state == TransferState.IDLE:
                if meta is not None:
                    self.meta = meta
                self._update_state(TransferState.OFFERED)

    @property
    def state(self) -> TransferState:
        with self._lock:
            return self._state

    @property
    def progress(self) -> float:
        with self._lock:
            return self._progress
    @property
    def is_terminal(self):
        return self._state in (
        TransferState.DONE,
        TransferState.FAILED,
        TransferState.CANCELLED
    )

    def register_state_callback(self, cb):
        self._state_callbacks.append(cb)

    def register_progress_callback(self, cb):
        self._progress_callbacks.append(cb)

    # --- Các hàm dịch chuyển trạng thái (State Transitions) ---

    def on_accept(self) -> None:
        """Kích hoạt khi người nhận bấm đồng ý nhận file trên GUI"""
        with self._lock:
            if self._state == TransferState.OFFERED:
                self._update_state(TransferState.ACCEPTED)

    def on_chunk(self, index: int = None, total_chunks: int = 0, current_count: int = None) -> None:
        """Cập nhật tiến độ thông minh, phân biệt rõ ràng giữa chỉ số index và số lượng mảnh thực tế"""
        with self._lock:
            if self._state in (TransferState.ACCEPTED, TransferState.RECEIVING):
                if self._state == TransferState.ACCEPTED:
                    self._update_state(TransferState.RECEIVING)
                
                if total_chunks > 0:
                    # Nếu truyền vào current_count (luồng từ FileReceiver xử lý out-of-order)
                    if current_count is not None:
                        calc_progress = current_count / total_chunks
                    # Nếu truyền vào index (luồng bài test tuần tự gọi trực tiếp State Machine)
                    elif index is not None:
                        calc_progress = (index + 1) / total_chunks
                    else:
                        return

                    # Ràng buộc an toàn: Không cho phép vượt quá 1.0 và chặn hoàn toàn việc giật lùi tiến độ
                    calc_progress = min(1.0, calc_progress)
                    if calc_progress > self._progress:
                        self._update_progress(calc_progress)
    def on_assembling(self) -> None:
        """Kích hoạt khi nhận được thông báo FILE_DONE để bắt đầu ráp file"""
        with self._lock:
            if self._state in (TransferState.ACCEPTED, TransferState.RECEIVING):
                self._update_state(TransferState.ASSEMBLING)

    def on_done(self, is_verified: bool = True) -> None:
        """Kết thúc truyền tải: DONE nếu mã hash khớp, FAILED nếu file lỗi hoặc thiếu mảnh"""
        with self._lock:
            if self._state == TransferState.ASSEMBLING:
                if is_verified:
                    self._update_state(TransferState.DONE)
                    self._update_progress(1.0)
                else:
                    self._update_state(TransferState.FAILED)

    def on_cancel(self) -> None:
        """Hủy ngang tiến trình từ phía người dùng hoặc mạng lỗi"""
        with self._lock:
            if self._state not in (TransferState.DONE, TransferState.FAILED, TransferState.CANCELLED):
                self._update_state(TransferState.CANCELLED)
    def on_timeout(self) -> None:
        """Timeout khi quá thời gian nhận file hoặc mất kết nối"""
        with self._lock:
            if self._state not in (
                TransferState.DONE,
                TransferState.FAILED,
                TransferState.CANCELLED
        ):
                self._update_state(TransferState.FAILED)

    # --- Các hàm cập nhật nội bộ và kích hoạt giao diện (Helpers) ---

    def _update_state(self, new_state: TransferState) -> None:
        self._state = new_state
        for cb in self._state_callbacks:
            try:
                cb(new_state)
            except Exception:
                pass

    def _update_progress(self, new_progress: float) -> None:
        self._progress = new_progress
        for cb in self._progress_callbacks:
            try:
                cb(new_progress)
            except Exception:
                pass