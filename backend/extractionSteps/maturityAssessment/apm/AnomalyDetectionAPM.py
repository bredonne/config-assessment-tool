import json
import logging
from collections import OrderedDict

from api.appd.AppDService import AppDService
from deepdiff import DeepDiff
from extractionSteps.JobStepBase import JobStepBase
from util.asyncio_utils import AsyncioUtils


class AnomalyDetectionAPM(JobStepBase):
    def __init__(self):
        super().__init__("apm")

    async def extract(self, controllerData):
        """
        Extract anomaly detection configuration details.
        1. Makes one API call per application to get Anomaly.
        """
        jobStepName = type(self).__name__

        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Extracting {jobStepName}')
            controller: AppDService = hostInfo["controller"]


            # Gather necessary metrics.
            getAnomalyFutures = []
            getPoliciesFutures = []
            for application in hostInfo[self.componentType].values():
                getAnomalyFutures.append(controller.getAnomalies(application["id"]))
                getPoliciesFutures.append(controller.getPolicies(application["id"]))

            anomalies = await AsyncioUtils.gatherWithConcurrency(*getAnomalyFutures)
            policies = await AsyncioUtils.gatherWithConcurrency(*getPoliciesFutures)

            logging.debug(f"  hostInfo[self.componentType] - { hostInfo[self.componentType]}")

            for idx, applicationName in enumerate(hostInfo[self.componentType]):
                logging.debug(f" idx - {idx}")
                logging.debug(f" applicationName - {applicationName}")
                application = hostInfo[self.componentType][applicationName]
                application["anomalies"] = anomalies[idx].data

                trimmedPos = [policy for policy in policies[idx].data if policy.error is None]
                application["policies"] = {
                    policyList.data["name"]: policyList.data for policyList in trimmedPos if policyList.error is None
                }



    def analyze(self, controllerData, thresholds):
        """
        Analysis of anomaly configuration details.
        1. Determines number of Anomalies
        """

        jobStepName = type(self).__name__

        # Get thresholds related to job
        jobStepThresholds = thresholds[self.componentType][jobStepName]

        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Analyzing {jobStepName}')

            for application in hostInfo[self.componentType].values():
                # Root node of current application for current JobStep.
                analysisDataRoot = application[jobStepName] = OrderedDict()
                # This data goes into the 'JobStep - Metrics' xlsx sheet.
                analysisDataEvaluatedMetrics = analysisDataRoot["evaluated"] = OrderedDict()
                # This data goes into the 'JobStep - Raw' xlsx sheet.
                analysisDataRawMetrics = analysisDataRoot["raw"] = OrderedDict()

                logging.debug(f' anomalies --- {application["anomalies"]}')
                logging.debug(f' anomalies/enabled --- {application["anomalies"]["enabled"]}')

                if "enabled" in application["anomalies"]:
                    analysisDataEvaluatedMetrics["anomalyEnabled"] = application["anomalies"]["enabled"]
                    analysisDataRawMetrics["anomalyEnabled"] = application["anomalies"]["enabled"]
                    analysisDataEvaluatedMetrics["bigPandaAction"] = False
                    analysisDataRawMetrics["bigPandaAction"] = False

                    # look through all policies
					# if anomalyEvents is not empty && actionName BigPanda

                    for idx, policy in application["policies"].items():
                        try:
                            if policy["enabled"] and policy["events"]["anomalyEvents"] is not None :
                                if "actions" in policy:  # Check for Panda Action
                                    for action in policy["actions"]:
                                        if "BigPanda" in str(action["actionName"]):
                                            analysisDataEvaluatedMetrics["bigPandaAction"] = True
                                            analysisDataRawMetrics["bigPandaAction"] = True
                        except (KeyError, TypeError, IndexError):
                            print("Couldn't find a match for the key:")

                else:
                    analysisDataEvaluatedMetrics["anomalyEnabled"] = False
                    analysisDataRawMetrics["anomalyEnabled"] = False
                    analysisDataEvaluatedMetrics["bigPandaAction"] = False
                    analysisDataRawMetrics["bigPandaAction"] = False

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)