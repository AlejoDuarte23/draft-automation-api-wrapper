import requests
import os
from typing import Annotated, Literal, Any
from dotenv import load_dotenv
from dsl import RegisterBundleResponse, UploadParameters, GetSignedS3UrlsResponse, CompleteUploadRequest

load_dotenv()

APS_BASE_URL = "https://developer.api.autodesk.com"
OSS_V2_BASE_URL = f"{APS_BASE_URL}/oss/v2"
OSS_V4_BASE_URL = f"{APS_BASE_URL}/oss/v4"
MD_BASE_URL = f"{APS_BASE_URL}/modelderivative/v2" 
DA_BASE_URL = f"{APS_BASE_URL}/da/us-east/v3" 
AUTH_URL = f"{APS_BASE_URL}/authentication/v2/token"

SCOPES = "data:read data:write data:create bucket:create bucket:read code:all"

def get_token(client_id: str, client_secret: str) -> str:
    response = requests.post(
        AUTH_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": SCOPES,
        },
        timeout=15,
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    return token


def create_bucket(
    bucketKey: Annotated[str, "Unique Name you assign to a bucket, Possible values: -_.a-z0-9 (between 3-128 characters in length"],
    token: Annotated[str, "2Lo token"],
    policy_key: Literal["transient", "temporary", "persistent"]= "transient",
    access: None | Literal["full", "read"] = "full",
    region: Literal["US", "EMEA", "AUS", "CAN", "DEU", "IND", "JPN", "GBN"] = "US",
) -> dict[str, Any]:
    """
    Create a bucket in OSS v2.
    https://aps.autodesk.com/en/docs/data/v2/reference/http/buckets-POST/
    """
    url = f"{OSS_V2_BASE_URL}/buckets"
    payload = {"bucketKey": bucketKey, "access": access, "policyKey": policy_key}
    headers = {
        "Authorization":f"Bearer {token}",
        "Content-Type": "application/json",
        "x-ads-region": region,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def get_signed_s3_upload(
        bucketKey: Annotated[str, "Unique Name you assign to a bucket, Possible values: -_.a-z0-9 (between 3-128 characters in length"],
        objectKey: Annotated[str, "URL-encoded object key to create signed URL for, basicallythenameofthefile"],
        token: Annotated[str, "2Lo Token"]
)->GetSignedS3UrlsResponse:
    """
    We need to check the encoded url part of this!
    """
    url = f"{OSS_V2_BASE_URL}/buckets/{bucketKey}/objects/{objectKey}/signeds3upload"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    response = r.json()
    return GetSignedS3UrlsResponse.model_validate(response)

def put_to_signed_url(signed_url: str, file_path: str) -> int:
    """
    Returns HTTP status code, 200 or 201 indicates success
    """
    with open(file_path, "rb") as f:
        r = requests.put(
            signed_url,
            data=f,
            headers={"Content-Type": "application/octet-stream"},
            timeout=120
        )
        r.raise_for_status()
        return r.status_code

def complete_signed_s3_upload(
        bucketKey: Annotated[str, "Unique Name of the bocket"],
        objectKey: Annotated[str, "URL-encoded object key to create signed URL for, basicallythenameofthefile"],
        uploadKey: Annotated[str, "UploadKey "],
        token: Annotated[str, "2Lo Token"]
    ) -> CompleteUploadRequest:
    url = f"{OSS_V2_BASE_URL}/buckets/{bucketKey}/objects/{objectKey}/signeds3upload"
    payload = {"uploadKey": uploadKey}
    header = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url, headers=header, json=payload, timeout=30)
    r.raise_for_status()
    return CompleteUploadRequest.model_validate(r.json())

def build_oss_urn(
        bucketKey:Annotated[str, "Unique Name of the bucket"],
        objectKey: Annotated[str, "URL-encode object key"]
    ) -> str:
    return f"urn:adsk.objects:os.object:{bucketKey}/{objectKey}"


def register_appbundle(
        appBundleId: Annotated[str, "Name of AppBundle Only alphanumeric characters and _ (underscore) are allowed."],
        engine: Annotated[str, "Engine to be use in the Automation api e.g'Autodesk.Revit+2021'"],
        description: Annotated[str, "App bundle description"],
        token: Annotated[str, "2Lo Token"]
)->RegisterBundleResponse:
    url = f"{DA_BASE_URL}/appbundles" 
    payload = {"id": appBundleId, "engine": engine, "description":description}
    header = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url,headers=header, json=payload)
    r.raise_for_status()
    return RegisterBundleResponse(**r.json())

def upload_appbundle(upload_parameters: UploadParameters, zip_path: str) -> Annotated[int, "Status Code e.g 200"]:
    with open(zip_path, "rb") as f:
        files = {**upload_parameters.formData.model_dump(by_alias=True, exclude_none=True), 'file': (os.path.basename(zip_path), f, "application/octet-stream")}
        r = requests.post(upload_parameters.endpointURL, files=files, timeout=60)
    r.raise_for_status()
    return r.status_code

def delete_appbundle(appbundleId:str, token: str) -> ...:
    """
    If return 204 then ok
    """
    url = f"{DA_BASE_URL}/appbundles/{appbundleId}"
    header = {"Authorization": f"Bearer {token}"}
    r = requests.delete(url=url, headers=header)
    r.raise_for_status() 
    return r.status_code

def get_signed_s3_download(
        bucketKey: Annotated[str, "Unique name of the bucket"],
        objectKey: Annotated[str, "URL-encoded object key to create signed URL for, basicallythenameofthefile"],
        token: Annotated[str, "2Lo Token"]
) -> None:
    url = f"{OSS_V2_BASE_URL}/buckets/{bucketKey}/objects/{objectKey}/signeds3download"
    header = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url=url, headers=header, timeout=30)
    r.raise_for_status()
    return r.json()

def dowload_from_signed_url(
        signed_url: Annotated[str, "Signed url from the previos"],
        output_path: Annotated[str, "Output path str"],
)-> int:
    """
    """
    r = requests.get(signed_url, timeout=120)
    r.raise_for_status()
    
    with open(output_path, "wb") as f:
        f.write(r.content)
    
    return r.status_code
        
def short_appbundle_id(app_bundle_full_alias: Annotated[str, "Example: 'myNick.DeleteWallsApp+test'"]) -> str:
    """
    Extract the short AppBundle id used inside $(appbundles[SHORT].path)
    Example input: 'myNick.DeleteWallsApp+test'
    """
    right = app_bundle_full_alias.split(".", 1)[-1]
    return right.split("+", 1)[0]

 