import logging
from collections import OrderedDict

from api.appd.AppDService import AppDService
from extractionSteps.JobStepBase import JobStepBase
from util.asyncio_utils import AsyncioUtils
from util.stdlib_utils import substringBetween


class BackendsAPM(JobStepBase):
    def __init__(self):
        super().__init__("apm")

    async def extract(self, controllerData):
        """
        Extract backend details.
        1. Makes one API call per application to get Backend Metadata.
        2. Makes one API call per application to get Backend Custom Exit Points.
        3. Makes one API call per application to get Backend Discovery Configurations.
        4. Makes one API call per application to get Backend Calls Per Minute.
        """
        jobStepName = type(self).__name__

        backendNameToCallsPerMinuteMap = {}
        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Extracting {jobStepName}')
            controller: AppDService = hostInfo["controller"]

            # Gather necessary metrics.
            getBackendsFutures = []
            getBackendsDBCollectorFutures = []
            getAllCustomExitPointsFutures = []
            getBackendDiscoveryConfigsFutures = []
            backendCallsPerMinuteFutures = []
            for application in hostInfo[self.componentType].values():
                getBackendsFutures.append(controller.getBackends(application["id"]))
                getBackendsDBCollectorFutures.append(controller.getApplicationDBCollectorStatus(application["id"])) 
                getAllCustomExitPointsFutures.append(controller.getAllCustomExitPoints(application["id"]))
                getBackendDiscoveryConfigsFutures.append(controller.getBackendDiscoveryConfigs(application["id"]))
                backendCallsPerMinuteFutures.append(
                    controller.getMetricData(
                        applicationID=application["id"],
                        metric_path="Backends|*|Calls per Minute",
                        rollup=True,
                        time_range_type="BEFORE_NOW",
                        duration_in_mins=controller.timeRangeMins,
                    )
                )

            backends = await AsyncioUtils.gatherWithConcurrency(*getBackendsFutures)
            backendsDBCollectors = await AsyncioUtils.gatherWithConcurrency(*getBackendsDBCollectorFutures)
            allCustomExitPoints = await AsyncioUtils.gatherWithConcurrency(*getAllCustomExitPointsFutures)
            backendDiscoveryConfigs = await AsyncioUtils.gatherWithConcurrency(*getBackendDiscoveryConfigsFutures)
            backendCallsPerMinute = await AsyncioUtils.gatherWithConcurrency(*backendCallsPerMinuteFutures)

            # Create a dictionary of Node -> Calls Per Minute for fast lookup
            for rolledUpMetrics in backendCallsPerMinute:
                if rolledUpMetrics.error is not None:  # call to gather metrics failed for some reason (most likely 504)
                    continue
                for backendMetric in rolledUpMetrics.data:
                    try:
                        # e.g. 'Backends|Discovered backend call - foo|Calls per Minute'
                        backendName = substringBetween(
                            backendMetric["metricPath"],
                            left="Discovered backend call - ",
                            right="|",
                        )
                        backendCallsPerMinuteMetric = backendMetric["metricValues"][0]["sum"]
                    except IndexError:
                        backendName = ""
                        backendCallsPerMinuteMetric = 0
                    backendNameToCallsPerMinuteMap[backendName] = backendCallsPerMinuteMetric

            # Append node level information to overall host info
            for idx, application in enumerate(hostInfo[self.componentType]):
                hostInfo[self.componentType][application]["backends"] = backends[idx].data
                hostInfo[self.componentType][application]["potentialDBCollectors"] = backendsDBCollectors[idx].data["data"]
                hostInfo[self.componentType][application]["allCustomExitPoints"] = allCustomExitPoints[idx].data
                hostInfo[self.componentType][application]["backendDiscoveryConfigs"] = backendDiscoveryConfigs[idx].data
                for backend in backends[idx].data:
                    try:
                        backend["callsPerMinute"] = backendNameToCallsPerMinuteMap[backend["name"]]
                    except KeyError:
                        backend["callsPerMinute"] = 0
                        logging.debug(f'{hostInfo["controller"].host} - Node: {backend["name"]} returned no metric data for Agent Availability.')               
                """
                numberOfPotentialDBCollectors = 0
                for potentialDBCollector in backendsDBCollectors[idx].data["data"]:
                    try:
                        # Correct/more efficient method would be to cross reference the ids from backendsDBCollectors + backends and grab the Vendor value from backends to check for oracle or mssql
                        databases = ["oracle", "mssql"]
                        if any([x in potentialDBCollector["name"].lower() for x in databases]) or "ADO.NET" in potentialDBCollector["exitPointSubtype"]:
                            print('Found Oracle or MS SQL!')
                            if "UNMAPPED" in potentialDBCollector["dbBackendStatus"]:
                                print(f'Needs DB Collector!')
                                numberOfPotentialDBCollectors += 1
                                print(numberOfPotentialDBCollectors)
                        hostInfo[self.componentType][application]["numberOfPotentialDBCollectors"] = numberOfPotentialDBCollectors
                    except KeyError:
                        logging.debug(f'{hostInfo["controller"].host} - Node: {backend["name"]} returned no backend.')
                """

    def analyze(self, controllerData, thresholds):
        """
        Analysis of node level details.
        1. Determines number of Backends reporting data.
        2. Determines if backend limits are being reached.
        3. Determines number of custom Backend Discovery rules are in place.
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

                # callsPerMinute
                numberOfBackendsWithLoad = 0.0
                numberOfDBBackendsWithLoad = 0
                for backend in application["backends"]:
                    if backend["callsPerMinute"] > 0:
                        numberOfBackendsWithLoad += 1
                        if "JDBC" in str(backend["exitPointType"]):
                            numberOfDBBackendsWithLoad +=1

                # percentBackendsWithLoad
                if numberOfBackendsWithLoad != 0.0:
                    analysisDataEvaluatedMetrics["percentBackendsWithLoad"] = numberOfBackendsWithLoad / len(application["backends"]) * 100
                else:
                    analysisDataEvaluatedMetrics["percentBackendsWithLoad"] = 0

                # potentialDBCollectors
                numberOfPotentialDBCollectors = 0
                for potentialDBCollector in application["potentialDBCollectors"]:
                    try:
                        # Correct/more efficient method would be to cross reference the ids from backendsDBCollectors + backends and grab the Vendor value from backends to check for oracle or mssql
                        databases = ["oracle", "mssql"]
                        if any([x in potentialDBCollector["name"].lower() for x in databases]) or "ADO.NET" in potentialDBCollector["exitPointSubtype"]:
                            #print('Found Oracle or MS SQL!')
                            if "UNMAPPED" in potentialDBCollector["dbBackendStatus"]:
                                #print(f'Needs DB Collector!')
                                numberOfPotentialDBCollectors += 1
                                #print(numberOfPotentialDBCollectors)
                    except KeyError:
                        logging.debug(f'{hostInfo["controller"].host} - Node: {backend["name"]}')

                    # Running into a KeyError when attemping to insert these below
                    # Will need assistance to finish these out.
                    #analysisDataRawMetrics["numberOfPotentialDBCollectors"] = numberOfPotentialDBCollectors
                    #analysisDataEvaluatedMetrics["numberOfPotentialDBCollectors"] = numberOfPotentialDBCollectors

                # backendLimitNotHit
                backendLimit = int(
                    next(
                        iter([configuration for configuration in hostInfo["configurations"] if configuration["name"] == "backend.registration.limit"])
                    )["value"]
                )
                analysisDataEvaluatedMetrics["backendLimitNotHit"] = len(application["backends"]) <= backendLimit

                # numberOfCustomBackendRules
                # Default Backend Discovery configs have a version of 0 initially. Subsequent modifications increment the version.
                numberOfModifiedDefaultBackendDiscoveryConfigs = len(
                    [config for config in application["backendDiscoveryConfigs"] if config["version"] != 0]
                )
                numberOfCustomExitPoints = len(application["allCustomExitPoints"])
                analysisDataEvaluatedMetrics["numberOfCustomBackendRules"] = numberOfModifiedDefaultBackendDiscoveryConfigs + numberOfCustomExitPoints

                analysisDataRawMetrics["numberOfBackends"] = len(application["backends"])
                analysisDataRawMetrics["numberOfBackendsWithLoad"] = numberOfBackendsWithLoad
                analysisDataRawMetrics["numberOfDBBackendsWithLoad"] = numberOfDBBackendsWithLoad
                analysisDataRawMetrics["backendLimit"] = backendLimit
                analysisDataRawMetrics["numberOfModifiedDefaultBackendDiscoveryConfigs"] = numberOfModifiedDefaultBackendDiscoveryConfigs
                analysisDataRawMetrics["numberOfCustomExitPoints"] = numberOfCustomExitPoints

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
