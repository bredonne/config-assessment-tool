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

                # WellsFargo BASEMONHealthRuleScore check
                HealthRulesAndAlertingAPM_RAW = application["HealthRulesAndAlertingAPM"]["raw"]
                analysisDataEvaluatedMetrics["BASEMONHealthRuleScore"] = 0
                if HealthRulesAndAlertingAPM_RAW['NumberOfBasemonHealthRules'] == 0 and HealthRulesAndAlertingAPM_RAW["NumberOfActivePoliciesWithBigPandaAction"] == 0 and HealthRulesAndAlertingAPM_RAW["numberOfCustomHealthRules"] == 0:
                    analysisDataEvaluatedMetrics["BASEMONHealthRuleScore"] = 0
                if 1 <= HealthRulesAndAlertingAPM_RAW['NumberOfBasemonHealthRules'] <= 7 and HealthRulesAndAlertingAPM_RAW["NumberOfBasemonHealthRulesWithPandaAction"] >= 1:
                    analysisDataEvaluatedMetrics["BASEMONHealthRuleScore"] = 1
                if HealthRulesAndAlertingAPM_RAW['NumberOfBasemonHealthRules'] >= 7 and HealthRulesAndAlertingAPM_RAW["numberOfCustomHealthRules"] >= 1:
                    analysisDataEvaluatedMetrics["BASEMONHealthRuleScore"] = 2
                if HealthRulesAndAlertingAPM_RAW['NumberOfBasemonHealthRules'] >= 7 and HealthRulesAndAlertingAPM_RAW["NumberOfBasemonHealthRulesWithPandaAction"] >= 1 and HealthRulesAndAlertingAPM_RAW["numberOfCustomHealthRules"] >= 1:
                    analysisDataEvaluatedMetrics["BASEMONHealthRuleScore"] = 3

                # WellsFargo BTRuleScore check
                BusinessTransactionsAPM_RAW = application["BusinessTransactionsAPM"]["raw"]
                analysisDataEvaluatedMetrics["BTScore"] = 0
                if BusinessTransactionsAPM_RAW["numberCustomMatchRules"] == 0 and not BusinessTransactionsAPM_RAW["btLockdownEnabled"] and not BusinessTransactionsAPM_RAW["numberOfRulesWithNonZeroPriority"] >> 0:
                    analysisDataEvaluatedMetrics["BTScore"] = 0
                if BusinessTransactionsAPM_RAW["numberCustomMatchRules"] == 0 and BusinessTransactionsAPM_RAW["btLockdownEnabled"]:
                    analysisDataEvaluatedMetrics["BTScore"] = 1
                if (BusinessTransactionsAPM_RAW["numberCustomMatchRules"] >> 0 or BusinessTransactionsAPM_RAW["btLockdownEnabled"]) and BusinessTransactionsAPM_RAW["numberOfRulesWithNonZeroPriority"] >> 0:
                    analysisDataEvaluatedMetrics["BTScore"] = 2
                if BusinessTransactionsAPM_RAW["btLockdownEnabled"] and (BusinessTransactionsAPM_RAW["numberCustomMatchRules"] >> 0 or BusinessTransactionsAPM_RAW["numberOfRulesWithNonZeroPriority"] >> 0) and BusinessTransactionsAPM_RAW["businessTransactionsWithLoad"] << 200:
                    analysisDataEvaluatedMetrics["BTScore"] = 3

                # WellsFargo Backend check
                BackendsAPM_RAW = application["BackendsAPM"]["raw"]
                ServiceEndpointsAPM_RAW = application["ServiceEndpointsAPM"]["raw"]
                analysisDataEvaluatedMetrics["BackendScore"] = 0
                if BackendsAPM_RAW["numberOfModifiedDefaultBackendDiscoveryConfigs"] == 0 and BackendsAPM_RAW["numberOfCustomExitPoints"] == 0 and ServiceEndpointsAPM_RAW['numberOfCustomServiceEndpointRules'] == 0 :
                    analysisDataEvaluatedMetrics["BackendScore"] = 0
                if (BackendsAPM_RAW["numberOfModifiedDefaultBackendDiscoveryConfigs"] >= 1 or BackendsAPM_RAW["numberOfCustomExitPoints"] >= 1)  and ServiceEndpointsAPM_RAW['numberOfCustomServiceEndpointRules'] >= 1 :
                    analysisDataEvaluatedMetrics["BackendScore"] = 1
                if (BackendsAPM_RAW["numberOfModifiedDefaultBackendDiscoveryConfigs"] >= 1 or BackendsAPM_RAW["numberOfCustomExitPoints"] >= 1) and ServiceEndpointsAPM_RAW['numberOfCustomServiceEndpointRules'] >= 1 and BackendsAPM_RAW["numberOfDBBackendsWithLoad"] >= 1:
                    analysisDataEvaluatedMetrics["BackendScore"] = 2
                if (BackendsAPM_RAW["numberOfModifiedDefaultBackendDiscoveryConfigs"] >= 1 or BackendsAPM_RAW["numberOfCustomExitPoints"] >= 1) and ServiceEndpointsAPM_RAW['numberOfCustomServiceEndpointRules'] >= 1 and BackendsAPM_RAW["numberOfDBBackendsWithLoad"] >= 1 and (HealthRulesAndAlertingAPM_RAW['numberOfBackendHealthRulesInPoliciesWithPandaAction'] >= 1 or HealthRulesAndAlertingAPM_RAW['numberOfSEHealthRulesInPoliciesWithPandaAction'] >= 1):
                    analysisDataEvaluatedMetrics["BackendScore"] = 3

                # WellsFargo JMX check
                kafkaRule = False
                log4j2Rule = False
                NIORule = False

                jmxConfigs = application["jmxConfigs"]
                JMXAPM_RAW = application["JMXAPM"]["raw"]

                for config in application["jmxConfigs"]:
                    if "Kafka Updated" in str(config["name"]):
                        kafkaRule = True
                    if "Log4j2" in str(config["name"]):
                        log4j2Rule = True
                    if "Java NIO Direct BufferPool" in str(config["name"]):
                        NIORule = True

                analysisDataEvaluatedMetrics["JMXScore"] = 0

                if not kafkaRule and not log4j2Rule and not NIORule:
                    analysisDataEvaluatedMetrics["JMXScore"] = 0
                if (not kafkaRule and not log4j2Rule and not NIORule) and JMXAPM_RAW["numberOfModifiedJMXConfigs"] >=1 :
                    analysisDataEvaluatedMetrics["JMXScore"] = 1
                if kafkaRule or log4j2Rule or NIORule:
                    analysisDataEvaluatedMetrics["JMXScore"] = 2
                if kafkaRule and log4j2Rule and NIORule:
                    analysisDataEvaluatedMetrics["JMXScore"] = 3

                #Dashboard Check
                DashboardsAPM_RAW = application["DashboardsAPM"]["raw"]
                analysisDataEvaluatedMetrics["DashboardScore"] = 0
                if DashboardsAPM_RAW["numberOfDashboards"] == 0:
                    analysisDataEvaluatedMetrics["DashboardScore"] = 0
                if DashboardsAPM_RAW["numberOfDashboards"] == 1:
                    analysisDataEvaluatedMetrics["DashboardScore"] = 1
                if DashboardsAPM_RAW["numberOfDashboards"] == 2:
                    analysisDataEvaluatedMetrics["DashboardScore"] = 2
                if DashboardsAPM_RAW["numberOfDashboards"] >= 3:
                    analysisDataEvaluatedMetrics["DashboardScore"] = 3

                #MIDC Check
                MIDCAPM_EVALUATED = application["DataCollectorsAPM"]["evaluated"]
                analysisDataEvaluatedMetrics["MIDCScore"] = 0
                if len(MIDCAPM_EVALUATED["numberOfDataCollectorFieldsConfigured"]) == 0:
                    analysisDataEvaluatedMetrics["MIDCScore"] = 0
                if len(MIDCAPM_EVALUATED["numberOfDataCollectorFieldsConfigured"]) >= 3:
                    analysisDataEvaluatedMetrics["MIDCScore"] = 3

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
