import json
import logging
from collections import OrderedDict

from api.appd.AppDService import AppDService
from deepdiff import DeepDiff
from extractionSteps.JobStepBase import JobStepBase
from util.asyncio_utils import AsyncioUtils


class HealthRulesAndAlertingAPM_WF(JobStepBase):
    def __init__(self):
        super().__init__("apm")

    async def extract(self, controllerData):
        """
        Extract health rule and alerting configuration details.
        1. Makes one API call per application to get Health Rules.
        2. Makes one API call per application to get Event Counts (health rule violations).
        3. Makes one API call per application to get Policies.
        """
        jobStepName = type(self).__name__

        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Extracting {jobStepName}')
            controller: AppDService = hostInfo["controller"]

            # Gather necessary metrics.
            getHealthRulesFutures = []
            getEventCountsFutures = []
            getPoliciesFutures = []
            for application in hostInfo[self.componentType].values():
                getEventCountsFutures.append(
                    controller.getEventCounts(
                        applicationID=application["id"],
                        entityType="APPLICATION",
                        entityID=application["id"],
                    )
                )
                getHealthRulesFutures.append(controller.getHealthRules(application["id"]))
                getPoliciesFutures.append(controller.getPolicies(application["id"]))

            eventCounts = await AsyncioUtils.gatherWithConcurrency(*getEventCountsFutures)
            healthRules = await AsyncioUtils.gatherWithConcurrency(*getHealthRulesFutures)
            policies = await AsyncioUtils.gatherWithConcurrency(*getPoliciesFutures)

            for idx, applicationName in enumerate(hostInfo[self.componentType]):
                application = hostInfo[self.componentType][applicationName]

                application["eventCounts"] = eventCounts[idx].data
