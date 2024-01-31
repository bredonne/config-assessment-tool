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
                sessionTimeoutMin = 0
                if "sessionTimeoutMin" in NetworkRequestsBRUM_RAW:
                    sessionTimeoutMin = NetworkRequestsBRUM_RAW["sessionTimeoutMin"]

                analysisDataEvaluatedMetrics["sessionTimeoutMin"] = sessionTimeoutMin

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
