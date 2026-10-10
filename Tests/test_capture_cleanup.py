import os
from pathlib import Path
import signal
import sys
import unittest
from unittest.mock import patch, Mock
import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts'))
import capture_russian_reference as adapter


class CleanupInterrupt(unittest.TestCase):
    def test_second_interrupt_cannot_abort_recovery_and_handler_restored(self):
        before=signal.getsignal(signal.SIGINT);events=[]
        def cleanup():
            self.assertEqual(signal.getsignal(signal.SIGINT),signal.SIG_IGN)
            os.kill(os.getpid(),signal.SIGINT);events.append('continued')
        with patch.object(adapter,'_finish',cleanup):adapter.finish()
        self.assertEqual(events,['continued']);self.assertEqual(signal.getsignal(signal.SIGINT),before)

    def test_handler_restored_when_real_recovery_reports_error(self):
        before=signal.getsignal(signal.SIGINT)
        with patch.object(adapter,'_finish',side_effect=ValueError('Unknown payload during restore')):
            with self.assertRaisesRegex(ValueError,'Unknown payload during restore'):adapter.finish()
        self.assertEqual(signal.getsignal(signal.SIGINT),before)


class ShutdownOwnership(unittest.TestCase):
    def setUp(self):
        self.path=str(adapter.FIXTURE/'Contents/Resources/Scripts/ShutdownScript.app')
        self.identity='Sun Oct 11 00:48:42 2026     '+self.path+'/Contents/MacOS/applet'
        self.epoch=datetime.datetime(2026,10,11,0,48,42).timestamp()
        self.record={'launchEpoch':self.epoch-10,'stopProcessIdentities':[[321,'verified prior Wine process']]}
        self.info={'applications':[{'pid':123,'path':self.path}]}

    def test_verified_shutdown_app_only_gets_sigterm(self):
        with patch.object(adapter.subprocess,'run',return_value=Mock(returncode=0,stdout=self.identity)), \
             patch.object(adapter.subprocess,'check_output',return_value=self.identity), \
             patch.object(adapter,'write') as write, patch('os.kill') as kill:
            adapter.stop_shutdown_applets(self.record,self.info)
            kill.assert_called_once_with(123,signal.SIGTERM);write.assert_called_once()
        self.assertEqual(self.record['shutdownProcessIdentities'],[[123,self.identity]])

    def test_valid_path_with_older_launch_is_rejected_before_kill(self):
        self.record['launchEpoch']=self.epoch+10
        with patch.object(adapter.subprocess,'run',return_value=Mock(returncode=0,stdout=self.identity)),patch('os.kill') as kill:
            with self.assertRaisesRegex(ValueError,'does not belong to this launched run'):
                adapter.stop_shutdown_applets(self.record,self.info)
            kill.assert_not_called()

    def test_identity_change_is_rejected_after_other_guards_pass(self):
        with patch.object(adapter.subprocess,'run',return_value=Mock(returncode=0,stdout=self.identity)), \
             patch.object(adapter.subprocess,'check_output',return_value=self.identity+' changed'),patch('os.kill') as kill:
            with self.assertRaisesRegex(ValueError,'Shutdown app identity changed'):
                adapter.stop_shutdown_applets(self.record,self.info)
            kill.assert_not_called()


if __name__=='__main__':unittest.main()
