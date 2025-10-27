import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from main import get_token, create_bucket, register_appbundle, delete_appbundle, upload_appbundle, get_signed_s3_upload, put_to_signed_url, complete_signed_s3_upload

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def test_upload_register_appbundle(token:str):
    app_bundle_name = "mytestbundle"
    try:
        register_response = register_appbundle(
            appBundleId=app_bundle_name, engine="Autodesk.Revit+2024",token=token, description="test register")
        zip_path=Path(__file__).parent / "bundles" / "IfcExportDA.bundle.zip"
        status_code = upload_appbundle(register_response.uploadParameters, zip_path=str(zip_path))
        print(status_code)
        
    except Exception as e:
        logging.warning(f"[ERROR] {e}")

    r = delete_appbundle(app_bundle_name, token=token)

def test_upload_and_download_to_bucket(token: str) -> None: 
    bucketKey = "natalisbucket5"
    objectKey = "wombat4.rvt"

    # 1. Path to the file
    zip_path=Path(__file__).parent / "bundles" / "SteelPortalFrame.rvt"
    
    #2. Create bucket
    try:
        bucket_response = create_bucket(bucketKey=bucketKey, token=token)
    except Exception:
        pass
    
    #3. Generate s3 signed urls
    signed_url_response = get_signed_s3_upload(bucketKey=bucketKey, objectKey=objectKey, token=token)
    upload_key = signed_url_response.uploadKey
    signed_url = signed_url_response.urls[0]
    print(f"{signed_url=}")
    
    #4. Upload to signed s3 key
    status = put_to_signed_url(signed_url=signed_url, file_path=str(zip_path))
    
    # 5. Confirm Upload
    response = complete_signed_s3_upload(bucketKey=bucketKey, objectKey=objectKey, uploadKey=upload_key, token=token)
    print(response)






if __name__ == "__main__":
    token = get_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    print(token)
    #test_upload_register_appbundle(token=token)
    test_upload_and_download_to_bucket(token=token)