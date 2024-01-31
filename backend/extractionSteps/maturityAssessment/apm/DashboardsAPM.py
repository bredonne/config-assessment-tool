import logging
from collections import OrderedDict
from datetime import datetime

#from api.appd.AppDService import AppDService
from extractionSteps.JobStepBase import JobStepBase
#from util.asyncio_utils import AsyncioUtils
from util.stdlib_utils import get_recursively


class DashboardsAPM(JobStepBase):
    def __init__(self):
        super().__init__("apm")

    async def extract(self, controllerData):
        """
        Extract Dashboard details.
        1. No API calls to make, simply associate dashboards with which applications they have widgets for.
        """
        jobStepName = type(self).__name__

        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Extracting {jobStepName}')

            # Gather necessary list of reports.
            """
            Close to Minimum Curl Requirements to use the restui endpoint but CAT tool refuses to get data back and only gets 500 error
            Will need to find whats going on with CAT tool and this endpoint, the AppDService has both JSESSIONID and X-CSRF-TOKEN

            curl 'https://amer-ps-sandbox.saas.appdynamics.com/controller/restui/report/list' \
            -H 'Accept: application/json' \
            -H 'Cookie: JSESSIONID=node06dio825ap8gvh1q8dba1s141162821.node0; X-CSRF-TOKEN=8cd30bf3a5c7bf86a6e01426f5dad20cf55f8a28;' \
            """

            # controller: AppDService = hostInfo["controller"]
            # getReportsFutures = []
            # getReportsFutures.append(controller.getReports())
            # reports = await AsyncioUtils.gatherWithConcurrency(*getReportsFutures)

            for dashboard in hostInfo["exportedDashboards"]:
                dashboard["applicationNames"] = get_recursively(dashboard, "applicationName")
                dashboard["applicationIDs"] = get_recursively(dashboard, "applicationId")
                dashboard["adqlQueries"] = get_recursively(dashboard, "adqlQueryList")

            for idx, applicationName in enumerate(hostInfo[self.componentType]):
                application = hostInfo[self.componentType][applicationName]
                application["apmDashboards"] = []
                application["biqDashboards"] = []
                # application["apmReports"] = []

                for dashboard in hostInfo["exportedDashboards"]:
                    if application["name"] in dashboard["applicationNames"]:
                        application["apmDashboards"].append(dashboard)
                    elif application["id"] in dashboard["applicationIDs"]:
                        application["apmDashboards"].append(dashboard)

                    if any(application["name"] in item for item in dashboard["adqlQueries"]):
                        application["biqDashboards"].append(dashboard)

    def analyze(self, controllerData, thresholds):
        """
        Analysis of node level details.
        1. Determines last modified date of dashboards per application.
        2. Determines number of dashboards per application.
        3. Determines number of dashboards with BiQ widgets per application.
        """

        jobStepName = type(self).__name__

        # Get thresholds related to job
        jobStepThresholds = thresholds[self.componentType][jobStepName]

        now = datetime.now()

        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Analyzing {jobStepName}')

            for application in hostInfo[self.componentType].values():
                # Root node of current application for current JobStep.
                analysisDataRoot = application[jobStepName] = OrderedDict()
                # This data goes into the 'JobStep - Metrics' xlsx sheet.
                analysisDataEvaluatedMetrics = analysisDataRoot["evaluated"] = OrderedDict()
                # This data goes into the 'JobStep - Raw' xlsx sheet.
                analysisDataRawMetrics = analysisDataRoot["raw"] = OrderedDict()

                # numberOfDashboards
                analysisDataEvaluatedMetrics["numberOfDashboards"] = len(application["apmDashboards"]) + len(application["biqDashboards"])
                analysisDataRawMetrics["numberOfDashboards"] = len(application["apmDashboards"]) + len(application["biqDashboards"])

                # percentageOfDashboardsModifiedLast6Months
                numDashboardsModifiedLast6Months = 0
                for dashboard in application["apmDashboards"]:
                    modified = datetime.fromtimestamp(dashboard["modifiedOn"] / 1000.0)
                    num_months = (now.year - modified.year) * 12 + (now.month - modified.month)
                    if num_months <= 6:
                        numDashboardsModifiedLast6Months += 1
                for dashboard in application["biqDashboards"]:
                    modified = datetime.fromtimestamp(dashboard["modifiedOn"] / 1000.0)
                    num_months = (now.year - modified.year) * 12 + (now.month - modified.month)
                    if num_months <= 6:
                        numDashboardsModifiedLast6Months += 1
                if len(application["apmDashboards"]) + len(application["biqDashboards"]) == 0:
                    analysisDataEvaluatedMetrics["percentageOfDashboardsModifiedLast6Months"] = 0
                else:
                    analysisDataEvaluatedMetrics["percentageOfDashboardsModifiedLast6Months"] = (
                        numDashboardsModifiedLast6Months / (len(application["apmDashboards"]) + len(application["biqDashboards"])) * 100
                    )

                # numberOfDashboardsUsingBiQ
                analysisDataEvaluatedMetrics["numberOfDashboardsUsingBiQ"] = len(application["biqDashboards"])

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
