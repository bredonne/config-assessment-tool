import logging
from collections import OrderedDict
from itertools import count

from api.appd.AppDService import AppDService
from extractionSteps.JobStepBase import JobStepBase
from util.asyncio_utils import AsyncioUtils


class NetworkRequestsBRUM(JobStepBase):
    def __init__(self):
        super().__init__("brum")

    async def extract(self, controllerData):
        """
        Extract node level details.
        1.
        """
        jobStepName = type(self).__name__

        for host, hostInfo in controllerData.items():
            logging.info(f'{hostInfo["controller"].host} - Extracting {jobStepName}')
            controller: AppDService = hostInfo["controller"]

            getEumPageListViewDataFutures = []
            getEumNetworkRequestListFutures = []
            getPagesAndFramesConfigFutures = []
            getAJAXConfigFutures = []
            getVirtualPagesConfigFutures = []
            getBrowserSnapshotsWithServerSnapshotsFutures = []
            getSettingsConfigFutures = []
            for application in hostInfo[self.componentType].values():
                getEumPageListViewDataFutures.append(controller.getEumPageListViewData(application["id"]))
                getEumNetworkRequestListFutures.append(controller.getEumNetworkRequestList(application["id"]))
                getPagesAndFramesConfigFutures.append(controller.getPagesAndFramesConfig(application["id"]))
                getAJAXConfigFutures.append(controller.getAJAXConfig(application["id"]))
                getVirtualPagesConfigFutures.append(controller.getVirtualPagesConfig(application["id"]))
                getBrowserSnapshotsWithServerSnapshotsFutures.append(controller.getBrowserSnapshotsWithServerSnapshots(application["id"]))
                getSettingsConfigFutures.append(controller.getSettingsConfig(application["id"]))

            eumPageListViewData = await AsyncioUtils.gatherWithConcurrency(*getEumPageListViewDataFutures)
            eumNetworkRequestList = await AsyncioUtils.gatherWithConcurrency(*getEumNetworkRequestListFutures)
            pagesAndFramesConfig = await AsyncioUtils.gatherWithConcurrency(*getPagesAndFramesConfigFutures)
            ajaxConfig = await AsyncioUtils.gatherWithConcurrency(*getAJAXConfigFutures)
            virtualPagesConfig = await AsyncioUtils.gatherWithConcurrency(*getVirtualPagesConfigFutures)
            browserSnapshotsWithServerSnapshots = await AsyncioUtils.gatherWithConcurrency(*getBrowserSnapshotsWithServerSnapshotsFutures)
            settingsConfig = await AsyncioUtils.gatherWithConcurrency(*getSettingsConfigFutures)

            for idx, application in enumerate(hostInfo[self.componentType]):
                hostInfo[self.componentType][application]["eumPageListViewData"] = eumPageListViewData[idx].data
                hostInfo[self.componentType][application]["eumNetworkRequestList"] = eumNetworkRequestList[idx].data
                hostInfo[self.componentType][application]["pagesAndFramesConfig"] = pagesAndFramesConfig[idx].data
                hostInfo[self.componentType][application]["ajaxConfig"] = ajaxConfig[idx].data
                hostInfo[self.componentType][application]["virtualPagesConfig"] = virtualPagesConfig[idx].data
                hostInfo[self.componentType][application]["browserSnapshotsWithServerSnapshots"] = browserSnapshotsWithServerSnapshots[idx].data
                hostInfo[self.componentType][application]["settingsConfig"] = settingsConfig[idx].data

    def analyze(self, controllerData, thresholds):
        """
        Analysis of node level details.
        1. Determines if Developer Mode is either enabled application wide or for any BT.
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

                analysisDataEvaluatedMetrics["collectingDataPastOneDay"] = application["metrics"]["pageRequestsPerMin"]["sum"] > 0
                analysisDataRawMetrics["totalCallsPastOneDay"] = application["metrics"]["pageRequestsPerMin"]["sum"]

                analysisDataRawMetrics["totalNetworkRequests"] = application["eumNetworkRequestList"]["totalCount"]
                analysisDataRawMetrics["totalAJAXRequests"] = len(
                    [app for app in application["eumNetworkRequestList"]["data"] if app["type"] == "AJAX_REQUEST"]
                )
                analysisDataRawMetrics["totalBasePageRequests"] = len(
                    [app for app in application["eumNetworkRequestList"]["data"] if app["type"] == "BASE_PAGE"]
                )
                analysisDataRawMetrics["totalVirtualPageRequests"] = len(
                    [app for app in application["eumNetworkRequestList"]["data"] if app["type"] == "VIRTUAL_PAGE"]
                )
                analysisDataRawMetrics["totalIFrameRequests"] = len(
                    [app for app in application["eumNetworkRequestList"]["data"] if app["type"] == "IFRAME"]
                )

                analysisDataRawMetrics["pageIFrameLimit"] = application["eumPageListViewData"]["pageIFrameLimit"]
                analysisDataRawMetrics["ajaxLimit"] = application["eumPageListViewData"]["ajaxLimit"]

                analysisDataEvaluatedMetrics["networkRequestLimitNotHit"] = (
                    analysisDataRawMetrics["totalAJAXRequests"] < analysisDataRawMetrics["ajaxLimit"]
                    and (
                        analysisDataRawMetrics["totalBasePageRequests"]
                        + analysisDataRawMetrics["totalVirtualPageRequests"]
                        + analysisDataRawMetrics["totalIFrameRequests"]
                    )
                    < analysisDataRawMetrics["pageIFrameLimit"]
                )

                numberOfCustomPageIncludeRules = len(application["pagesAndFramesConfig"]["customNamingIncludeRules"])
                numberOfCustomPageExcludeRules = len(application["pagesAndFramesConfig"]["customNamingExcludeRules"])
                numberOfCustomAJAXIncludeRules = len(application["ajaxConfig"]["customNamingIncludeRules"])
                numberOfCustomAJAXExcludeRules = len(application["ajaxConfig"]["customNamingExcludeRules"])
                numberOfCustomAJAXEventIncludeRules = len(application["ajaxConfig"]["eventServiceIncludeRules"])
                numberOfCustomAJAXEventExcludeRules = len(application["ajaxConfig"]["eventServiceExcludeRules"])
                numberOfCustomVirtualIncludeRules = len(application["virtualPagesConfig"]["customNamingIncludeRules"])
                numberOfCustomVirtualExcludeRules = len(application["virtualPagesConfig"]["customNamingExcludeRules"])
                numberOfCustomURLIncludeRules = 0
                numberOfCustomURLExcludeRules = 0

                nonDefaultIncludeRule = 0
                nonDefaultExcludeRule = 0
                try:
                    for rule in application["pagesAndFramesConfig"]["customNamingIncludeRules"]:
                        if not rule["isDefault"]:
                            nonDefaultIncludeRule += 1
                            if rule["matchOnURL"] is not None:
                                numberOfCustomURLIncludeRules += 1
                    for rule in application["pagesAndFramesConfig"]["customNamingExcludeRules"]:
                        if rule["matchOnURL"] is not None:
                            numberOfCustomURLExcludeRules += 1
                    for rule in application["ajaxConfig"]["customNamingIncludeRules"]:
                        if not rule["isDefault"]:
                            nonDefaultIncludeRule += 1
                            if rule["matchOnURL"] is not None:
                                numberOfCustomURLIncludeRules += 1
                    for rule in application["ajaxConfig"]["customNamingExcludeRules"]:
                        if rule["matchOnURL"] is not None:
                            numberOfCustomURLExcludeRules += 1
                    for rule in application["virtualPagesConfig"]["customNamingIncludeRules"]:
                        if not rule["isDefault"]:
                            nonDefaultIncludeRule += 1
                            if rule["matchOnURL"] is not None:
                                numberOfCustomURLIncludeRules += 1
                    for rule in application["virtualPagesConfig"]["customNamingExcludeRules"]:
                        if rule["matchOnURL"] is not None:
                            numberOfCustomURLExcludeRules += 1
                except (KeyError, TypeError, IndexError):
                    print("Couldn't find a match for the key in application")

                analysisDataEvaluatedMetrics["numberCustomMatchRules"] = (
                    numberOfCustomPageIncludeRules
                    + numberOfCustomPageExcludeRules
                    + numberOfCustomAJAXIncludeRules
                    + numberOfCustomAJAXExcludeRules
                    + numberOfCustomVirtualIncludeRules
                    + numberOfCustomVirtualExcludeRules
                )
                analysisDataRawMetrics["numberOfCustomPageIncludeRules"] = numberOfCustomPageIncludeRules
                analysisDataRawMetrics["numberOfCustomPageExcludeRules"] = numberOfCustomPageExcludeRules
                analysisDataRawMetrics["numberOfCustomAJAXIncludeRules"] = numberOfCustomAJAXIncludeRules
                analysisDataRawMetrics["numberOfCustomAJAXExcludeRules"] = numberOfCustomAJAXExcludeRules
                analysisDataRawMetrics["numberOfCustomAJAXEventIncludeRules"] = numberOfCustomAJAXEventIncludeRules
                analysisDataRawMetrics["numberOfCustomAJAXEventExcludeRules"] = numberOfCustomAJAXEventExcludeRules
                analysisDataRawMetrics["numberOfCustomVirtualIncludeRules"] = numberOfCustomVirtualIncludeRules
                analysisDataRawMetrics["numberOfCustomVirtualExcludeRules"] = numberOfCustomVirtualExcludeRules
                analysisDataRawMetrics["numberOfCustomURLIncludeRules"] = numberOfCustomURLIncludeRules
                analysisDataRawMetrics["numberOfCustomURLExcludeRules"] = numberOfCustomURLExcludeRules
                analysisDataRawMetrics["nonDefaultIncludeRule"] = nonDefaultIncludeRule
                analysisDataRawMetrics["nonDefaultExcludeRule"] = nonDefaultExcludeRule

                numBrowserSnapshotsWithServerSnapshots = 0
                if application["browserSnapshotsWithServerSnapshots"].get("snapshots"):
                    numBrowserSnapshotsWithServerSnapshots = len(application["browserSnapshotsWithServerSnapshots"]["snapshots"])
                analysisDataEvaluatedMetrics["hasBtCorrelation"] = numBrowserSnapshotsWithServerSnapshots > 0
                analysisDataRawMetrics["numberOfBrowserSnapshots"] = numBrowserSnapshotsWithServerSnapshots

                analysisDataEvaluatedMetrics["hasCustomEventServiceIncludeRule"] = len(application["ajaxConfig"]["eventServiceIncludeRules"]) > 0
                analysisDataRawMetrics["numberOfCustomEventServiceIncludeRules"] = len(application["ajaxConfig"]["eventServiceIncludeRules"])
                analysisDataRawMetrics["numberOfCustomEventServiceExcludeRules"] = len(application["ajaxConfig"]["eventServiceExcludeRules"])

                self.applyThresholds(analysisDataEvaluatedMetrics, analysisDataRoot, jobStepThresholds)
