import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from main import (
    get_token,
    create_bucket,
    register_appbundle,
    delete_appbundle,
    upload_appbundle,
    get_signed_s3_upload,
    put_to_signed_url,
    complete_signed_s3_upload,
    get_nickname,
    create_appbundle_alias,
    create_activity
)
from classes import ActivityParameter, ActivityModel

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def test_upload_register_appbundle(token: str):
    app_bundle_name = "mytestbundle"
    try:
        register_response = register_appbundle(
            appBundleId=app_bundle_name,
            engine="Autodesk.Revit+2024",
            token=token,
            description="test register",
        )
        zip_path = Path(__file__).parent / "bundles" / "IfcExportDA.bundle.zip"
        status_code = upload_appbundle(
            register_response.uploadParameters, zip_path=str(zip_path)
        )
        print(status_code)

    except Exception as e:
        logging.warning(f"[ERROR] {e}")

    r = delete_appbundle(app_bundle_name, token=token)


def test_upload_and_download_to_bucket(token: str) -> None:
    bucketKey = "374892307487testbucket"
    objectKey = "input.rvt"

    # 1. Path to the file
    zip_path = Path(__file__).parent / "bundles" / "revit_input.rvt"

    # 2. Create bucket
    try:
        bucket_response = create_bucket(bucketKey=bucketKey, token=token)
        logging.info(f"{bucket_response}")
    except Exception:
        pass

    # 3. Generate s3 signed urls
    signed_url_response = get_signed_s3_upload(
        bucketKey=bucketKey, objectKey=objectKey, token=token
    )
    upload_key = signed_url_response.uploadKey
    signed_url = signed_url_response.urls[0]
    logging.info(f"{signed_url=}")

    # 4. Upload to signed s3 key
    status = put_to_signed_url(signed_url=signed_url, file_path=str(zip_path))

    # 5. Confirm Upload
    response = complete_signed_s3_upload(
        bucketKey=bucketKey, objectKey=objectKey, uploadKey=upload_key, token=token
   )
    print(response)
    
    # 5. Get signed url for output
    output_object_key = "new_model_revit.rvt"
    signed_url_for_output = get_signed_s3_upload(bucketKey=bucketKey,objectKey=output_object_key, token=token)
    logging.info(f"{signed_url_for_output=}")

def test_construction_work_item(token: str) -> None:
    from classes import ActivityInputParameter, ActivityJsonParameter, ActivityOutputParameter

    zip_path = Path(__file__).parent / "bundles" / "revit_input.rvt"
    bucketKey = "374892307487testbucket"
    input_revit = ActivityInputParameter(
            localName="input.rvt",
            zip=False,
            ondemand=False,
            verb="get",
            description="Input revit File",
        )
    output_revit = ActivityOutputParameter(
        localName="result.rvt",
        zip=False,
        ondemand=False,
        verb="put",
        description="Input revit File",
    )
    input_json = ActivityJsonParameter(
        localName="structure.json",
        zip=False,
        ondemand=False,
        verb="get",
        description="Structure Parameter Json",
    )
    
    parameters = {"structure": input_json, "result": output_revit, "rvtFile": input_revit}

    # Input File
    input_revit.upload_file_to_oss(bucketKey=bucketKey, objectKey="new_input.rvt",file_path=str(zip_path), token=token)
    input_oss_urn = input_revit.generate_oss_urn(bucketKey=bucketKey, objectKey="new_input.rvt")
    print(f"{input_oss_urn=}")
    
    # Output file
    output_oss_urn = output_revit.generate_oss_urn(bucketKey=bucketKey, objectKey="transmission.rvt")
    print(f"{output_oss_urn=}")
    
    # Generate work item payload
    data={
        "units": "m",
        "connectivity": {
            "1": {"x": 0.0, "y": 0.0, "z": 0.0},
            "2": {"x": 0.0, "y": 6.0, "z": 0.0},
            "3": {"x": 0.0, "y": 0.0, "z": 4.0},
            "4": {"x": 0.0, "y": 6.0, "z": 4.0},
            "5": {"x": 4.0, "y": 0.0, "z": 0.0},
            "6": {"x": 4.0, "y": 6.0, "z": 0.0},
            "7": {"x": 4.0, "y": 0.0, "z": 4.0},
            "8": {"x": 4.0, "y": 6.0, "z": 4.0}
        },
        "lines": {
            "1": {"nodeI": "1", "nodeJ": "3", "section": "UB305x165x4"},
            "2": {"nodeI": "2", "nodeJ": "4", "section": "UB305x165x4"},
            "3": {"nodeI": "5", "nodeJ": "7", "section": "UB305x165x4"},
            "4": {"nodeI": "6", "nodeJ": "8", "section": "UB305x165x4"},
            "5": {"nodeI": "3", "nodeJ": "4", "section": "UB305x165x4"},
            "6": {"nodeI": "7", "nodeJ": "8", "section": "UB305x165x4"},
            "7": {"nodeI": "3", "nodeJ": "7", "section": "UB305x165x4"},
            "8": {"nodeI": "4", "nodeJ": "8", "section": "UB305x165x4"},
            "9": {"nodeI": "1", "nodeJ": "2", "section": "UB305x165x4"},
            "10": {"nodeI": "5", "nodeJ": "6", "section": "UB305x165x4"}
        }
    }

    input_wi = input_revit.generate_work_item_params(param_name="rvtFile", bucketKey=bucketKey, objectKey="new_input.rvt", token=token)

    output_wi= output_revit.generate_work_item_params(param_name="result", bucketKey=bucketKey, objectKey="output.rvt", token=token)
    json_wi = input_json.generate_work_item_params(param_name="structure", data=data)
    wi_params = {**input_wi,**output_wi, **json_wi}
    import pprint
    pprint.pp(wi_params, indent=4)



