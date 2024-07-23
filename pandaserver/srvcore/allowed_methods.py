# List of methods that can be executed by the clients

allowed_methods = []

# methods from pandaserver.taskbuffer.Utils
allowed_methods += [
    "isAlive",
    "putFile",
    "deleteFile",
    "getServer",
    "updateLog",
    "fetchLog",
    "touchFile",
    "getVomsAttr",
    "putEventPickingRequest",
    "getAttr",
    "uploadLog",
    "put_checkpoint",
    "delete_checkpoint",
    "put_file_recovery_request",
    "put_workflow_request",
]
# methods from pandaserver.jobdispatcher.JobDispatcher
allowed_methods += [
    "getJob",
    "updateJob",
    "getStatus",
    "genPilotToken",
    "getEventRanges",
    "updateEventRange",
    "getKeyPair",
    "updateEventRanges",
    "getDNsForS3",
    "getProxy",
    "get_access_token",
    "get_token_key",
    "getCommands",
    "ackCommands",
    "checkJobStatus",
    "checkEventsAvailability",
    "updateJobsInBulk",
    "getResourceTypes",
    "updateWorkerPilotStatus",
    "get_max_worker_id",
    "get_events_status",
]

# methods from pandaserver.userinterface.UserIF
allowed_methods += [
    "submitJobs",
    "getJobStatus",
    "queryPandaIDs",
    "killJobs",
    "reassignJobs",
    "getJobStatistics",
    "getJobStatisticsPerSite",
    "resubmitJobs",
    "queryLastFilesInDataset",
    "getPandaIDsSite",
    "getJobsToBeUpdated",
    "updateProdDBUpdateTimes",
    "getSiteSpecs",
    "getCloudSpecs",
    "queryJobInfoPerCloud",
    "getJobIDsInTimeRange",
    "getPandIDsWithJobID",
    "getFullJobStatus",
    "getJobStatisticsForBamboo",
    "addSiteAccess",
    "listSiteAccess",
    "getFilesInUseForAnal",
    "updateSiteAccess",
    "getPandaClientVer",
    "getSlimmedFileInfoPandaIDs",
    "getQueuedAnalJobs",
    "getHighestPrioJobStat",
    "getActiveDatasets",
    "getSerialNumberForGroupJob",
    "checkMergeGenerationStatus",
    "getNumPilots",
    "retryFailedJobsInActive",
    "getJobStatisticsWithLabel",
    "getPandaIDwithJobExeID",
    "getJobStatisticsPerUserSite",
    "getDisInUseForAnal",
    "getLFNsInUseForAnal",
    "getScriptOfflineRunning",
    "setDebugMode",
    "insertSandboxFileInfo",
    "checkSandboxFile",
    "changeJobPriorities",
    "insertTaskParams",
    "killTask",
    "finishTask",
    "getJediTasksInTimeRange",
    "getJediTaskDetails",
    "retryTask",
    "getRetryHistory",
    "changeTaskPriority",
    "reassignTask",
    "changeTaskAttributePanda",
    "pauseTask",
    "resumeTask",
    "increaseAttemptNrPanda",
    "killUnfinishedJobs",
    "changeTaskSplitRulePanda",
    "changeTaskModTimePanda",
    "avalancheTask",
    "getPandaIDsWithTaskID",
    "reactivateTask",
    "getTaskStatus",
    "reassignShare",
    "listTasksInShare",
    "getTaskParamsMap",
    "updateWorkers",
    "harvesterIsAlive",
    "reportWorkerStats",
    "reportWorkerStats_jobtype",
    "getWorkerStats",
    "addHarvesterDialogs",
    "getJobStatisticsPerSiteResource",
    "setNumSlotsForWP",
    "reloadInput",
    "enableJumboJobs",
    "updateServiceMetrics",
    "getUserJobMetadata",
    "getJumboJobDatasets",
    "getGShareStatus",
    "sweepPQ",
    "get_job_statistics_per_site_label_resource",
    "relay_idds_command",
    "send_command_to_job",
    "execute_idds_workflow_command",
    "set_user_secret",
    "get_user_secrets",
    "get_ban_users",
    "get_files_in_datasets",
    "release_task",
]
