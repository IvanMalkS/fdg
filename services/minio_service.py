from minio import Minio
from minio.error import S3Error
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, Tuple
from config import Config
from services.logger import logger

load_dotenv()

class MinioService:
    def __init__(self):
        self.client = Minio(
            f"{Config.MINIO_HOST}:{Config.MINIO_PORT}",
            access_key=Config.MINIO_USER,
            secret_key=Config.MINIO_PASSWORD,
            secure=Config.SECURE
        )
        self.bucket_name = "user-reports"
        self._ensure_bucket_exists()
        self._make_bucket_public()

    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Бакет '{self.bucket_name}' создан")
        except S3Error as e:
            logger.error(f"Не удалось создать бакет: {e}")
            raise

    def _make_bucket_public(self):
        try:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": ["s3:GetObject"],
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"],
                        "Sid": ""
                    }
                ]
            }
            import json
            self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
            logger.info(f"Бакет '{self.bucket_name}' теперь публичный (read-only)")
        except S3Error as e:
            logger.error(f"Не удалось сделать бакет публичным: {e}")

    async def upload_report(self, user_id: int, file_data: BytesIO, file_extension: str = "xlsx") -> Tuple[bool, str]:
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reports/{user_id}/DAMA_Report_{user_id}_{timestamp}.{file_extension}"

            file_data.seek(0)
            file_size = file_data.getbuffer().nbytes

            content_type_map = {
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "csv": "text/csv",
                "pdf": "application/pdf"
            }

            self.client.put_object(
                self.bucket_name,
                filename,
                file_data,
                file_size,
                content_type=content_type_map.get(file_extension, "application/octet-stream")
            )

            return True, filename
        except S3Error as e:
            logger.error(f"Проблема с отправкой файла: {e}")
            return False, str(e)

    async def get_report_url(self, filename: str) -> Optional[str]:
        try:
            protocol = "https" if Config.SECURE else "http"
            return f"{protocol}://{Config.MINIO_HOST}:{Config.MINIO_PORT}/{self.bucket_name}/{filename}"
        except Exception as e:
            logger.error(f"Ошибка при построении URL: {e}")
            return None

    async def delete_report(self, filename: str) -> bool:
        try:
            self.client.remove_object(self.bucket_name, filename)
            return True
        except S3Error as e:
            logger.error(f"Произошла ошибка при удалении файла: {e}")
            return False
