import logging
from collections import OrderedDict

from extractionSteps.JobStepBase import JobStepBase


class OverallAssessmentBRUM_WF(JobStepBase):
    def __init__(self):
        super().__init__("brum")

    async def extract(self, controllerData):
        pass

    def analyze(self, controllerData, thresholds):
        """
        Analysis of overall results to determine classification
        """

        jobStepName = type(self).__name__

        jobStepNames = ["NetworkRequestsBRUM", "HealthRulesAndAlertingBRUM"]

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


                NetworkRequestsBRUM_RAW = application["NetworkRequestsBRUM"]["raw"]

                #Generate scorecard pass/fail for session timeoout.
                sessionTimeoutMin = 0
                if "sessionTimeoutMin" in NetworkRequestsBRUM_RAW:
                    sessionTimeoutMin = NetworkRequestsBRUM_RAW["sessionTimeoutMin"]
                if sessionTimeoutMin != 5:
                    analysisDataEvaluatedMetrics["sessionTimeout"] = 0
                else:
                    analysisDataEvaluatedMetrics["sessionTimeout"] = 1

                # Generate scorecard pass/fail for custom BRUM include rules.
                numberOfCustomURLRules = 0
                analysisDataEvaluatedMetrics["numberOfCustomURLRules"] = 0
                if "numberOfCustomURLIncludeRules" in NetworkRequestsBRUM_RAW and "numberOfCustomURLExcludeRules" in NetworkRequestsBRUM_RAW:
                    if (NetworkRequestsBRUM_RAW["numberOfCustomURLIncludeRules"] + NetworkRequestsBRUM_RAW["numberOfCustomURLExcludeRules"]) > 0:
                        analysisDataEvaluatedMetrics["numberOfCustomURLRules"] = 1

                numberOfCustomAJAXRules = 0
                analysisDataEvaluatedMetrics["numberOfCustomAJAXRules"] = 0
                if "numberOfCustomAJAXIncludeRules" in NetworkRequestsBRUM_RAW and "numberOfCustomAJAXExcludeRules" in NetworkRequestsBRUM_RAW:
                    if (NetworkRequestsBRUM_RAW["numberOfCustomAJAXIncludeRules"] + NetworkRequestsBRUM_RAW["numberOfCustomAJAXExcludeRules"]) > 1:
                        analysisDataEvaluatedMetrics["numberOfCustomAJAXRules"] = 1

                numberOfCustomAJAXEventRules = 0
                analysisDataEvaluatedMetrics["numberOfCustomAJAXEventRules"] = 0
                if "numberOfCustomAJAXEventIncludeRules" in NetworkRequestsBRUM_RAW and "numberOfCustomAJAXEventExcludeRules" in NetworkRequestsBRUM_RAW:
                    if (NetworkRequestsBRUM_RAW["numberOfCustomAJAXEventIncludeRules"] + NetworkRequestsBRUM_RAW["numberOfCustomAJAXEventExcludeRules"]) > 0:
                        analysisDataEvaluatedMetrics["numberOfCustomAJAXEventRules"] = 1

                numberOfCustomPageRules = 0
                analysisDataEvaluatedMetrics["numberOfCustomPageRules"] = 0
                if "numberOfCustomPageIncludeRules" in NetworkRequestsBRUM_RAW and "numberOfCustomPageExcludeRules" in NetworkRequestsBRUM_RAW:
                    if (NetworkRequestsBRUM_RAW["numberOfCustomPageIncludeRules"] + NetworkRequestsBRUM_RAW["numberOfCustomPageExcludeRules"]) > 1:
                        analysisDataEvaluatedMetrics["numberOfCustomPageRules"] = 1

                numberOfCustomVirtualPageRules = 0
                analysisDataEvaluatedMetrics["numberOfCustomVirtualPageRules"] = 0
                if "numberOfCustomVirtualIncludeRules" in NetworkRequestsBRUM_RAW and "numberOfCustomVirtualExcludeRules" in NetworkRequestsBRUM_RAW:
                    if (NetworkRequestsBRUM_RAW["numberOfCustomVirtualIncludeRules"] + NetworkRequestsBRUM_RAW["numberOfCustomVirtualExcludeRules"]) > 1:
                        analysisDataEvaluatedMetrics["numberOfCustomVirtualPageRules"] = 1

                # Generate scorecard pass/fail for any include rules.
                nonDefaultIncludeRule = 0
                if "nonDefaultIncludeRule" in NetworkRequestsBRUM_RAW:
                    nonDefaultIncludeRule = NetworkRequestsBRUM_RAW["nonDefaultIncludeRule"]
                if nonDefaultIncludeRule == 0:
                    analysisDataEvaluatedMetrics["nonDefaultIncludeRule"] = 0
                else:
                    analysisDataEvaluatedMetrics["nonDefaultIncludeRule"] = 1

                #Generate scorecared pass/fail for non-default thresholds
                if NetworkRequestsBRUM_RAW["thresholdModified"]:
                    analysisDataEvaluatedMetrics["thresholdModified"] = 1
                else:
                    analysisDataEvaluatedMetrics["thresholdModified"] = 0

                # WellsFargo HealthRuleScore check
                HealthRulesAndAlertingBRUM_RAW = application["HealthRulesAndAlertingBRUM"]["raw"]

                analysisDataEvaluatedMetrics["HealthRuleScore"] = 0
                if HealthRulesAndAlertingBRUM_RAW['NumberOfHealthRules'] == 0 and HealthRulesAndAlertingBRUM_RAW["NumberOfActivePoliciesWithBigPandaAction"] == 0:
                    analysisDataEvaluatedMetrics["HealthRuleScore"] = 0
                if HealthRulesAndAlertingBRUM_RAW['NumberOfHealthRules'] > 0 and HealthRulesAndAlertingBRUM_RAW["NumberOfHealthRulesWithPandaAction"] > 0:
                    analysisDataEvaluatedMetrics["HealthRuleScore"] = 1

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