def test_create_activity(token: str) -> None:
    nickname = get_nickname(token)
    print(f"{nickname=}")
    app_bundle_name = "BuildStructureApp2"
    alias = "dev"
    try:
        nickname = get_nickname(token)
        logging.info(f"{nickname=}")
        register_response = register_appbundle(
            appBundleId=app_bundle_name,
            engine="Autodesk.Revit+2024",
            token=token,
            description="test register",
        )
        zip_path = Path(__file__).parent / "bundles" / "MyRevitAddin.bundle.zip"
        status_code = upload_appbundle(
            register_response.uploadParameters, zip_path=str(zip_path)
        )
        logging.info(f"Upload bundle status {status_code=}")
        # Version increment is an issue for the future
        output = create_appbundle_alias(token=token, app_id=app_bundle_name, alias_id=alias, version=1)
        logging.info(f"Alias output: {output=}")

        appbundle_full_alias = f"{nickname}.{app_bundle_name}+{alias}"
        print(f"{appbundle_full_alias=}")
     
        input_revit = ActivityParameter(
            localName="input.rvt",
            zip=False,
            ondemand=False,
            verb="get",
            description="Input revit File",
        )
        output_revit = ActivityParameter(
            localName="result.rvt",
            zip=False,
            ondemand=False,
            verb="put",
            description="Input revit File",
        )
        input_json = ActivityParameter(
            localName="structure.json",
            zip=False,
            ondemand=False,
            verb="get",
            description="Structure Parameter Json",
        )


        parameters = {"structure": input_json, "result": output_revit, "rvtFile": input_revit}
       
        activity = ActivityModel(
            id="BuildStructureActivity2",
            parameters=parameters,
            engine="Autodesk.Revit+2024",
            appbundle_full_name=appbundle_full_alias,
            description="Create Structural Elements with json",
            alias = "prod"
        )
        activity.set_revit_command_line(input_param_name="rvtFile")
        activity_dictionary = activity.to_api_dict()
        import pprint
        pprint.pp(f"{activity_dictionary=}")
        response = create_activity(token=token, payload=activity_dictionary)
        pprint.pp(f" Create activity response {response=}")
    except Exception as e:
        logging.warning(f"[ERROR] {e}")
        delete_appbundle(app_bundle_name, token=token)

def test_create_activity_payload(token):
    nickname = get_nickname(token)
    app_bundle_name = "my_bundle_name_test"
    alias = "prod"
    appbundle_full_alias = f"{nickname}.{app_bundle_name}+{alias}"
    print(f"{appbundle_full_alias=}")
 
    input_revit = ActivityParameter(
        localName="input.rvt",
        zip=False,
        ondemand=False,
        verb="get",
        description="Input revit File",
    )
    output_revit = ActivityParameter(
        localName="result.rvt",
        zip=False,
        ondemand=False,
        verb="put",
        description="Input revit File",
    )

    input_json = ActivityParameter(
        localName="structure.json",
        zip=False,
        ondemand=False,
        verb="get",
        description="Structure Parameter Json",
    )

    parameters = {"strcture": input_json, "result": output_revit, "rvtFile": input_revit}
    
    activity = ActivityModel(
        id=appbundle_full_alias,
        parameters=parameters,
        engine="Autodesk.Revit+2024",
        appbundle_full_name="BuildStructureApp",
        description="Create Structural Elements with json",
        alias = "prod"
    )
    activity.set_revit_command_line(input_param_name="rvtFile")
    activity_dictionary = activity.to_api_dict()
    import pprint
    pprint.pp(f"{activity_dictionary=}")
   
def test_activity_alias(token):
    from main import create_activity_alias
    #nickname = get_nickname(token=token)
    activity_id = "BuildStructureActivity2"
    alias = "prod"
    response = create_activity_alias(activity_id=activity_id, alias_id=alias,version=1, token=token)
    print(f"{response=}")


if __name__ == "__main__":
    token = get_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    # test_upload_register_appbundle(token=token)
    #test_upload_and_download_to_bucket(token=token)
    # create_activity(token=token)
    #test_create_activity(token)
    #test_activity_alias(token=token)
    test_construction_work_item(token)
