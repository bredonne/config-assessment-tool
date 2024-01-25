import logging
from collections import OrderedDict

from api.appd.AppDService import AppDService
from extractionSteps.JobStepBase import JobStepBase
from util.asyncio_utils import AsyncioUtils



class JMXAPM(JobStepBase):
    def __init__(self):
        super().__init__("apm")

    async def extract(self, controllerData):
        """
        Extract JMX details.
        1. Makes one API call per application to get JMX Metadata.
        """
        jobStepName = type(self).__name__

        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Extracting {jobStepName}')
            controller: AppDService = hostInfo["controller"]

            # Gather necessary metrics.
            getJMXConfigsFutures = []
            for application in hostInfo[self.componentType].values():
                getJMXConfigsFutures.append(controller.getJMXConfig(application["id"]))

            jmxConfigs =  await AsyncioUtils.gatherWithConcurrency(*getJMXConfigsFutures)

            # Append JMX config information
            for idx, application in enumerate(hostInfo[self.componentType]):
                hostInfo[self.componentType][application]["jmxConfigs"] = jmxConfigs[idx].data

    def analyze(self, controllerData, thresholds):
        """
        Analysis of JMX details.
        1. Determines number of JMX configurations.
        2. Determines number of modified JMX configurations.
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

                # Get number of modified JMX configurations.
                numberOfModifiedJMXConfigs = 0

                # If parent level details have been modified.
                numberOfModifiedJMXConfigs = len(
                    [config for config in application["jmxConfigs"] if config["version"] != 0]
                )

                # If children attributes have been modified.
                for config in application["jmxConfigs"]:
                    for children in config["children"]:
                        if children["version"] != 0:
                            numberOfModifiedJMXConfigs += 1

                analysisDataEvaluatedMetrics["numberOfJMXConfigs"] = len(application["jmxConfigs"])
                analysisDataEvaluatedMetrics["numberOfModifiedJMXConfigs"] = numberOfModifiedJMXConfigs
                analysisDataRawMetrics["numberOfJMXConfigs"] = len(application["jmxConfigs"])
                analysisDataRawMetrics["numberOfModifiedJMXConfigs"] = numberOfModifiedJMXConfigs

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
