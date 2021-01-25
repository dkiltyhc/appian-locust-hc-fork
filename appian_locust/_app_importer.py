from typing import Any, Dict, Optional

from . import logger
from ._interactor import _Interactor
from .helper import extract_all_by_label, find_component_by_attribute_in_dict
from .uiform import SailUiForm, raises_locust_error

log = logger.getLogger(__name__)


DESIGN_URI_PATH: str = "/suite/rest/a/applications/latest/app/design"


class AppImporter:
    def __init__(self, interactor: _Interactor):
        self.interactor = interactor

    @raises_locust_error("_app_importer.import_app")
    def import_app(self, app_file_path: str, customization_file_path: str = None, inspect_and_import: bool = False) -> Optional[Dict[str, Any]]:
        """
        Imports an application via the design environment

        Args:
            app_file_path (str): path to the application on the local system
            customization_file_path (str): path to the customization file
            inspect_and_import(bool) : if True => first inspect and then import else simply import
        Returns: Latest state of the form as a dictionary
        """
        # Navigate to Design
        headers = self.interactor.setup_sail_headers()
        headers['X-Client-Mode'] = 'DESIGN'
        label = "Design.LandingPage"
        response = self.interactor.get_page(DESIGN_URI_PATH, headers=headers, label=label)
        response.raise_for_status()
        initial_form = SailUiForm(self.interactor, response.json(), DESIGN_URI_PATH, breadcrumb=f'{label}.SailUi')

        # Open the import modal
        modal_form = initial_form.click_button("Import")

        # Upload Package
        modal_form = modal_form.upload_document_to_upload_field("Package (ZIP)", app_file_path)

        # Optionally upload import cust file
        if customization_file_path:
            modal_form = modal_form.check_checkbox_by_test_label("propertiesCheckboxField", [1])
            modal_form.upload_document_to_upload_field("Import Customization File (PROPERTIES)", customization_file_path)

        if inspect_and_import:
            log.info("First inspecting and then importing the package")
            modal_form = modal_form.click_button("Inspect").get_latest_form().click_button("Import Package").get_latest_form()
        else:
            log.info("Simply importing the package")
            modal_form = modal_form.click_button("Import")

        import_result = find_component_by_attribute_in_dict("testLabel", "importResultsText", modal_form.state)
        if import_result:
            log.info(f"Import of {app_file_path} was successful")
            import_message = import_result.get("value", {}).get("values", {})[0].get("#v", {})
            log.info(import_message)
        else:
            validations: list = extract_all_by_label(modal_form.state, "validations")
            raise Exception(f"Import failed, validation were {validations}")
        return modal_form.state
