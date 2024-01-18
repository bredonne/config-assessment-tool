import logging
from collections import OrderedDict

from extractionSteps.JobStepBase import JobStepBase


class OverallAssessmentAPM_WF(JobStepBase):
    def __init__(self):
        super().__init__("apm")

    async def extract(self, controllerData):
        pass

    def analyze(self, controllerData, thresholds):
        """
        Analysis of overall results to determine classification
        """

        jobStepName = type(self).__name__

        jobStepNames = [
            "AppAgentsAPM",
            "MachineAgentsAPM",
            "BusinessTransactionsAPM",
            "BackendsAPM",
            "OverheadAPM",
            "ServiceEndpointsAPM",
            "ErrorConfigurationAPM",
            "HealthRulesAndAlertingAPM",
            "DataCollectorsAPM",
            "DashboardsAPM",
        ]

        num_job_steps = len(jobStepNames)

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

                num_silver = 0
                num_gold = 0
                num_platinum = 0

                for individualJobStepName in jobStepNames:
                    job_step_color = application[individualJobStepName]["computed"]
                    if job_step_color[0] == "silver":
                        num_silver = num_silver + 1
                    elif job_step_color[0] == "gold":
                        num_gold = num_gold + 1
                    elif job_step_color[0] == "platinum":
                        num_platinum = num_platinum + 1

                #analysisDataEvaluatedMetrics["percentageTotalPlatinum"] = num_platinum / num_job_steps * 100
                #analysisDataEvaluatedMetrics["percentageTotalGoldOrBetter"] = (num_platinum + num_gold) / num_job_steps * 100
                #analysisDataEvaluatedMetrics["percentageTotalSilverOrBetter"] = (num_platinum + num_gold + num_silver) / num_job_steps * 100

                HealthRulesAndAlertingAPM_RAW = application["HealthRulesAndAlertingAPM"]["raw"]
                BusinessTransactionsAPM_RAW = application["BusinessTransactionsAPM"]["raw"]

                #WellsFargo BASEMONHealthRuleScore check
                analysisDataEvaluatedMetrics["HealthRuleScore"] = 0
                if HealthRulesAndAlertingAPM_RAW['numberOfAppDBasemonHealthRules'] == 0 and HealthRulesAndAlertingAPM_RAW["Basemonandbigpandaenabled"] == 0 and HealthRulesAndAlertingAPM_RAW["numberOfCustomHealthRules"] == 0:
                    analysisDataEvaluatedMetrics["HealthRuleScore"] = 0
                if 1 <= HealthRulesAndAlertingAPM_RAW['numberOfAppDBasemonHealthRules'] <= 3 and HealthRulesAndAlertingAPM_RAW["Basemonandbigpandaenabled"] == 0:
                    analysisDataEvaluatedMetrics["HealthRuleScore"] = 1
                if HealthRulesAndAlertingAPM_RAW['numberOfAppDBasemonHealthRules'] >= 7 and HealthRulesAndAlertingAPM_RAW["numberOfCustomHealthRules"] >= 1:
                    analysisDataEvaluatedMetrics["HealthRuleScore"] = 2
                if HealthRulesAndAlertingAPM_RAW['numberOfAppDBasemonHealthRules'] >= 7 and HealthRulesAndAlertingAPM_RAW["Basemonandbigpandaenabled"] >= 1 and HealthRulesAndAlertingAPM_RAW["numberOfCustomHealthRules"] >= 1:
                    analysisDataEvaluatedMetrics["HealthRuleScore"] = 3

                # WellsFargo BTRuleScore check
                analysisDataEvaluatedMetrics["BTScore"] = 0
                if BusinessTransactionsAPM_RAW["numberCustomMatchRules"] == 0 and not BusinessTransactionsAPM_RAW["btLockdownEnabled"] and not BusinessTransactionsAPM_RAW["numberOfRulesWithNonZeroPriority"] >> 0:
                    analysisDataEvaluatedMetrics["BTScore"] = 0
                if BusinessTransactionsAPM_RAW["numberCustomMatchRules"] == 0 and BusinessTransactionsAPM_RAW["btLockdownEnabled"]:
                    analysisDataEvaluatedMetrics["BTScore"] = 1
                if (BusinessTransactionsAPM_RAW["numberCustomMatchRules"] >> 0 or BusinessTransactionsAPM_RAW["btLockdownEnabled"]) and BusinessTransactionsAPM_RAW["numberOfRulesWithNonZeroPriority"] >> 0:
                    analysisDataEvaluatedMetrics["BTScore"] = 2
                if BusinessTransactionsAPM_RAW["btLockdownEnabled"] and (BusinessTransactionsAPM_RAW["numberCustomMatchRules"] >> 0 or BusinessTransactionsAPM_RAW["numberOfRulesWithNonZeroPriority"] >> 0) and BusinessTransactionsAPM_RAW["businessTransactionsWithLoad"] << 200:
                    analysisDataEvaluatedMetrics["BTScore"] = 3

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