#                application["policies"] = policies[idx].data

                trimmedHrs = [healthRule for healthRule in healthRules[idx].data if healthRule.error is None]
                application["healthRules"] = {
                    healthRuleList.data["name"]: healthRuleList.data for healthRuleList in trimmedHrs if healthRuleList.error is None
                }
                trimmedPos = [policy for policy in policies[idx].data if policy.error is None]
                application["policies"] = {
                    policyList.data["name"]: policyList.data for policyList in trimmedPos if policyList.error is None
                }

    def analyze(self, controllerData, thresholds):
        """
        Analysis of error configuration details.
        1. Determines number of Health Rule violations.
        2. Determines number of Default Health Rules modified.
        3. Determines number of Actions currently bound to enabled policies.
        4. Determines number of Custom Health Rules.
        """

        jobStepName = type(self).__name__

        # Get thresholds related to job
        jobStepThresholds = thresholds[self.componentType][jobStepName]

        defaultHealthRules = json.loads(open("backend/resources/controllerDefaults/defaultHealthRulesAPM.json").read())
        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Analyzing {jobStepName}')

            for application in hostInfo[self.componentType].values():
                # Root node of current application for current JobStep.
                analysisDataRoot = application[jobStepName] = OrderedDict()
                # This data goes into the 'JobStep - Metrics' xlsx sheet.
                analysisDataEvaluatedMetrics = analysisDataRoot["evaluated"] = OrderedDict()
                # This data goes into the 'JobStep - Raw' xlsx sheet.
                analysisDataRawMetrics = analysisDataRoot["raw"] = OrderedDict()

                # numberOfHealthRuleViolations
                policyEventCounts = application["eventCounts"]["policyViolationEventCounts"]["totalPolicyViolations"]
                analysisDataEvaluatedMetrics["numberOfHealthRuleViolations"] = policyEventCounts["warning"] + policyEventCounts["critical"]


                NumberOfActivePolicies = 0
                NumberOfActivePoliciesWithAllHealthRuleScope = 0
                PoliciesWithBigPandaAction = 0
                SEHealthRules = 0
                SEHealthRulesWithPolicy = 0
                SEHealthRulesWithPolicyPandaAction = 0
                JMXHealthRules = 0
                JMXHealthRulesWithPolicy = 0
                BackendHealthRules = 0
                BackendHealthRulesWithPolicy = 0
                BackendHealthRulesWithPolicyPandaAction = 0

                for healthrule, healthruleinfo in application["healthRules"].items():
                    if healthruleinfo["affects"]["affectedEntityType"] in ["SERVICE_ENDPOINTS"]:
                        SEHealthRules += 1
                        # Check if HR is specified in a policy.
                        for idx, policy in application["policies"].items():
                            try:
                                if policy["enabled"] and policy["events"]["healthRuleEvents"] is not None and "healthRules" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:  # Better type checking for when a policy does not act on HR's but other checkboxes
                                    if policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"] is not None:
                                        if healthrule in policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"]:
                                            SEHealthRulesWithPolicy += 1
                                            if "actions" in policy:  #Check for Panda Action
                                                for action in policy["actions"]:
                                                    if "BigPanda" in str(action["actionName"]):
                                                        SEHealthRulesWithPolicyPandaAction += 1
                            except (KeyError, TypeError, IndexError):
                                print("Couldn't find a match for the key:")

                    if healthruleinfo["affects"]["affectedEntityType"] in ["JMX_AFFECTED_EMC"]:
                        JMXHealthRules += 1
                        # Check if HR is specified in a policy.
                        for idx, policy in application["policies"].items():
                            try:
                                if policy["enabled"] and policy["events"]["healthRuleEvents"] is not None and "healthRules" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:  # Better type checking for when a policy does not act on HR's but other checkboxes
                                # if policy["enabled"] and "healthRules" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:
                                    if policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"] is not None:
                                        if healthrule in policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"]:
                                            JMXHealthRulesWithPolicy += 1
                            except (KeyError, TypeError, IndexError):
                                print("Couldn't find a match for the key:")

                    if healthruleinfo["affects"]["affectedEntityType"] in ["BACKENDS"]:
                        BackendHealthRules += 1
                        # Check if HR is specified in a policy.
                        for idx, policy in application["policies"].items():
                            try:
                                if policy["enabled"] and policy["events"]["healthRuleEvents"] is not None and "healthRules" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:  #Better type checking for when a policy does not act on HR's but other checkboxes
                                #if policy["enabled"] and "healthRules" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:
                                    if policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"] is not None:
                                        if healthrule in policy["events"]["healthRuleEvents"]["healthRuleScope"]["healthRules"]:
                                            BackendHealthRulesWithPolicy += 1
                                            if "actions" in policy:  #Check for Panda Action
                                                for action in policy["actions"]:
                                                    if "BigPanda" in str(action["actionName"]):
                                                        BackendHealthRulesWithPolicyPandaAction += 1
                            except (KeyError, TypeError, IndexError):
                                print("Couldn't find a match for the key:")

                analysisDataEvaluatedMetrics["numberOfSEHealthRules"] = SEHealthRules
                analysisDataEvaluatedMetrics["numberOfSEHealthRulesInPolicies"] = SEHealthRulesWithPolicy

                #Number of active policies going to BigPanda
                BigPanda_actionsInEnabledPolicies = set()
                for idx, policy in application["policies"].items():
                    if policy["enabled"]:
                        NumberOfActivePolicies += 1
                        if policy["events"]["healthRuleEvents"] is not None and "All_HEALTH_RULES" in policy["events"]["healthRuleEvents"]["healthRuleScope"]:
                            NumberOfActivePoliciesWithAllHealthRuleScope += 1
                        if "actions" in policy:
                            for action in policy["actions"]:
                                if "BigPanda" in str(action["actionName"]):
                                    PoliciesWithBigPandaAction += 1
                                    BigPanda_actionsInEnabledPolicies.add(action["actionName"])
                        else:
                            logging.warning(f"Policy {policy['name']} is enabled but has no actions bound to it.")


                #analysisDataEvaluatedMetrics["numberOfBigPandaActionsBoundToEnabledPolicies"] = len(BigPanda_actionsInEnabledPolicies)
                analysisDataEvaluatedMetrics["numberOfBigPandaActionsBoundToEnabledPolicies"] = PoliciesWithBigPandaAction

                # numberOfCustomHealthRules
                analysisDataEvaluatedMetrics["numberOfCustomHealthRules"] = len(
                    set(application["healthRules"].keys()).symmetric_difference(defaultHealthRules.keys())
                )

                analysisDataRawMetrics["totalWarningPolicyViolations"] = policyEventCounts["warning"]
                analysisDataRawMetrics["totalCriticalPolicyViolations"] = policyEventCounts["critical"]
                analysisDataRawMetrics["numberOfHealthRules"] = len(application["healthRules"])
                analysisDataRawMetrics["numberOfCustomHealthRules"] = len(set(application["healthRules"].keys()).symmetric_difference(defaultHealthRules.keys()))
                analysisDataRawMetrics["numberOfSEHealthRules"] = SEHealthRules
                analysisDataRawMetrics["numberOfSEHealthRulesInPolicies"] = SEHealthRulesWithPolicy
                analysisDataRawMetrics["numberOfSEHealthRulesInPoliciesWithPandaAction"] = SEHealthRulesWithPolicyPandaAction
                analysisDataRawMetrics["numberOfBackendHealthRules"] = BackendHealthRules
                analysisDataRawMetrics["numberOfBackendHealthRulesInPolicies"] = BackendHealthRulesWithPolicy
                analysisDataRawMetrics["numberOfBackendHealthRulesInPoliciesWithPandaAction"] =BackendHealthRulesWithPolicyPandaAction
#                analysisDataRawMetrics["numberOfJMXHealthRules"] = JMXHealthRules
#                analysisDataRawMetrics["numberOfJMXHealthRulesInPolicies"] = JMXHealthRulesWithPolicy
                analysisDataRawMetrics["numberOfPolicies"] = len(application["policies"])
                analysisDataRawMetrics["numberOfActivePolicies"] = NumberOfActivePolicies
                analysisDataRawMetrics["numberOfActivePoliciesWithAllHealthRuleScope"]= NumberOfActivePoliciesWithAllHealthRuleScope
                analysisDataRawMetrics["numberOfActiveBigPandaPolicies"] = PoliciesWithBigPandaAction


                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
