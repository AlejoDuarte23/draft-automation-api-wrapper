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
    
class ActivityParameter:
    zip: bool = Field(default=False)
    on_demand: bool = Field(default=False)
    verb: Literal["get", "put", "post"]
    description: str
    required: bool = Field(default=False)
    local_name: str
    
    
class ActivityModel(BaseModel):
    """ Works for a single app bundle"""
    id: str
    commandLine: list[str]
    parameters: dict[str, ActivityParameter]
    engine: str | None
    appbundle_name: str
    description: str

    def to_api_dict(self) -> dict[str, Any]:
        params_dump = {k: p.model_dump(by_alias=True) for k, p in self.parameters.items()}
        return {
            "id": self.id,
            "commandLine": self.commandLine,
            "parameters": params_dump,
            "engine": self.engine,
            "appbundles": [self.appbundle_name],
            "description": self.description,
        }

    @staticmethod
    def short_appbundle_id(appbundle_full_alias: str) -> str:
        """Check"""
        # "MyBundle+prod" -> "MyBundle"
        right = appbundle_full_alias.split(".", 1)[-1]
        return right.split("+", 1)[0]

    def set_revit_command_line(
        self,
        input_param_name: str,
    ) -> None:
        appbundle_short_id = self.short_appbundle_id(self.appbundle_name)
        self.engine = (
            f"$({self.engine})\\revitcoreconsole.exe "
            f'/i "$(args[{input_param_name}].path)" '
            f'/al "$(appbundles[{appbundle_short_id}].path)"'
        )


        
