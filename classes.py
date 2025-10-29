import json
from main import (
    create_bucket,
    get_signed_s3_upload,
    put_to_signed_url,
    complete_signed_s3_upload,
    build_oss_urn,
)
from pydantic import BaseModel, Field
from typing import Literal, Any


class ActivityParameter(BaseModel):
    zip: bool = Field(default=False)
    ondemand: bool = Field(default=False)
    verb: Literal["get", "put", "post"]
    description: str
    required: bool = Field(default=False)
    localName: str

    def upload_file_to_oss(
        self, bucketKey: str, objectKey: str, file_path: str, token: str
    ) -> None:
        try:
            bucket_response = create_bucket(bucketKey=bucketKey, token=token)
            # get resposne if bucket already exists and son on
        except Exception:
            pass

        # 3. Generate s3 signed urls
        signed_url_response = get_signed_s3_upload(
            bucketKey=bucketKey, objectKey=objectKey, token=token
        )
        upload_key = signed_url_response.uploadKey
        signed_url = signed_url_response.urls[0]

        # 4. Upload to signed s3 key
        status = put_to_signed_url(signed_url=signed_url, file_path=file_path)

        # 5. Confirm Upload
        response = complete_signed_s3_upload(
            bucketKey=bucketKey, objectKey=objectKey, uploadKey=upload_key, token=token
        )
        print(response)

    def generate_oss_urn(self, bucketKey: str, objectKey: str) -> str:
        return build_oss_urn(bucketKey=bucketKey, objectKey=objectKey)


class ActivityInputParameter(ActivityParameter):

    def generate_work_item_params(
        self, param_name: str, bucketKey: str, objectKey: str, token: str
    ):
        return {
            param_name: {
                "url": self.generate_oss_urn(bucketKey, objectKey),
                "verb": self.verb,
                "headers": {"Authorization": f"Bearer {token}"},
            }
        }


class ActivityOutputParameter(ActivityInputParameter):
    pass


class ActivityJsonParameter(ActivityParameter):
    def generate_work_item_params(self, param_name: str, data: dict):
        data_str = json.dumps(data, separators=(",", ":"))
        return {
            param_name: {
                "url": f"data:application/json, {data_str}",
            }
        }


class ActivityModel(BaseModel):
    """Works for a single app bundle"""

    id: str
    commandLine: list[str] | None = None
    parameters: dict[str, ActivityParameter]
    engine: str | None
    appbundle_full_name: str
    description: str
    alias: str

    def to_api_dict(self) -> dict[str, Any]:
        params_dump = {
            k: p.model_dump(by_alias=True) for k, p in self.parameters.items()
        }
        return {
            "id": self.id,
            "commandLine": self.commandLine,
            "parameters": params_dump,
            "engine": self.engine,
            "appbundles": [self.appbundle_full_name],
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
        appbundle_short_id = self.short_appbundle_id(self.appbundle_full_name)
        self.commandLine = (
            "$(engine.path)\\revitcoreconsole.exe "
            f'/i "$(args[{input_param_name}].path)" '
            f'/al "$(appbundles[{appbundle_short_id}].path)"'
        )