# Copyright (C) 2016 Red Hat
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors: Adam Williamson <awilliam@redhat.com>

"""Important constants duplicated from openQA. We need to keep this in
sync with upstream, but it's better to have it done just once here
rather than every consumer of this library duplicating things like
'these are the "running" states' on the fly. It is explicitly allowed
to use 'from openqa_client.const import *'; this will only import
sanely named 'constants'. You may prefer to do `from openqa_client
import const as oqc` or similar.
"""

# we use 'bad' whitespace to align the definitions nicely.
# pylint: disable=bad-whitespace

# lib/OpenQA/Schema/Result/Jobs.pm

# States
JOB_STATE_SCHEDULED = "scheduled"
JOB_STATE_RUNNING =   "running"
JOB_STATE_CANCELLED = "cancelled"
JOB_STATE_WAITING =   "waiting"
JOB_STATE_DONE =      "done"
JOB_STATE_UPLOADING = "uploading"

JOB_STATES =           [JOB_STATE_SCHEDULED, JOB_STATE_RUNNING, JOB_STATE_CANCELLED,
                        JOB_STATE_WAITING, JOB_STATE_DONE, JOB_STATE_UPLOADING]
JOB_PENDING_STATES =   [JOB_STATE_SCHEDULED, JOB_STATE_RUNNING, JOB_STATE_WAITING,
                        JOB_STATE_UPLOADING]
JOB_EXECUTION_STATES = [JOB_STATE_RUNNING, JOB_STATE_WAITING, JOB_STATE_UPLOADING]
JOB_FINAL_STATES =     [JOB_STATE_DONE, JOB_STATE_CANCELLED]

# Results
JOB_RESULT_NONE =               "none"
JOB_RESULT_PASSED =             "passed"
JOB_RESULT_SOFTFAILED =         "softfailed"
JOB_RESULT_FAILED =             "failed"
JOB_RESULT_INCOMPLETE =         "incomplete"
JOB_RESULT_SKIPPED =            "skipped"
JOB_RESULT_OBSOLETED =          "obsoleted"
JOB_RESULT_PARALLEL_FAILED =    "parallel_failed"
JOB_RESULT_PARALLEL_RESTARTED = "parallel_restarted"
JOB_RESULT_USER_CANCELLED =     "user_cancelled"
JOB_RESULT_USER_RESTARTED =     "user_restarted"

JOB_RESULTS =            [JOB_RESULT_NONE, JOB_RESULT_PASSED, JOB_RESULT_SOFTFAILED,
                          JOB_RESULT_FAILED, JOB_RESULT_INCOMPLETE, JOB_RESULT_SKIPPED,
                          JOB_RESULT_OBSOLETED, JOB_RESULT_PARALLEL_FAILED,
                          JOB_RESULT_PARALLEL_RESTARTED, JOB_RESULT_USER_CANCELLED,
                          JOB_RESULT_USER_RESTARTED]
JOB_COMPLETE_RESULTS =   [JOB_RESULT_PASSED, JOB_RESULT_SOFTFAILED, JOB_RESULT_FAILED]
JOB_INCOMPLETE_RESULTS = [JOB_RESULT_INCOMPLETE, JOB_RESULT_SKIPPED, JOB_RESULT_OBSOLETED,
                          JOB_RESULT_PARALLEL_FAILED, JOB_RESULT_PARALLEL_RESTARTED,
                          JOB_RESULT_USER_CANCELLED, JOB_RESULT_USER_RESTARTED]
