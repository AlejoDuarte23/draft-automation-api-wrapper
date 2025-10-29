import json
import os
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from main import (
    get_token,
    create_bucket,
    register_appbundle,
    upload_appbundle,
    get_nickname,
    create_appbundle_alias,
    create_activity,
    create_activity_alias,
    run_work_item,
    get_workitem_status,
    get_signed_s3_download,
    dowload_from_signed_url,
)
from classes import (
    ActivityModel, 
    ActivityInputParameter, 
    ActivityOutputParameter, 
    ActivityJsonParameter
)

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def test_full_integration_buildStructureApp3(token: str) -> None:
    app_bundle_name = "IFCExportBundle"
    activity_name = "RevitIFCExportAppActivity"
    bucket_key = "bucket_13776_ifc_export6"
    alias = "prod"
    
    # Get user nickname for fully qualified names
    nickname = get_nickname(token)
    appbundle_full_alias = f"{nickname}.{app_bundle_name}+{alias}"
    activity_full_alias = f"{nickname}.{activity_name}+{alias}"
    
    try:
        # # Step 1: Register anaupload app bundle
        register_response = register_appbundle(appBundleId=app_bundle_name, engine="Autodesk.Revit+2024", token=token, description="Exports IFC from views")
        zip_path = Path(__file__).parent / "bundles" / "ifcExportDA.bundle.zip"
        upload_appbundle(register_response.uploadParameters, zip_path=str(zip_path))
        create_appbundle_alias(token=token, app_id=app_bundle_name, alias_id=alias, version=register_response.version)
        
        # # # Step 2: Define activity parameters
        input_revit = ActivityInputParameter(localName="input.rvt", zip=False, ondemand=False, verb="get", description="Input Revit File")
        output_zip = ActivityOutputParameter(localName="result", zip=True, ondemand=False, verb="put", description="Zipped ifcs")
        input_json = ActivityJsonParameter(localName="ifc_settings.json", zip=False, ondemand=False, verb="get", description="Export Settings Parameter JSON")
        
        parameters = {"ifcSettings": input_json, "result": output_zip, "rvtFile": input_revit}
        
        # # Create activity model
        activity = ActivityModel(id=activity_name, parameters=parameters, engine="Autodesk.Revit+2024", appbundle_full_name=appbundle_full_alias, description="Create Structural Elements with JSON input", alias=alias)
        
        # Set command line for Revit
        activity.set_revit_command_line(input_param_name="rvtFile")
        activity_payload = activity.to_api_dict()
        create_activity(token=token, payload=activity_payload)
        create_activity_alias(activity_id=activity_name, alias_id=alias, version=1, token=token)
        
        # Step 3: Prepare input files and data
        create_bucket(bucketKey=bucket_key, token=token)
        input_file_path = Path(__file__).parent / "bundles" / "SteelStructureFrame.rvt"
        input_revit.upload_file_to_oss(bucketKey=bucket_key, objectKey="input.rvt", file_path=str(input_file_path), token=token)
        
        json_path = Path(__file__).resolve().parent / "bundles" / "export_settings.json"
        with json_path.open("r", encoding="utf-8") as f:
            settings = json.load(f) 

        # Generate work item parameters
        input_wi = input_revit.generate_work_item_params(param_name="rvtFile", bucketKey=bucket_key, objectKey="input.rvt", token=token)
        output_wi = output_zip.generate_work_item_params(param_name="result", bucketKey=bucket_key, objectKey="IFCExport.zip", token=token)
        json_wi = input_json.generate_work_item_params(param_name="ifcSettings", data=settings)
        
        work_item_params = {**input_wi, **output_wi, **json_wi}
        
        # Step 5: Run work item
        work_item_response = run_work_item(token=token, full_activity_alias=activity_full_alias, work_item_args=work_item_params)
        work_item_id = work_item_response.get("id")
        
        if work_item_id:
        # Step 6: Poll work item status
            max_wait_time = 300  # 5 minutes
            poll_interval = 10   # 10 seconds
            elapsed_time = 0
            
            print(f"Polling work item status for ID: {work_item_id}")
            
            while elapsed_time < max_wait_time:
                status_response = get_workitem_status(work_item_id, token)
                print(f"{status_response=}")
                status = status_response.get('status')
                
                print(f"  [{elapsed_time:3d}s] {status}")
                
                if status in ['success', 'failed', 'cancelled']:
                    break
                
                time.sleep(poll_interval)
                elapsed_time += poll_interval
            else:
                print(f"Warning: Timeout after {max_wait_time}s")
                return {
                    "status": "timeout",
                    "workitem_id": work_item_id,
                    "elapsed_time": elapsed_time
                }
            
            # Display results
            final_status = status_response.get('status')
            
            print(f"Work item completed with status: {final_status}")
            if status_response.get('reportUrl'):
                print(f"Report URL: {status_response.get('reportUrl')}")
            
            # Step 7: Download result if successful
            if final_status == 'success':
                download_response = get_signed_s3_download(bucketKey=bucket_key, objectKey="IFCExport.zip", token=token)
                output_path = Path(__file__).parent / "output" / "IFCExport.zip"
                output_path.parent.mkdir(exist_ok=True)
                dowload_from_signed_url(signed_url=download_response["url"], output_path=str(output_path))
                print(f"Result downloaded to: {output_path}")
            else:
                print(f"Work item failed with status: {final_status}")
                if status_response.get('reportUrl'):
                    print("Check the report URL for more details.")
        
    except Exception:
        raise


if __name__ == "__main__":
    token = get_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    
    # Choose which test to run:
    
    # Full integration test (creates everything and runs work item)
    test_full_integration_buildStructureApp3(token)
    
    # Or just test parameter generation
    # test_work_item_parameters_only(token)