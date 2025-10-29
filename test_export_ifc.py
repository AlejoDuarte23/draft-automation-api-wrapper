# usage_ifc_export.py
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from classes import (
    ActivityModel,
    ActivityInputParameter,
    ActivityOutputParameter,
    ActivityJsonParameter,
    AppBundleModel
)

from main import (
    get_token,
    get_nickname,
    run_work_item,
    poll_workitem_status,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

# Example constants
app_bundle_name = "IFCExportBundle9"
activity_name = "RevitIFCExportAppActivity8"
alias = "prod"
bucket_key = "bucket_13776_ifc_export10"
zip_path = Path(__file__).parent / "bundles" / "ifcExportDA.bundle.zip"
 
def main() -> None:
    token = get_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    nickname = get_nickname(token)

    appbundle_full_alias = f"{nickname}.{app_bundle_name}+{alias}"
    activity_full_alias = f"{nickname}.{activity_name}+{alias}"
    # Step 1, register and upload the app bundle, then create alias
    bundle = AppBundleModel(
        appBundleId=app_bundle_name,
        engine="Autodesk.Revit+2024",
        alias=alias,
        zip_path=str(zip_path),
        description="Exports IFC from selected views",
    )
    bundle.deploy(token)

    # Step 2, define activity parameters that include storage keys
    input_revit = ActivityInputParameter(
        name="rvtFile",
        localName="input.rvt",
        verb="get",
        description="Input Revit File",
        required=True,
        is_engine_input=True,
        bucketKey=bucket_key,
        objectKey="input.rvt",
    )

    output_zip = ActivityOutputParameter(
        name="result",
        localName="result",
        verb="put",
        description="Zipped IFCs",
        zip=True,
        bucketKey=bucket_key,
        objectKey="IFCExport.zip",
    )

    input_json = ActivityJsonParameter(
        name="ifcSettings",
        localName="ifc_settings.json",
        verb="get",
        description="Export Settings Parameter JSON",
    )

    activity = ActivityModel(
        id=activity_name,
        parameters=[input_revit, output_zip, input_json],
        engine="Autodesk.Revit+2024",
        appbundle_full_name=appbundle_full_alias,
        description="Export IFC from views using JSON settings",
        alias=alias,
    )

    # Step 3, create the activity with alias
    activity.deploy(token=token)

    # Step 4, upload the Revit input
    input_rvt_path = Path(__file__).parent / "bundles" / "SteelStructureFrame.rvt"
    input_revit.upload_file_to_oss(file_path=str(input_rvt_path), token=token)

    # Step 5, read IFC settings
    settings_path = Path(__file__).parent / "bundles" / "export_settings.json"
    with settings_path.open("r", encoding="utf-8") as f:
        settings = json.load(f)

    # Step 6, build work item args from parameters
    wi_args = {
        **input_revit.work_item_arg(token),
        **output_zip.work_item_arg(token), 
        **input_json.work_item_arg(settings)
    }

    # Step 7, run work item
    wi_resp = run_work_item(
        token=token,
        full_activity_alias=activity_full_alias,
        work_item_args=wi_args,
    )
    work_item_id = wi_resp.get("id")
    if not work_item_id:
        raise RuntimeError("No work item id returned")

    # Step 8, poll status
    status_resp = poll_workitem_status(work_item_id, token, max_wait=600, interval=10)
    last_status = status_resp.get("status", "")

    # Step 9, download result if successful
    if last_status == "success":
        out_dir = Path(__file__).parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_zip = out_dir / "IFCExport.zip"
        output_zip.download_to(output_path=str(out_zip), token=token)
        logging.info("Result downloaded to %s", out_zip)
    else:
        logging.error("Work item finished with status: %s", last_status)

if __name__ == "__main__":
    main()
