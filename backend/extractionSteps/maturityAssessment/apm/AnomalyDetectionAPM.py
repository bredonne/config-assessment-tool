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
        Extract health rule and alerting configuration details.
        1. Makes one API call per application to get Anomaly.
        """
        jobStepName = type(self).__name__

        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Extracting {jobStepName}')
            controller: AppDService = hostInfo["controller"]

            # /controller/restui/pi/config/application/{ApplicationID} returns true/false if anomaly detection is enabled.
            # ""name"": ""DefaultMLApplicationConfig"",
            # ""enabled"": true"

            # Gather necessary metrics.
            getAnomalyFutures = []
            getPoliciesFutures = []
            for application in hostInfo[self.componentType].values():
                controller.getEventCounts(
                    applicationID=application["id"],
                    entityType="APPLICATION",
                    entityID=application["id"],
                )
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
        Analysis of error configuration details.
        1. Determines number of Anomalies
        """

        jobStepName = type(self).__name__

        logging.info(f" jobStepName - {jobStepName}")
        # AnomalyDetectionAPM
        logging.info(f" self.componentType - {self.componentType}")
        # apm
        logging.info(f" thresholds - {thresholds}")
        # {'apm': {'AppAgentsAPM': {'platinum': {'percentAgentsLessThan1YearOld': 100, 'percentAgentsLessThan2YearsOld': 100, 'percentAgentsReportingData': 100, 'percentAgentsRunningSameVersion': 100, 'metricLimitNotHit': True}, 'gold': {'percentAgentsLessThan1YearOld': 80, 'percentAgentsLessThan2YearsOld': 80, 'percentAgentsReportingData': 80, 'percentAgentsRunningSameVersion': 80, 'metricLimitNotHit': True}, 'silver': {'percentAgentsLessThan1YearOld': 0, 'percentAgentsLessThan2YearsOld': 50, 'percentAgentsReportingData': 0, 'percentAgentsRunningSameVersion': 0, 'metricLimitNotHit': True}, 'direction': {'percentAgentsLessThan1YearOld': 'decreasing', 'percentAgentsLessThan2YearsOld': 'decreasing', 'percentAgentsReportingData': 'decreasing', 'percentAgentsRunningSameVersion': 'decreasing', 'metricLimitNotHit': 'decreasing'}}, 'BusinessTransactionsAPM': {'platinum': {'numberCustomMatchRules': 3, 'btLockdownEnabled': True, 'percentBTsWithLoad': 90, 'numberOfBTs': 200}, 'gold': {'numberCustomMatchRules': 1, 'btLockdownEnabled': False, 'percentBTsWithLoad': 75, 'numberOfBTs': 400}, 'silver': {'numberCustomMatchRules': 0, 'btLockdownEnabled': False, 'percentBTsWithLoad': 0, 'numberOfBTs': 600}, 'direction': {'numberCustomMatchRules': 'decreasing', 'btLockdownEnabled': 'decreasing', 'percentBTsWithLoad': 'decreasing', 'numberOfBTs': 'increasing'}}, 'MachineAgentsAPM': {'platinum': {'percentAgentsLessThan1YearOld': 100, 'percentAgentsLessThan2YearsOld': 100, 'percentAgentsReportingData': 100, 'percentAgentsRunningSameVersion': 100, 'percentAgentsInstalledAlongsideAppAgents': 100}, 'gold': {'percentAgentsLessThan1YearOld': 80, 'percentAgentsLessThan2YearsOld': 80, 'percentAgentsReportingData': 80, 'percentAgentsRunningSameVersion': 80, 'percentAgentsInstalledAlongsideAppAgents': 80}, 'silver': {'percentAgentsLessThan1YearOld': 0, 'percentAgentsLessThan2YearsOld': 50, 'percentAgentsReportingData': 0, 'percentAgentsRunningSameVersion': 0, 'percentAgentsInstalledAlongsideAppAgents': 0}, 'direction': {'percentAgentsLessThan1YearOld': 'decreasing', 'percentAgentsLessThan2YearsOld': 'decreasing', 'percentAgentsReportingData': 'decreasing', 'percentAgentsRunningSameVersion': 'decreasing', 'percentAgentsInstalledAlongsideAppAgents': 'decreasing'}}, 'BackendsAPM': {'platinum': {'backendLimitNotHit': True, 'percentBackendsWithLoad': 75, 'numberOfCustomBackendRules': 1}, 'gold': {'backendLimitNotHit': True, 'percentBackendsWithLoad': 60, 'numberOfCustomBackendRules': 0}, 'silver': {'backendLimitNotHit': True, 'percentBackendsWithLoad': 0, 'numberOfCustomBackendRules': 0}, 'direction': {'backendLimitNotHit': 'decreasing', 'percentBackendsWithLoad': 'decreasing', 'numberOfCustomBackendRules': 'decreasing'}}, 'OverheadAPM': {'platinum': {'developerModeNotEnabledForAnyBT': True, 'developerModeNotEnabledForApplication': True, 'findEntryPointsNotEnabled': True, 'aggressiveSnapshottingNotEnabled': True}, 'gold': {'developerModeNotEnabledForAnyBT': True, 'developerModeNotEnabledForApplication': True, 'findEntryPointsNotEnabled': True, 'aggressiveSnapshottingNotEnabled': True}, 'silver': {'developerModeNotEnabledForAnyBT': True, 'developerModeNotEnabledForApplication': True, 'findEntryPointsNotEnabled': True, 'aggressiveSnapshottingNotEnabled': True}, 'direction': {'developerModeNotEnabledForAnyBT': 'decreasing', 'developerModeNotEnabledForApplication': 'decreasing', 'findEntryPointsNotEnabled': 'decreasing', 'aggressiveSnapshottingNotEnabled': 'decreasing'}}, 'ServiceEndpointsAPM': {'platinum': {'serviceEndpointLimitNotHit': True, 'percentServiceEndpointsWithLoadOrDisabled': 50, 'numberOfCustomServiceEndpointRules': 1}, 'gold': {'serviceEndpointLimitNotHit': True, 'percentServiceEndpointsWithLoadOrDisabled': 25, 'numberOfCustomServiceEndpointRules': 0}, 'silver': {'serviceEndpointLimitNotHit': True, 'percentServiceEndpointsWithLoadOrDisabled': 0, 'numberOfCustomServiceEndpointRules': 0}, 'direction': {'serviceEndpointLimitNotHit': 'decreasing', 'percentServiceEndpointsWithLoadOrDisabled': 'decreasing', 'numberOfCustomServiceEndpointRules': 'decreasing'}}, 'ErrorConfigurationAPM': {'platinum': {'numberOfCustomRules': 1, 'successPercentageOfWorstTransaction': 80}, 'gold': {'numberOfCustomRules': 0, 'successPercentageOfWorstTransaction': 80}, 'silver': {'numberOfCustomRules': 0, 'successPercentageOfWorstTransaction': 50}, 'direction': {'numberOfCustomRules': 'decreasing', 'successPercentageOfWorstTransaction': 'decreasing'}}, 'HealthRulesAndAlertingAPM': {'platinum': {'numberOfHealthRuleViolations': 10, 'numberOfActionsBoundToEnabledPolicies': 1, 'numberOfCustomHealthRules': 5, 'numberOfDefaultHealthRulesModified': 2, 'numberOfAppDBasemonHealthRules': 3}, 'gold': {'numberOfHealthRuleViolations': 20, 'numberOfActionsBoundToEnabledPolicies': 1, 'numberOfCustomHealthRules': 2, 'numberOfDefaultHealthRulesModified': 1, 'numberOfAppDBasemonHealthRules': 3}, 'silver': {'numberOfHealthRuleViolations': 50, 'numberOfActionsBoundToEnabledPolicies': 0, 'numberOfCustomHealthRules': 0, 'numberOfDefaultHealthRulesModified': 0, 'numberOfAppDBasemonHealthRules': 3}, 'direction': {'numberOfHealthRuleViolations': 'increasing', 'numberOfActionsBoundToEnabledPolicies': 'decreasing', 'numberOfCustomHealthRules': 'decreasing', 'numberOfDefaultHealthRulesModified': 'decreasing', 'numberOfAppDBasemonHealthRules': 'increasing'}}, 'DataCollectorsAPM': {'platinum': {'numberOfDataCollectorFieldsConfigured': 5, 'numberOfDataCollectorFieldsCollectedInSnapshots': 5, 'numberOfDataCollectorFieldsCollectedInAnalytics': 5, 'biqEnabled': True}, 'gold': {'numberOfDataCollectorFieldsConfigured': 2, 'numberOfDataCollectorFieldsCollectedInSnapshots': 2, 'numberOfDataCollectorFieldsCollectedInAnalytics': 2, 'biqEnabled': False}, 'silver': {'numberOfDataCollectorFieldsConfigured': 0, 'numberOfDataCollectorFieldsCollectedInSnapshots': 0, 'numberOfDataCollectorFieldsCollectedInAnalytics': 0, 'biqEnabled': False}, 'direction': {'numberOfDataCollectorFieldsConfigured': 'decreasing', 'numberOfDataCollectorFieldsCollectedInSnapshots': 'decreasing', 'numberOfDataCollectorFieldsCollectedInAnalytics': 'decreasing', 'biqEnabled': 'decreasing'}}, 'DashboardsAPM': {'platinum': {'numberOfDashboards': 5, 'percentageOfDashboardsModifiedLast6Months': 100, 'numberOfDashboardsUsingBiQ': 1}, 'gold': {'numberOfDashboards': 1, 'percentageOfDashboardsModifiedLast6Months': 10, 'numberOfDashboardsUsingBiQ': 0}, 'silver': {'numberOfDashboards': 0, 'percentageOfDashboardsModifiedLast6Months': 0, 'numberOfDashboardsUsingBiQ': 0}, 'direction': {'numberOfDashboards': 'decreasing', 'percentageOfDashboardsModifiedLast6Months': 'decreasing', 'numberOfDashboardsUsingBiQ': 'decreasing'}}, 'OverallAssessmentAPM': {'platinum': {'percentageTotalPlatinum': 50, 'percentageTotalGoldOrBetter': 50, 'percentageTotalSilverOrBetter': 100}, 'gold': {'percentageTotalPlatinum': 0, 'percentageTotalGoldOrBetter': 50, 'percentageTotalSilverOrBetter': 90}, 'silver': {'percentageTotalPlatinum': 0, 'percentageTotalGoldOrBetter': 0, 'percentageTotalSilverOrBetter': 80}, 'direction': {'percentageTotalPlatinum': 'decreasing', 'percentageTotalGoldOrBetter': 'decreasing', 'percentageTotalSilverOrBetter': 'decreasing'}}}, 'brum': {'NetworkRequestsBRUM': {'platinum': {'collectingDataPastOneDay': True, 'networkRequestLimitNotHit': True, 'numberCustomMatchRules': 5, 'hasBtCorrelation': True, 'hasCustomEventServiceIncludeRule': True}, 'gold': {'collectingDataPastOneDay': True, 'networkRequestLimitNotHit': True, 'numberCustomMatchRules': 3, 'hasBtCorrelation': False, 'hasCustomEventServiceIncludeRule': False}, 'silver': {'collectingDataPastOneDay': True, 'networkRequestLimitNotHit': True, 'numberCustomMatchRules': 2, 'hasBtCorrelation': False, 'hasCustomEventServiceIncludeRule': False}, 'direction': {'collectingDataPastOneDay': 'decreasing', 'networkRequestLimitNotHit': 'decreasing', 'numberCustomMatchRules': 'decreasing', 'hasBtCorrelation': 'decreasing', 'hasCustomEventServiceIncludeRule': 'decreasing'}}, 'HealthRulesAndAlertingBRUM': {'platinum': {'numberOfHealthRuleViolations': 10, 'numberOfActionsBoundToEnabledPolicies': 1, 'numberOfCustomHealthRules': 5}, 'gold': {'numberOfHealthRuleViolations': 20, 'numberOfActionsBoundToEnabledPolicies': 1, 'numberOfCustomHealthRules': 2}, 'silver': {'numberOfHealthRuleViolations': 50, 'numberOfActionsBoundToEnabledPolicies': 0, 'numberOfCustomHealthRules': 0}, 'direction': {'numberOfHealthRuleViolations': 'increasing', 'numberOfActionsBoundToEnabledPolicies': 'decreasing', 'numberOfCustomHealthRules': 'decreasing'}}, 'OverallAssessmentBRUM': {'platinum': {'percentageTotalPlatinum': 50, 'percentageTotalGoldOrBetter': 50, 'percentageTotalSilverOrBetter': 100}, 'gold': {'percentageTotalPlatinum': 0, 'percentageTotalGoldOrBetter': 50, 'percentageTotalSilverOrBetter': 90}, 'silver': {'percentageTotalPlatinum': 0, 'percentageTotalGoldOrBetter': 0, 'percentageTotalSilverOrBetter': 80}, 'direction': {'percentageTotalPlatinum': 'decreasing', 'percentageTotalGoldOrBetter': 'decreasing', 'percentageTotalSilverOrBetter': 'decreasing'}}}, 'mrum': {'NetworkRequestsMRUM': {'platinum': {'collectingDataPastOneDay': True, 'networkRequestLimitNotHit': True, 'numberCustomMatchRules': 5, 'hasBtCorrelation': True, 'hasCustomEventServiceIncludeRule': True}, 'gold': {'collectingDataPastOneDay': True, 'networkRequestLimitNotHit': True, 'numberCustomMatchRules': 3, 'hasBtCorrelation': False, 'hasCustomEventServiceIncludeRule': False}, 'silver': {'collectingDataPastOneDay': True, 'networkRequestLimitNotHit': True, 'numberCustomMatchRules': 2, 'hasBtCorrelation': False, 'hasCustomEventServiceIncludeRule': False}, 'direction': {'collectingDataPastOneDay': 'decreasing', 'networkRequestLimitNotHit': 'decreasing', 'numberCustomMatchRules': 'decreasing', 'hasBtCorrelation': 'decreasing', 'hasCustomEventServiceIncludeRule': 'decreasing'}}, 'HealthRulesAndAlertingMRUM': {'platinum': {'numberOfHealthRuleViolations': 10, 'numberOfActionsBoundToEnabledPolicies': 1, 'numberOfCustomHealthRules': 5}, 'gold': {'numberOfHealthRuleViolations': 20, 'numberOfActionsBoundToEnabledPolicies': 1, 'numberOfCustomHealthRules': 2}, 'silver': {'numberOfHealthRuleViolations': 50, 'numberOfActionsBoundToEnabledPolicies': 0, 'numberOfCustomHealthRules': 0}, 'direction': {'numberOfHealthRuleViolations': 'increasing', 'numberOfActionsBoundToEnabledPolicies': 'decreasing', 'numberOfCustomHealthRules': 'decreasing'}}, 'OverallAssessmentMRUM': {'platinum': {'percentageTotalPlatinum': 50, 'percentageTotalGoldOrBetter': 50, 'percentageTotalSilverOrBetter': 100}, 'gold': {'percentageTotalPlatinum': 0, 'percentageTotalGoldOrBetter': 50, 'percentageTotalSilverOrBetter': 90}, 'silver': {'percentageTotalPlatinum': 0, 'percentageTotalGoldOrBetter': 0, 'percentageTotalSilverOrBetter': 80}, 'direction': {'percentageTotalPlatinum': 'decreasing', 'percentageTotalGoldOrBetter': 'decreasing', 'percentageTotalSilverOrBetter': 'decreasing'}}}}

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

                # anomalyEnabled

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