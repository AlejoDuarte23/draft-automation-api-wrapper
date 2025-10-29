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
    app_bundle_name = "BuildStructureApp3"
    activity_name = "BuildStructureActivity3"
    bucket_key = "374892307487testbucket"
    alias = "prod"
    
    # Get user nickname for fully qualified names
    nickname = get_nickname(token)
    appbundle_full_alias = f"{nickname}.{app_bundle_name}+{alias}"
    activity_full_alias = f"{nickname}.{activity_name}+{alias}"
    
    try:
        # Step 1: Register andupload app bundle
        register_response = register_appbundle(appBundleId=app_bundle_name, engine="Autodesk.Revit+2024", token=token, description="BuildStructureApp3 - Creates structural elements from JSON input")
        zip_path = Path(__file__).parent / "bundles" / "MyRevitAddin.bundle.zip"
        upload_appbundle(register_response.uploadParameters, zip_path=str(zip_path))
        create_appbundle_alias(token=token, app_id=app_bundle_name, alias_id=alias, version=register_response.version)
        
        # Step 2: Define activity parameters
        input_revit = ActivityInputParameter(localName="input.rvt", zip=False, ondemand=False, verb="get", description="Input Revit File")
        output_revit = ActivityOutputParameter(localName="result.rvt", zip=False, ondemand=False, verb="put", description="Output Revit File")
        input_json = ActivityJsonParameter(localName="structure.json", zip=False, ondemand=False, verb="get", description="Structure Parameter JSON")
        
        parameters = {"structure": input_json, "result": output_revit, "rvtFile": input_revit}
        
        # Create activity model
        activity = ActivityModel(id=activity_name, parameters=parameters, engine="Autodesk.Revit+2024", appbundle_full_name=appbundle_full_alias, description="Create Structural Elements with JSON input", alias=alias)
        
        # Set command line for Revit
        activity.set_revit_command_line(input_param_name="rvtFile")
        activity_payload = activity.to_api_dict()
        create_activity(token=token, payload=activity_payload)
        create_activity_alias(activity_id=activity_name, alias_id=alias, version=1, token=token)
        
        # Step 3: Prepare input files and data
        create_bucket(bucketKey=bucket_key, token=token)
        input_file_path = Path(__file__).parent / "bundles" / "revit_input.rvt"
        input_revit.upload_file_to_oss(bucketKey=bucket_key, objectKey="buildStructure_input.rvt", file_path=str(input_file_path), token=token)
        
        # Step 4: Prepare work item parameters and structure data
        structure_data = {
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
                "1": {"nodeI": "1", "nodeJ": "3", "section": "UB305x165x40"},
                "2": {"nodeI": "2", "nodeJ": "4", "section": "UB305x165x40"},
                "3": {"nodeI": "5", "nodeJ": "7", "section": "UB305x165x40"},
                "4": {"nodeI": "6", "nodeJ": "8", "section": "UB305x165x40"},
                "5": {"nodeI": "3", "nodeJ": "4", "section": "UB305x165x40"},
                "6": {"nodeI": "7", "nodeJ": "8", "section": "UB305x165x40"},
                "7": {"nodeI": "3", "nodeJ": "7", "section": "UB305x165x40"},
                "8": {"nodeI": "4", "nodeJ": "8", "section": "UB305x165x40"},
                "9": {"nodeI": "1", "nodeJ": "2", "section": "UB305x165x40"},
                "10": {"nodeI": "5", "nodeJ": "6", "section": "UB305x165x40"}
            }
        }
        
        # Generate work item parameters
        input_wi = input_revit.generate_work_item_params(param_name="rvtFile", bucketKey=bucket_key, objectKey="buildStructure_input.rvt", token=token)
        output_wi = output_revit.generate_work_item_params(param_name="result", bucketKey=bucket_key, objectKey="buildStructure_output.rvt", token=token)
        json_wi = input_json.generate_work_item_params(param_name="structure", data=structure_data)
        
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
                download_response = get_signed_s3_download(bucketKey=bucket_key, objectKey="buildStructure_output.rvt", token=token)
                output_path = Path(__file__).parent / "output" / "buildStructure_result.rvt"
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