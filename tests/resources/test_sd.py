from appian_locust import AppianTaskSet, SailUiForm, helper
from locust import task, HttpUser, between


class SiteDesignerTaskSet(AppianTaskSet):

    @task
    def nav_to_site_designer(self):
        uri = "/suite/rest/a/applications/latest/app/design/koBHer_bdD8Emw8hLHIVbTE4VVYhe67L0vlHTpP4tgRJpQLzriXFo6NxZ2dZZJAhDGELUiEJfv4fTh6Y4tJc1q2NxztJuzv-XyAYA"
        # uri = "/suite/rest/a/applications/latest/app/design/koBRiBJbvt7QuRiqjQRMM3to01_ihyZOZXelvq2wVBYCVYJjp5azZLattqab0AluZv9C7OaLSY2kBts5BU09-bwMfqciz39GHYWTw"
        headers = self.appian.interactor.setup_sail_headers()
        headers['X-Client-Mode'] = 'DESIGN'
        resp = self.appian.interactor.get_page(uri, label="LoadSiteDesignerPage", headers=headers)
        # print(resp)
        # print(resp.text)
        form = SailUiForm(self.appian.interactor, resp.json(), uri, breadcrumb='SitesDesigner')
        form = form.click('Add Page').select_dropdown_item('Type', 'Record List')
        for extr in helper.extract_values(form.state, 'label', 'Content'):
            print('Choices after selecting record list ' + str(len(extr['choices'])))
        form = form.select_dropdown_item('Type', 'Report')
        for extr in helper.extract_values(form.state, 'label', 'Content'):
            print('Choices after selecting report ' + str(len(extr['choices'])))


class Actor(HttpUser):
    wait_time = between(0.5, 0.5)
    tasks = [SiteDesignerTaskSet]
    config = {}
