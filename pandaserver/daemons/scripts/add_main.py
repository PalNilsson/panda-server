import os
import re
import sys
import time
import glob
import queue
import random
import datetime
import traceback
import threading
import multiprocessing

import pandaserver.taskbuffer.ErrorCode

from pandacommon.pandalogger.PandaLogger import PandaLogger
from pandacommon.pandautils import PandaUtils
from pandacommon.pandalogger.LogWrapper import LogWrapper
from pandacommon.pandautils.thread_utils import GenericThread
from pandaserver.config import panda_config
from pandaserver.taskbuffer import EventServiceUtils
from pandaserver.brokerage.SiteMapper import SiteMapper
from pandaserver.taskbuffer.TaskBuffer import TaskBuffer
from pandaserver.taskbuffer.TaskBufferInterface import TaskBufferInterface
from pandaserver.dataservice.AdderGen import AdderGen


# logger
_logger = PandaLogger().getLogger('add_main')


# main
def main(argv=tuple(), tbuf=None, **kwargs):

    try:
        long
    except NameError:
        long = int

    tmpLog = LogWrapper(_logger,None)

    tmpLog.debug("===================== start =====================")

    # return value, true to run main again in next daemon loop
    ret_val = True

    # overall timeout value
    overallTimeout = 20

    # grace period
    try:
        gracePeriod = int(argv[1])
    except Exception:
        gracePeriod = 3

    # current minute
    currentMinute = datetime.datetime.utcnow().minute


    # instantiate TB
    if tbuf is None:
        from pandaserver.taskbuffer.TaskBuffer import taskBuffer
        taskBuffer.init(panda_config.dbhost,panda_config.dbpasswd,nDBConnection=1)
    else:
        taskBuffer = tbuf

    # instantiate sitemapper
    aSiteMapper = SiteMapper(taskBuffer)


    # # process for adder
    # class AdderProcess:
    # thread for adder
    class AdderThread(GenericThread):

        def __init__(self, taskBuffer, aSiteMapper, holdingAna, job_output_reports, report_index_list):
            GenericThread.__init__(self)
            self.taskBuffer = taskBuffer
            self.aSiteMapper = aSiteMapper
            self.holdingAna = holdingAna
            self.job_output_reports = job_output_reports
            self.report_index_list = report_index_list

        # main loop
        def run(self):
            # get logger
            # _logger = PandaLogger().getLogger('add_process')
            # initialize
            taskBuffer = self.taskBuffer
            aSiteMapper = self.aSiteMapper
            holdingAna = self.holdingAna
            # get file list
            timeNow = datetime.datetime.utcnow()
            timeInt = datetime.datetime.utcnow()
            # try to pre-lock records for a short period of time, so that multiple nodes can get different records
            prelock_pid = self.get_pid()
            # unique pid
            GenericThread.__init__(self)
            uniq_pid = self.get_pid()
            # log pid
            tmpLog.debug("pid={0} prelock_pid={1}".format(uniq_pid, prelock_pid))
            # stats
            n_processed = 0
            n_skipped = 0
            # loop
            while True:
                # get report index from queue
                try:
                    report_index = self.report_index_list.get(timeout=1)
                except queue.Empty:
                    break
                # got a job report
                one_JOR = self.job_output_reports[report_index]
                panda_id, job_status, attempt_nr, time_stamp = one_JOR
                # get lock
                got_lock = taskBuffer.lockJobOutputReport(
                                panda_id=panda_id, attempt_nr=attempt_nr,
                                pid=prelock_pid, time_limit=10)
                if not got_lock:
                    # did not get lock, skip
                    n_skipped += 1
                    continue
                # time limit to avoid too many copyArchive running at the same time
                if (datetime.datetime.utcnow() - timeNow) > datetime.timedelta(minutes=overallTimeout):
                    tmpLog.debug("time over in Adder session")
                    break
                # check if near to logrotate
                if PandaUtils.isLogRotating(5,5):
                    tmpLog.debug("terminate since close to log-rotate time")
                    break
                # add
                try:
                    # modTime = datetime.datetime(*(time.gmtime(os.path.getmtime(fileName))[:7]))
                    modTime = time_stamp
                    adder_gen = None
                    if (timeNow - modTime) > datetime.timedelta(hours=24):
                        # last chance
                        tmpLog.debug("Last Add pid={0} job={1}.{2} st={3}".format(uniq_pid, panda_id, attempt_nr, job_status))
                        adder_gen = AdderGen(taskBuffer, panda_id, job_status, attempt_nr,
                                       ignoreTmpError=False, siteMapper=aSiteMapper, pid=uniq_pid, prelock_pid=prelock_pid)
                        n_processed += 1
                    elif (timeInt - modTime) > datetime.timedelta(minutes=gracePeriod):
                        # add
                        tmpLog.debug("Add pid={0} job={1}.{2} st={3}".format(uniq_pid, panda_id, attempt_nr, job_status))
                        adder_gen = AdderGen(taskBuffer, panda_id, job_status, attempt_nr,
                                       ignoreTmpError=True, siteMapper=aSiteMapper, pid=uniq_pid, prelock_pid=prelock_pid)
                        n_processed += 1
                    else:
                        n_skipped += 1
                    if adder_gen is not None:
                        adder_gen.run()
                        del adder_gen
                except Exception:
                    type, value, traceBack = sys.exc_info()
                    tmpLog.error("%s %s" % (type,value))
                # unlock prelocked reports if possible
                taskBuffer.unlockJobOutputReport(
                            panda_id=panda_id, attempt_nr=attempt_nr, pid=prelock_pid)
            # stats
            tmpLog.debug("pid={0} : processed {1} , skipped {2}".format(uniq_pid, n_processed, n_skipped))
        # launcher, run with multiprocessing
        # def launch(self,taskBuffer,aSiteMapper,holdingAna):
        def proc_launch(self):
            # run
            self.process = multiprocessing.Process(target=self.run)
            self.process.start()

        # join of multiprocessing
        def proc_join(self):
            self.process.join()


    # get buildJobs in the holding state
    tmpLog.debug("get holding build jobs")
    holdingAna = []
    varMap = {}
    varMap[':prodSourceLabel'] = 'panda'
    varMap[':jobStatus'] = 'holding'
    status,res = taskBuffer.querySQLS("SELECT PandaID from ATLAS_PANDA.jobsActive4 WHERE prodSourceLabel=:prodSourceLabel AND jobStatus=:jobStatus",varMap)
    if res is not None:
        for id, in res:
            holdingAna.append(id)
    tmpLog.debug("number of holding Ana %s " % len(holdingAna))

    # add files
    tmpLog.debug("run Adder processes")

    # make TaskBuffer IF
    # taskBufferIF = TaskBufferInterface()
    # taskBufferIF.launch(taskBuffer)

    # p = AdderProcess()
    # p.run(taskBuffer, aSiteMapper, holdingAna)

    adderThrList = []
    nThr = 6

    n_jors_per_batch = 2000

    # get some job output reports
    jor_list = taskBuffer.listJobOutputReport(only_unlocked=True, time_limit=10, limit=n_jors_per_batch*nThr,
                                              grace_period=gracePeriod)
    tmpLog.debug("got {0} job reports".format(len(jor_list)))
    if len(jor_list) < n_jors_per_batch*nThr*0.875:
        # too few job output reports, can stop the daemon loop
        ret_val = False

    # fill in queue
    job_output_reports = dict()
    report_index_list = multiprocessing.Queue()
    for one_jor in jor_list:
        panda_id, job_status, attempt_nr, time_stamp = one_jor
        report_index = (panda_id, attempt_nr)
        job_output_reports[report_index] = one_jor
        report_index_list.put(report_index)

    # taskBuffer interface for multiprocessing
    _tbuf = TaskBuffer()
    _tbuf.init(panda_config.dbhost, panda_config.dbpasswd, nDBConnection=3)
    taskBufferIF = TaskBufferInterface()
    taskBufferIF.launch(_tbuf)

    # adder consumer processes
    for i in range(nThr):
        # p = AdderProcess()
        # p.launch(taskBufferIF.getInterface(),aSiteMapper,holdingAna)
        # tbuf = TaskBuffer()
        # tbuf.init(panda_config.dbhost, panda_config.dbpasswd, nDBConnection=1)
        # thr = AdderThread(tbuf, aSiteMapper, holdingAna, job_output_reports, report_index_list)
        thr = AdderThread(taskBufferIF.getInterface(), aSiteMapper, holdingAna, job_output_reports, report_index_list)
        adderThrList.append(thr)
    # start all threads
    for thr in adderThrList:
        # thr.start()
        thr.proc_launch()
        time.sleep(0.25)

    # join all threads
    for thr in adderThrList:
        # thr.join()
        thr.proc_join()

    # terminate TaskBuffer IF
    # taskBufferIF.terminate()
    # stop TaskBuffer IF
    taskBufferIF.stop()

    tmpLog.debug("===================== end =====================")

    # return
    return ret_val


# run
if __name__ == '__main__':
    main(argv=sys.argv)
