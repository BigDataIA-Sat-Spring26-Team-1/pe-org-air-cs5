
import pytest
from unittest.mock import MagicMock, patch
from app.services.s3_storage import AWSService
from botocore.exceptions import ClientError

def test_s3_client_initialization():
    with patch('app.config.settings.AWS_ACCESS_KEY_ID.get_secret_value', return_value=""), \
         patch('app.config.settings.AWS_SECRET_ACCESS_KEY.get_secret_value', return_value=""):
        service = AWSService()
        assert service.s3_client is None

def test_s3_file_presence_check():
    service = AWSService()
    service.s3_client = MagicMock()
    service.bucket = "prod-data"
    
    # Positive case
    service.s3_client.head_object.return_value = {}
    assert service.file_exists("existing/file.json")
    
    # Negative case
    service.s3_client.head_object.side_effect = ClientError({"Error": {"Code": "404"}}, "head_object")
    assert not service.file_exists("missing/file.json")

def test_s3_upload_functionality():
    service = AWSService()
    service.s3_client = MagicMock()
    service.bucket = "prod-data"
    
    success = service.upload_bytes(b"some content", "uploads/data.txt")
    assert success
    service.s3_client.put_object.assert_called()

def test_s3_json_retrieval():
    service = AWSService()
    service.s3_client = MagicMock()
    service.bucket = "prod-data"
    
    mock_body = MagicMock()
    mock_body.read.return_value = b'{"status": "ok"}'
    service.s3_client.get_object.return_value = {"Body": mock_body}
    
    data = service.read_json("configs/app.json")
    assert data["status"] == "ok"
