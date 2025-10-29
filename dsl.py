from pydantic import BaseModel, Field, ConfigDict, AliasChoices, HttpUrl
from typing import Literal, Any

class FormData(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    key: str
    policy: str
    success_action_status: str = Field(alias="success_action_status")
    success_action_redirect: str = Field(alias="success_action_redirect")

    # Exactly as in the sample: "content-type"
    content_type: str | None = Field(default=None, alias="content-type")

    x_amz_signature: str | None = Field(default=None, alias="x-amz-signature")
    x_amz_credential: str | None = Field(default=None, alias="x-amz-credential")
    x_amz_algorithm: str | None = Field(default=None, alias="x-amz-algorithm")
    x_amz_date: str | None = Field(default=None, alias="x-amz-date")
    x_amz_server_side_encryption: str | None = Field(default=None, alias="x-amz-server-side-encryption")
    x_amz_security_token: str | None = Field(default=None, alias="x-amz-security-token")



class UploadParameters(BaseModel):
    endpointURL: str 
    formData: FormData


class RegisterBundleResponse(BaseModel):
    uploadParameters: UploadParameters
    id: str
    engine: str
    description: str | None = Field(default=None)
    version: int
    
class GetSignedS3UrlsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    uploadKey: str
    urls: list[str]
    urlExpiration: str | None = None
    uploadExpiration: str | None = None
    # Only present when the URL request failed, per APS schema
    status: str | None = None
    reason: str | None = None


class CompleteUploadRequest(BaseModel):
  bucketKey:str 
  objectId:str 
  objectKey:str
  size: int
  contentType: str
  location: str

class GetDownloadS3Url(BaseModel):
    status: str
    url: str
    params: dict
    size: int
    sha1: str
    
