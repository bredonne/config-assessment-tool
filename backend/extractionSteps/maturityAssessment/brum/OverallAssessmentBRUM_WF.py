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

        jobStepNames = ["NetworkRequestsBRUM", "HealthRulesAndAlertingBRUM", "DashboardsBRUM"]

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

                # numberOfDashboards
                #analysisDataEvaluatedMetrics["numberOfDashboards"] = len(application["brumDashboards"]) + len(application["biqDashboards"])
                analysisDataRawMetrics["numberOfDashboards"] = len(application["brumDashboards"]) + len(application["biqDashboards"])
                # numberOfDashboardsUsingBiQ
                #analysisDataEvaluatedMetrics["numberOfDashboardsUsingBiQ"] = len(application["biqDashboards"])
                #analysisDataRawMetrics["brumReports"] = len(application["brumReports"])

                #Check Analytics Metrics for appKey of this BRUM application
                analyticsMetric = 0
                for metric in hostInfo["analyticsMetrics"]:
                    if metric["adqlQueryString"] is not None:
                        if str(application["appKey"]) in metric["adqlQueryString"]:
                            analyticsMetric = + 1

                analysisDataRawMetrics["analyticsMetric"] = analyticsMetric

                analysisDataEvaluatedMetrics["AnalyticsScore"] = 0
                if analyticsMetric == 0:
                    analysisDataEvaluatedMetrics["AnalyticsScore"] = 0
                if analyticsMetric >= 1:
                    analysisDataEvaluatedMetrics["AnalyticsScore"] = 1


                #Dashboard Check
                DashboardsBRUM_RAW = application["DashboardsBRUM"]["raw"]
                analysisDataEvaluatedMetrics["DashboardScore"] = 0
                if DashboardsBRUM_RAW["numberOfDashboards"] == 0:
                    analysisDataEvaluatedMetrics["DashboardScore"] = 0
                if DashboardsBRUM_RAW["numberOfDashboards"] >= 3:
                    analysisDataEvaluatedMetrics["DashboardScore"] = 1

                # Dashboard Reports Check
                dashboardReport = 0
                for dashboard in application["brumDashboards"]:
                    if str(application["name"]) in dashboard["applicationNames"]:
                        for report in hostInfo["exportedReports"]:
                            if report["reportDataIds"] is not None:
                                if dashboard["dashboardId"] in report["reportDataIds"]:
                                    dashboardReport = + 1

                analysisDataRawMetrics["dashboardReports"] = dashboardReport

                analysisDataEvaluatedMetrics["DashboardReportScore"] = 0
                if dashboardReport == 0:
                    analysisDataEvaluatedMetrics["DashboardReportScore"] = 0
                if dashboardReport > 0:
                    analysisDataEvaluatedMetrics["DashboardReportScore"] = 1


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
                thresholdModified = False
                if "STANDARD_DEVIATION" in application["settingsConfig"]["thresholds"]["slowThreshold"]["type"]:
                    if application["settingsConfig"]["thresholds"]["slowThreshold"]["value"] != 3:
                        thresholdModified = True
                else:
                    thresholdModified = True

                if "STANDARD_DEVIATION" in application["settingsConfig"]["thresholds"]["verySlowThreshold"]["type"]:
                    if application["settingsConfig"]["thresholds"]["verySlowThreshold"]["value"] != 4:
                        thresholdModified = True
                else:
                    thresholdModified = True

                if "STATIC_MS" in application["settingsConfig"]["thresholds"]["stallThreshold"]["type"]:
                    if application["settingsConfig"]["thresholds"]["stallThreshold"]["value"] != 45000:
                        thresholdModified = True

                if thresholdModified:
                    analysisDataEvaluatedMetrics["thresholdModified"] = 1
                else:
                    analysisDataEvaluatedMetrics["thresholdModified"] = 0

                # WellsFargo HealthRuleScore check
                # Check for HealthRules having APPD_BASEMON in the name.
                NumberOfHealthRules = 0
                NumberOfHealthRulesWithPolicy = 0
                NumberOfHealthRulesWithPandaAction = 0
                for healthrule, healthruleinfo in application["healthRules"].items():
                    NumberOfHealthRules += 1
                    # Check if HR is specified in a policy.
                    for idx, policy in application["policies"].items():
                        try:
                            if policy["enabled"] and policy["events"]["healthRuleEvents"] is not None:
                                if policy["events"]["healthRuleEvents"]["healthRuleScope"] is not None:
                                    if "All_HEALTH_RULES" in policy["events"]["healthRuleEvents"]["healthRuleScope"]['healthRuleScopeType']:
                                        NumberOfHealthRulesWithPolicy += 1
                                        if "actions" in policy:  # Check for BigPanda Action
                                            for action in policy["actions"]:
                                                if "BigPanda" in str(action["actionName"]):
                                                    NumberOfHealthRulesWithPandaAction += 1
                                    if "healthRules" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:  # Better type checking for when a policy does not act on HR's but other checkboxes
                                        if healthrule in policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"]:
                                            NumberOfHealthRulesWithPolicy += 1
                                            if "actions" in policy:  # Check for BigPanda Action
                                                for action in policy["actions"]:
                                                    if "BigPanda" in str(action["actionName"]):
                                                        NumberOfHealthRulesWithPandaAction += 1
                        except (KeyError, TypeError, IndexError):
                            print("Couldn't find a match for the key:")

                analysisDataRawMetrics["NumberOfHealthRules"] = NumberOfHealthRules
                analysisDataRawMetrics["NumberOfHealthRulesWithPolicy"] = NumberOfHealthRulesWithPolicy
                analysisDataRawMetrics["NumberOfHealthRulesWithPandaAction"] = NumberOfHealthRulesWithPandaAction

                # Number of active policies going to BigPanda
                NumberOfActivePolicies = 0
                NumberOfActivePoliciesWithBigPandaAction = 0
                for idx, policy in application["policies"].items():
                    if policy["enabled"]:
                        NumberOfActivePolicies += 1
                        if "actions" in policy:
                            for action in policy["actions"]:
                                if "BigPanda" in str(action["actionName"]):
                                    NumberOfActivePoliciesWithBigPandaAction += 1
                        else:
                            logging.warning(f"Policy {policy['name']} is enabled but has no actions bound to it.")

                analysisDataRawMetrics["NumberOfActivePoliciesWithBigPandaAction"] = NumberOfActivePoliciesWithBigPandaAction
                analysisDataRawMetrics["numberOfHealthRules"] = len(application["healthRules"])


                analysisDataEvaluatedMetrics["HealthRuleScore"] = 0
                if NumberOfHealthRules == 0 and NumberOfActivePoliciesWithBigPandaAction == 0:
                    analysisDataEvaluatedMetrics["HealthRuleScore"] = 0
                if NumberOfHealthRules > 0 and NumberOfHealthRulesWithPandaAction > 0:
                    analysisDataEvaluatedMetrics["HealthRuleScore"] = 1

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
