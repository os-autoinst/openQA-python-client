# Copyright Red Hat
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
import const as oqc` or similar. For details on what each of these
means, please refer to the openQA source, it has comments that explain
them; it seems unnecessary to duplicate those here.
"""

# we use 'bad' whitespace to align the definitions nicely.
# pylint: disable=bad-whitespace

# lib/OpenQA/Schema/Result/Jobs.pm

# States
JOB_STATE_SCHEDULED = "scheduled"
JOB_STATE_ASSIGNED =  "assigned"
JOB_STATE_SETUP =     "setup"
JOB_STATE_RUNNING =   "running"
JOB_STATE_UPLOADING = "uploading"
JOB_STATE_CANCELLED = "cancelled"
JOB_STATE_DONE =      "done"

JOB_STATES =               (JOB_STATE_SCHEDULED, JOB_STATE_SETUP, JOB_STATE_RUNNING,
                            JOB_STATE_CANCELLED, JOB_STATE_DONE, JOB_STATE_UPLOADING,
                            JOB_STATE_ASSIGNED)
JOB_PENDING_STATES =       (JOB_STATE_SCHEDULED, JOB_STATE_ASSIGNED, JOB_STATE_SETUP,
                            JOB_STATE_RUNNING, JOB_STATE_UPLOADING)
JOB_EXECUTION_STATES =     (JOB_STATE_ASSIGNED, JOB_STATE_SETUP,
                            JOB_STATE_RUNNING, JOB_STATE_UPLOADING)
JOB_PRE_EXECUTION_STATES = (JOB_STATE_SCHEDULED,)
JOB_FINAL_STATES =         (JOB_STATE_DONE, JOB_STATE_CANCELLED)

# These are referred to as 'meta' states upstream
JOB_STATE_PRE_EXECUTION = "pre_execution"
JOB_STATE_EXECUTION =     "execution"
JOB_STATE_FINAL =         "final"

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
JOB_RESULT_TIMEOUT_EXCEEDED =   "timeout_exceeded"

JOB_RESULTS =              (JOB_RESULT_NONE, JOB_RESULT_PASSED, JOB_RESULT_SOFTFAILED,
                            JOB_RESULT_FAILED, JOB_RESULT_INCOMPLETE, JOB_RESULT_SKIPPED,
                            JOB_RESULT_OBSOLETED, JOB_RESULT_PARALLEL_FAILED,
                            JOB_RESULT_PARALLEL_RESTARTED, JOB_RESULT_USER_CANCELLED,
                            JOB_RESULT_USER_RESTARTED, JOB_RESULT_TIMEOUT_EXCEEDED)
JOB_COMPLETE_RESULTS =     (JOB_RESULT_PASSED, JOB_RESULT_SOFTFAILED, JOB_RESULT_FAILED)
JOB_OK_RESULTS =           (JOB_RESULT_PASSED, JOB_RESULT_SOFTFAILED)
JOB_NOT_COMPLETE_RESULTS = (JOB_RESULT_INCOMPLETE, JOB_RESULT_TIMEOUT_EXCEEDED)
JOB_ABORTED_RESULTS =      (JOB_RESULT_SKIPPED, JOB_RESULT_OBSOLETED, JOB_RESULT_PARALLEL_FAILED,
                            JOB_RESULT_PARALLEL_RESTARTED, JOB_RESULT_USER_CANCELLED,
                            JOB_RESULT_USER_RESTARTED)
JOB_NOT_OK_RESULTS =       (JOB_RESULT_FAILED,) + JOB_NOT_COMPLETE_RESULTS + JOB_ABORTED_RESULTS

# 'meta' results
JOB_RESULT_COMPLETE =     "complete"
JOB_RESULT_NOT_COMPLETE = "not_complete"
JOB_RESULT_ABORTED =      "aborted"

# Scenarios
JOB_SCENARIO_KEYS              = ('DISTRI', 'VERSION', 'FLAVOR', 'ARCH', 'TEST')
JOB_SCENARIO_WITH_MACHINE_KEYS = JOB_SCENARIO_KEYS + ('MACHINE',)
