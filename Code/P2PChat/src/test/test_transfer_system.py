import unittest
import os
import shutil

from transfer.download_manager import DownloadManager
from transfer.receiver import FileReceiver
from security.crypto import CryptoHandler


class TestTransferSystemIntegration(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.join(
            os.path.dirname(__file__),
            "temp_system_test"
        )
        os.makedirs(self.test_dir, exist_ok=True)

        self.download_manager = DownloadManager(
            download_dir=self.test_dir
        )
        self.receiver = FileReceiver(self.download_manager)
        self.crypto = CryptoHandler()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_end_to_end_secure_transfer(self):
        """Test integration: encrypt/decrypt + receive file end-to-end"""

        # Test crypto
        plaintext = "Hello P2P"

        encrypted = self.crypto.encrypt(plaintext)
        decrypted = self.crypto.decrypt(encrypted)

        self.assertEqual(plaintext, decrypted)

        transfer_id = "sys_test_file_001"

        meta = {
            "filename": "document_secured.txt",
            "file_size": 42,
            "total_chunks": 1,
            "checksum": "dummy"
        }

        # FILE_OFFER
        self.receiver.handle_offer(
            "127.0.0.1",
            {
                "transfer_id": transfer_id,
                "meta": meta
            }
        )

        self.receiver.accept(transfer_id)

        # CHUNK
        chunk_data = b"P2P Secure transfer system works perfectly!"

        self.receiver.handle_chunk(
            "127.0.0.1",
            {
                "transfer_id": transfer_id,
                "index": 0,
                "total_chunks": 1,
                "data": chunk_data.hex()
            }
        )

        # FILE_DONE
        self.receiver.handle_done(
            "127.0.0.1",
            {
                "transfer_id": transfer_id,
                "checksum": "dummy"
            }
        )

        output_path = os.path.join(
            self.test_dir,
            "document_secured.txt"
        )

        self.assertTrue(os.path.exists(output_path))


if __name__ == "__main__":
    unittest.main()