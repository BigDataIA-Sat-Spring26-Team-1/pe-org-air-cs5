import boto3
from botocore.exceptions import ClientError
import structlog
from app.config import settings

logger = structlog.get_logger()


class AWSService:
    def __init__(self):
        if settings.AWS_ACCESS_KEY_ID.get_secret_value() and settings.AWS_SECRET_ACCESS_KEY.get_secret_value():
            from botocore.config import Config
            config = Config(max_pool_connections=50)
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID.get_secret_value(),
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY.get_secret_value(),
                region_name=settings.AWS_REGION,
                config=config
            )
        else:
            logger.warning("AWS credentials missing")
            self.s3_client = None

        self.bucket = settings.S3_BUCKET

    def file_exists(self, s3_key: str) -> bool:
        if not self.s3_client:
            return False
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError:
            return False

    def upload_file(self, file_path: str, s3_key: str) -> bool:
        if not self.s3_client:
            return False
        try:
            self.s3_client.upload_file(file_path, self.bucket, s3_key)
            logger.info("request_sent", type="upload", bucket=self.bucket, key=s3_key)
            return True
        except ClientError as e:
            logger.error("upload_failed", error=str(e), key=s3_key)
            return False

    def upload_bytes(self, data: bytes, s3_key: str, content_type: str = "text/plain") -> bool:
        if not self.s3_client:
            return False
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=data,
                ContentType=content_type
            )
            return True
        except ClientError as e:
            logger.error("upload_bytes_failed", error=str(e), key=s3_key)
            return False

    def read_json(self, s3_key: str) -> dict | list | None:
        """Read a JSON file from S3."""
        if not self.s3_client:
            return None
        try:
            import json
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)
        except ClientError as e:
            logger.error("read_json_failed", error=str(e), key=s3_key)
            return None
        except Exception as e:
            logger.error("read_json_parse_error", error=str(e), key=s3_key)
            return None

    def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3."""
        if not self.s3_client:
            return False
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info("file_deleted", bucket=self.bucket, key=s3_key)
            return True
        except ClientError as e:
            logger.error("delete_file_failed", error=str(e), key=s3_key)
            return False


aws_service = AWSService()
