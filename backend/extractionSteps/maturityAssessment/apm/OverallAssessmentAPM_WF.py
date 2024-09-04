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
            "JMXAPM",
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

                # Check for HealthRules having APPD_BASEMON in the name.
                NumberOfBasemonHealthRules = 0
                NumberOfBasemonHealthRulesWithPolicy = 0
                NumberOfBasemonHealthRulesWithPandaAction = 0
                for healthrule, healthruleinfo in application["healthRules"].items():
                    if "APPD_BASEMON" in str(healthrule):  # Hardcode rule name for now.
                        NumberOfBasemonHealthRules += 1
                        # Check if HR is specified in a policy.
                        for idx, policy in application["policies"].items():
                            try:
                                if policy["enabled"] and policy["events"]["healthRuleEvents"] is not None:
                                    if policy["events"]["healthRuleEvents"]["healthRuleScope"] is not None:
                                        if "All_HEALTH_RULES" in policy["events"]["healthRuleEvents"]["healthRuleScope"]['healthRuleScopeType']:  # If policy has all HR's, it's a match.
                                            NumberOfBasemonHealthRulesWithPolicy += 1
                                            if "actions" in policy:  # Check for BigPanda Action
                                                for action in policy["actions"]:
                                                    if "BigPanda" in str(action["actionName"]):
                                                        NumberOfBasemonHealthRulesWithPandaAction += 1
                                        if "healthRules" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:  # If policy has individual HR's, check if this HR in that list.
                                            if healthrule in policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"]:
                                                NumberOfBasemonHealthRulesWithPolicy += 1
                                                if "actions" in policy:  # Check for BigPanda Action
                                                    for action in policy["actions"]:
                                                        if "BigPanda" in str(action["actionName"]):
                                                            NumberOfBasemonHealthRulesWithPandaAction += 1
                            except (KeyError, TypeError, IndexError):
                                print("Couldn't find a match for the key:")

                analysisDataRawMetrics["NumberOfBasemonHealthRules"] = NumberOfBasemonHealthRules
                analysisDataRawMetrics["NumberOfBasemonHealthRulesWithPolicy"] = NumberOfBasemonHealthRulesWithPolicy
                analysisDataRawMetrics["NumberOfBasemonHealthRulesWithPandaAction"] = NumberOfBasemonHealthRulesWithPandaAction

                #Number of active policies going to BigPanda
                NumberOfActivePolicies = 0
                NumberOfActiveBasemonPolicies = 0
                NumberOfActivePoliciesWithAllHealthRuleScope = 0
                NumberOfActivePoliciesWithBigPandaAction = 0
                BigPanda_actionsInEnabledPolicies = set()
                for idx, policy in application["policies"].items():
                    if policy["enabled"]:
                        NumberOfActivePolicies += 1
                        if "APPD_BASEMON" in str(policy):  # Hardcode Policy name for now.
                            NumberOfActiveBasemonPolicies += 1
                        if policy["events"]["healthRuleEvents"] is not None and "All_HEALTH_RULES" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:
                            NumberOfActivePoliciesWithAllHealthRuleScope += 1
                        if "actions" in policy:
                            for action in policy["actions"]:
                                if "BigPanda" in str(action["actionName"]):
                                    NumberOfActivePoliciesWithBigPandaAction += 1
                                    BigPanda_actionsInEnabledPolicies.add(action["actionName"])
                        else:
                            logging.warning(f"Policy {policy['name']} is enabled but has no actions bound to it.")

                analysisDataRawMetrics["NumberOfActivePoliciesWithBigPandaAction"] = NumberOfActivePoliciesWithBigPandaAction
                analysisDataRawMetrics["NumberOfActiveBasemonPolicies"] = NumberOfActiveBasemonPolicies

                # WellsFargo BASEMONHealthRuleScore check
                HealthRulesAndAlertingAPM_RAW = application["HealthRulesAndAlertingAPM"]["raw"]
                analysisDataEvaluatedMetrics["BASEMONHealthRuleScore"] = 0
                if NumberOfBasemonHealthRules == 0 and NumberOfActivePoliciesWithBigPandaAction == 0 and HealthRulesAndAlertingAPM_RAW["numberOfCustomHealthRules"] == 0:
                    analysisDataEvaluatedMetrics["BASEMONHealthRuleScore"] = 0
                #Gary 4.24.24 req.  Pass score if 4 or more basemon HRs with any panda action
                if NumberOfBasemonHealthRules >= 4 and NumberOfActivePoliciesWithBigPandaAction >= 1 and HealthRulesAndAlertingAPM_RAW["numberOfCustomHealthRules"] >= 1:
                    analysisDataEvaluatedMetrics["BASEMONHealthRuleScore"] = 1


                # WellsFargo BTRuleScore check
                BusinessTransactionsAPM_RAW = application["BusinessTransactionsAPM"]["raw"]
                analysisDataEvaluatedMetrics["BTScore"] = 0
                if BusinessTransactionsAPM_RAW["numberCustomMatchRules"] == 0 and not BusinessTransactionsAPM_RAW["btLockdownEnabled"] and not BusinessTransactionsAPM_RAW["numberOfRulesWithNonZeroPriority"] >> 0:
                    analysisDataEvaluatedMetrics["BTScore"] = 0
                if BusinessTransactionsAPM_RAW["btLockdownEnabled"] and (BusinessTransactionsAPM_RAW["numberCustomMatchRules"] > 0 or BusinessTransactionsAPM_RAW["numberOfRulesWithNonZeroPriority"] > 0) and BusinessTransactionsAPM_RAW["businessTransactionsWithLoad"] < 200:
                    analysisDataEvaluatedMetrics["BTScore"] = 1


                #ServiceEndpoint Rule Check
                SEHealthRules = 0
                SEHealthRulesWithPolicy = 0
                SEHealthRulesWithPolicyPandaAction = 0
                for healthrule, healthruleinfo in application["healthRules"].items():
                    if healthruleinfo["affects"]["affectedEntityType"] in ["SERVICE_ENDPOINTS"]:
                        SEHealthRules += 1
                        # Check if HR is specified in a policy.
                        for idx, policy in application["policies"].items():
                            try:
                                if policy["enabled"] and policy["events"]["healthRuleEvents"] is not None:
                                    if policy["events"]["healthRuleEvents"]["healthRuleScope"] is not None:
                                        if "All_HEALTH_RULES" in policy["events"]["healthRuleEvents"]["healthRuleScope"]['healthRuleScopeType']:  # If policy has all HR's, it's a match.
                                            SEHealthRulesWithPolicy += 1
                                            if "actions" in policy:  # Check for BigPanda Action
                                                for action in policy["actions"]:
                                                    if "BigPanda" in str(action["actionName"]):
                                                        SEHealthRulesWithPolicyPandaAction += 1
                                        if "healthRules" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:  # If policy has individual HR's, check if this HR in that list.
                                            if healthrule in policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"]:
                                                SEHealthRulesWithPolicy += 1
                                                if "actions" in policy:  # Check for BigPanda Action
                                                    for action in policy["actions"]:
                                                        if "BigPanda" in str(action["actionName"]):
                                                            SEHealthRulesWithPolicyPandaAction += 1

                            except (KeyError, TypeError, IndexError):
                                print("Couldn't find a match for the key:")

                analysisDataRawMetrics["numberOfSEHealthRules"] = SEHealthRules
                analysisDataRawMetrics["numberOfSEHealthRulesInPolicies"] = SEHealthRulesWithPolicy
                analysisDataRawMetrics["numberOfSEHealthRulesInPoliciesWithPandaAction"] = SEHealthRulesWithPolicyPandaAction

                # Backend Rule Check
                BackendHealthRules = 0
                BackendHealthRulesWithPolicy = 0
                BackendHealthRulesWithPolicyPandaAction = 0
                for healthrule, healthruleinfo in application["healthRules"].items():
                    if healthruleinfo["affects"]["affectedEntityType"] in ["BACKENDS"]:
                        BackendHealthRules += 1
                        # Check if HR is specified in a policy.
                        for idx, policy in application["policies"].items():
                            try:
                                if policy["enabled"] and policy["events"]["healthRuleEvents"] is not None:
                                    if policy["events"]["healthRuleEvents"]["healthRuleScope"] is not None:
                                        if "All_HEALTH_RULES" in policy["events"]["healthRuleEvents"]["healthRuleScope"]['healthRuleScopeType']:  # If policy has all HR's, it's a match.
                                            NumberOfBasemonHealthRulesWithPolicy += 1
                                            if "actions" in policy:  # Check for BigPanda Action
                                                for action in policy["actions"]:
                                                    if "BigPanda" in str(action["actionName"]):
                                                        NumberOfBasemonHealthRulesWithPandaAction += 1
                                        if "healthRules" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:  # If policy has individual HR's, check if this HR in that list.
                                            if healthrule in policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"]:
                                                BackendHealthRulesWithPolicy += 1
                                                if "actions" in policy:  # Check for BigPanda Action
                                                    for action in policy["actions"]:
                                                        if "BigPanda" in str(action["actionName"]):
                                                            BackendHealthRulesWithPolicyPandaAction += 1
                            except (KeyError, TypeError, IndexError):
                                print("Couldn't find a match for the key:")

                analysisDataRawMetrics["numberOfBackendHealthRules"] = BackendHealthRules
                analysisDataRawMetrics["numberOfBackendHealthRulesInPolicies"] = BackendHealthRulesWithPolicy
                analysisDataRawMetrics["numberOfBackendHealthRulesInPoliciesWithPandaAction"] = BackendHealthRulesWithPolicyPandaAction


                # WellsFargo Backend check
                BackendsAPM_RAW = application["BackendsAPM"]["raw"]
                ServiceEndpointsAPM_RAW = application["ServiceEndpointsAPM"]["raw"]
                analysisDataEvaluatedMetrics["BackendScore"] = 0
                if BackendsAPM_RAW["numberOfModifiedDefaultBackendDiscoveryConfigs"] == 0 and BackendsAPM_RAW["numberOfCustomExitPoints"] == 0 and ServiceEndpointsAPM_RAW['numberOfCustomServiceEndpointRules'] == 0 :
                    analysisDataEvaluatedMetrics["BackendScore"] = 0
                if (BackendsAPM_RAW["numberOfModifiedDefaultBackendDiscoveryConfigs"] >= 1 or BackendsAPM_RAW["numberOfCustomExitPoints"] >= 1) and ServiceEndpointsAPM_RAW['numberOfCustomServiceEndpointRules'] >= 1 and BackendsAPM_RAW["numberOfDBBackendsWithLoad"] >= 1 and ( BackendHealthRulesWithPolicyPandaAction >=1  or SEHealthRulesWithPolicyPandaAction >= 1):
                    analysisDataEvaluatedMetrics["BackendScore"] = 1
                if (BackendsAPM_RAW["numberOfModifiedDefaultBackendDiscoveryConfigs"] >= 1 or BackendsAPM_RAW["numberOfCustomExitPoints"] >= 1):  # Gary req. 4.24.24
                    analysisDataEvaluatedMetrics["BackendScore"] = 1


                # DBCollectorScore check.  In DB's calls are showing but are unmapped.
                analysisDataEvaluatedMetrics["DBCollectorScore"] = 0
                if BackendsAPM_RAW["UnMappedDBBackends"] == 0:
                    analysisDataEvaluatedMetrics["DBCollectorScore"] = 1

                # WellsFargo JMX check
                kafkaRule = False
                log4j2Rule = False
                NIORule = False

                for config in application["jmxConfigs"]:
                    if "Kafka Updated" in str(config["name"]):
                        kafkaRule = True
                    if "Log4j2" in str(config["name"]):
                        log4j2Rule = True
                    if "Java NIO Direct BufferPool" in str(config["name"]):
                        NIORule = True

                analysisDataEvaluatedMetrics["JMXScore"] = 0
                if kafkaRule and log4j2Rule and NIORule:
                    analysisDataEvaluatedMetrics["JMXScore"] = 1

                analyticsMetric = 0
                for metric in hostInfo["analyticsMetrics"]:
                    if metric["adqlQueryString"] is not None:
                        if str(application["name"]) in metric["adqlQueryString"]:
                            analyticsMetric = + 1

                analysisDataRawMetrics["analyticsMetric"] = analyticsMetric

                analysisDataEvaluatedMetrics["AnalyticsScore"] = 0
                if analyticsMetric >= 1:
                    analysisDataEvaluatedMetrics["AnalyticsScore"] = 1


                #Dashboard Check    OLD...Original code that matches full appname used in dashboard widget.

                #DashboardsAPM_RAW = application["DashboardsAPM"]["raw"]
                #analysisDataEvaluatedMetrics["DashboardScore"] = 0
                #if DashboardsAPM_RAW["numberOfDashboards"] == 0:
                #    analysisDataEvaluatedMetrics["DashboardScore"] = 0
                #if DashboardsAPM_RAW["numberOfDashboards"] >= 3:
                #    analysisDataEvaluatedMetrics["DashboardScore"] = 1

                # Dashboard Name Prefix check.  (New Gary req. 04.24.24  Pass if have more than 3 dashboards starting with first 4 of app name. )
                dashboardPrefixMatch = 0
                for dashboard in hostInfo["exportedDashboards"]:
                    if str(application["name"]).startswith(dashboard["name"][0:4]):
                        dashboardPrefixMatch = + 1

                analysisDataRawMetrics["dashboardReports"] = dashboardPrefixMatch
                analysisDataEvaluatedMetrics["DashboardScore"] = 0
                if dashboardPrefixMatch >= 3:
                    analysisDataEvaluatedMetrics["DashboardScore"] = 1

                # Dashboard Reports Check
                dashboardReports = 0
                for dashboard in application["apmDashboards"]:
                    if str(application["name"]) in dashboard["applicationNames"]:
                        for report in hostInfo["exportedReports"]:
                            if report["reportDataIds"] is not None:
                                if dashboard["dashboardId"] in report["reportDataIds"]:
                                    dashboardReports = + 1

                analysisDataRawMetrics["dashboardReports"] = dashboardReports

                #DashboardReport Check
                analysisDataEvaluatedMetrics["DashboardReportScore"] = 0
                if dashboardReports >= 1:
                    analysisDataEvaluatedMetrics["DashboardReportScore"] = 1

                #MIDC Check
                MIDCAPM_EVALUATED = application["DataCollectorsAPM"]["evaluated"]
                analysisDataEvaluatedMetrics["MIDCScore"] = 0
                if len(MIDCAPM_EVALUATED["numberOfDataCollectorFieldsConfigured"]) >= 1:
                    analysisDataEvaluatedMetrics["MIDCScore"] = 1

                #Error Detection Check
                ErrorConfigurationAPM_RAW = application["ErrorConfigurationAPM"]["raw"]
                analysisDataEvaluatedMetrics["ErrorDetectScore"] = 0
                if ErrorConfigurationAPM_RAW["numberOfCustomRules"] >= 1:
                    analysisDataEvaluatedMetrics["ErrorDetectScore"] = 1

                #Anomaly Detection Check
                analysisDataEvaluatedMetrics["AnomalyDetectionScore"] = 0
                analysisDataRawMetrics["AnomalyDetectionEnabled"] = 0
                anomalyDetectionEnabled = False
                anomalyWithBigPandaAction = False
                if "enabled" in application["anomalies"]:
                    analysisDataRawMetrics["AnomalyDetectionEnabled"] = 1
                    anomalyDetectionEnabled = True
                    for idx, policy in application["policies"].items():
                        try:
                            if policy["enabled"] and policy["events"]["anomalyEvents"] is not None :
                                if "actions" in policy:  # Check for Panda Action
                                    for action in policy["actions"]:
                                        if "BigPanda" in str(action["actionName"]):
                                            anomalyWithBigPandaAction = True
                        except (KeyError, TypeError, IndexError):
                            print("Couldn't find a match for the key:")


                if anomalyDetectionEnabled and anomalyWithBigPandaAction:
                    analysisDataEvaluatedMetrics["AnomalyDetectionScore"] = 1

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
