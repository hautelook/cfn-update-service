#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import mock
import subprocess
import unittest

from cfnupdateservice import CloudFormationUpdateService
from cfnupdateservice.logging import Levels, Level, Logger
from datetime import datetime, timedelta, tzinfo


class CloudFormationUpdateServiceTestCase(unittest.TestCase):
    """Tests the CloudFormationUpdateService."""

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.iterator = 0

    @mock.patch.object(Logger, '__new__', autospec=True)
    def test_constructor(self, mock_logger):
        """Tests that the constructor works."""
        reference = CloudFormationUpdateService(
            stack_name="stacky",
            resource="resourcey",
            region="regiony",
            delay_minutes=1,
            logger=mock_logger()
        )

        self.assertEqual(reference.stack_name, "stacky")
        self.assertEqual(reference.resource, "resourcey")
        self.assertEqual(reference.region, "regiony")
        self.assertEqual(reference.delay_minutes, 1)
        self.assertEqual(reference.logger, mock_logger())
        # assert nones
        self.assertIsNone(reference.last_tick)
        self.assertIsNone(reference.last_checksum)

    @mock.patch('cfnupdateservice.datetime')
    @mock.patch.object(CloudFormationUpdateService, 'wait_until_next')
    @mock.patch.object(CloudFormationUpdateService, 'execute_update')
    @mock.patch.object(CloudFormationUpdateService, 'check_for_updates')
    def test_start(self, mock_check_for_updates, mock_execute_update, mock_wait_until_next, mock_datetime):
        """Tests that the start service method works as expected."""
        self.iterator = 0

        now = mock.MagicMock()
        mock_datetime.utcnow.return_value = now

        def condition():
            result = self.iterator <= 1
            self.iterator += 1
            return result

        reference = CloudFormationUpdateService(
            stack_name=None,
            resource=None,
            region=None,
            delay_minutes=1,
            logger=mock.Mock()
        )

        mock_check_for_updates.return_value = False

        # test where no updates
        reference.start(condition=condition)
        # should set the last tick to now
        self.assertEqual(reference.last_tick, now)

        mock_check_for_updates.assert_called_with()
        mock_wait_until_next.assert_called_with()
        mock_execute_update.assert_not_called()
        # test where updates
        self.iterator = 0
        mock_check_for_updates.reset_mock()
        mock_check_for_updates.return_value = True
        mock_wait_until_next.reset_mock()
        mock_execute_update.reset_mock()

        reference.start(condition=condition)
        mock_check_for_updates.assert_called_with()
        mock_execute_update.assert_called_with()
        mock_wait_until_next.assert_called_with()


    @mock.patch.object(CloudFormationUpdateService, 'fetch_metadata_checksum', autospec=True)
    def test_check_for_updates(self, mock_fetch_metadata):
        """Test that we can correctly check for updates and persist state."""
        reference = CloudFormationUpdateService(
            stack_name=None,
            resource=None,
            region=None,
            delay_minutes=1,
            logger=mock.Mock()
        )

        # test with empty last checksum
        mock_fetch_metadata.return_value = "46ea8ad0a953e9632d9e54bee5917bfb5cb814c02c65472d1577d06aea48496a"
        self.assertFalse(reference.check_for_updates())
        self.assertEqual(reference.last_checksum, "46ea8ad0a953e9632d9e54bee5917bfb5cb814c02c65472d1577d06aea48496a")

        # test with set last checksum, but with no difference
        self.assertFalse(reference.check_for_updates())
        self.assertEqual(reference.last_checksum, "46ea8ad0a953e9632d9e54bee5917bfb5cb814c02c65472d1577d06aea48496a")

        # test with an actual difference
        mock_fetch_metadata.return_value = "b6f00f283e24783b68eb63deb8c6f492dfafd29a45a11fa7c2725869596f81f4"
        self.assertTrue(reference.check_for_updates())
        self.assertEqual(reference.last_checksum, "b6f00f283e24783b68eb63deb8c6f492dfafd29a45a11fa7c2725869596f81f4")

    @mock.patch('cfnupdateservice.datetime')
    @mock.patch('cfnupdateservice.sleep')
    def test_wait_until_next(self, mock_sleep, mock_datetime):
        """Test that we sleep for the proper amount of time or not at all."""
        class UTC(tzinfo):
            def utcoffset(self, dt):
                return timedelta(0)
            def tzname(self, dt):
                return "UTC"
            def dst(self, dt):
                return timedelta(0)

        utc = UTC()
        now       = datetime(2000, 1, 1, 10, 1, 0, 0, utc)
        last_tick = datetime(2000, 1, 1, 10, 0, 0, 0, utc)
        mock_datetime.utcnow.return_value = now

        reference = CloudFormationUpdateService(
            stack_name=None,
            resource=None,
            region=None,
            delay_minutes=1,
            logger=mock.Mock()
        )

        reference.last_tick = last_tick

        # test a difference of one minute exactly from the last tick
        reference.wait_until_next()
        mock_sleep.assert_not_called() # should return immediately
        self.assertEqual(reference.last_tick, now) # should update last tick

        # test a difference of greater than one minute
        now = datetime(2000, 1, 1, 10, 2, 15, 0, utc) # 1 minute 15 seconds
        mock_datetime.utcnow.return_value = now

        reference.wait_until_next()
        mock_sleep.assert_not_called()

        # test a difference of less than one minute
        now = datetime(2000, 1, 1, 10, 2, 45, 0, utc) # 30 seconds
        mock_datetime.utcnow.return_value = now

        reference.wait_until_next()
        mock_sleep.assert_called_with(30.0)

    @mock.patch('cfnupdateservice.subprocess.Popen', autospec=True)
    def test_fetch_metadata_checksum(self, mock_popen):
        """Test that we can fetch metadata correctly."""
        reference = CloudFormationUpdateService(
            stack_name='s',
            resource='r',
            region='R',
            delay_minutes=1,
            logger=mock.Mock()
        )

        popen_object = mock.MagicMock()
        popen_object.returncode = 0
        popen_object.communicate.return_value = ("OUT", "ERR")
        mock_popen.return_value = popen_object

        # try in the best case scenario
        self.assertEqual(reference.fetch_metadata_checksum(), "c57929ed14088114883b23815775f37cb9f7d10c96f23b3cb2c1a3e375a6bbcc")
        mock_popen.assert_called_with(['/usr/bin/cfn-get-metadata', '-s', 's', '-r', 'r', '--region', 'R'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        reference.logger.error.assert_not_called()

        # try a failure
        popen_object.returncode = 1
        self.assertEqual(reference.fetch_metadata_checksum(), "1785cfc3bc6ac7738e8b38cdccd1af12563c2b9070e07af336a1bf8c0f772b6a")
        mock_popen.assert_called_with(['/usr/bin/cfn-get-metadata', '-s', 's', '-r', 'r', '--region', 'R'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        reference.logger.error.assert_called_with("Unable to execute cfn-get-metadata (1): \nERR")

    @mock.patch('cfnupdateservice.subprocess.Popen', autospec=True)
    def test_execute_update(self, mock_popen):
        """Test that we execute updates properly."""
        # setup
        mock_popen_object = mock.MagicMock()
        mock_popen_object.returncode = 0
        mock_popen_object.communicate.return_value = ("OUT", None)
        mock_popen.return_value = mock_popen_object

        reference = CloudFormationUpdateService(
            stack_name='s',
            resource='r',
            region='R',
            delay_minutes=1,
            logger=mock.Mock()
        )

        # test success case
        reference.execute_update()
        mock_popen.assert_called_with(['/usr/bin/cfn-init', '-v', '-s', 's', '-r', 'r', '--region', 'R'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        reference.logger.info.assert_called_with("Successfully updated based on the new CloudFormation metadata.")
        reference.logger.error.assert_not_called()

        # test error case
        mock_popen_object.returncode = 1
        reference.logger.reset_mock()
        reference.execute_update()
        mock_popen.assert_called_with(['/usr/bin/cfn-init', '-v', '-s', 's', '-r', 'r', '--region', 'R'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        reference.logger.error.assert_called_with("Unable to update based on the new CloudFormation metadata (1):\nOUT")
        reference.logger.info.assert_not_called()

class LoggingLevelsUnitTest(unittest.TestCase):
    """Test the Levels singleton."""

    def test_level_names(self):
        """Test that level names are expected."""
        self.assertEqual(Levels.TRACE.name, "TRACE")
        self.assertEqual(Levels.DEBUG.name, "DEBUG")
        self.assertEqual(Levels.INFO.name, "INFO")
        self.assertEqual(Levels.WARN.name, "WARN")
        self.assertEqual(Levels.ERROR.name, "ERROR")

    def test_level_values(self):
        """Test that level comparison works as planned."""
        self.assertGreater(Levels.DEBUG.priority, Levels.TRACE.priority)
        self.assertGreater(Levels.INFO.priority, Levels.DEBUG.priority)
        self.assertGreater(Levels.WARN.priority, Levels.INFO.priority)
        self.assertGreater(Levels.ERROR.priority, Levels.WARN.priority)

    def test_get_all(self):
        """Tests that fetching all logging levels works."""
        self.assertEqual(5, len(Levels.get_all()))
        self.assertIn(Levels.TRACE, Levels.get_all())
        self.assertIn(Levels.DEBUG, Levels.get_all())
        self.assertIn(Levels.INFO, Levels.get_all())
        self.assertIn(Levels.WARN, Levels.get_all())
        self.assertIn(Levels.ERROR, Levels.get_all())


class LoggingLevelUnitTest(unittest.TestCase):
    """Tests construction of logging level objects."""

    def test_constructor(self):
        reference = Level('arbitrary', 9000)

        self.assertEqual(reference.name, 'arbitrary')
        self.assertEqual(reference.priority, 9000)


class LoggerUnitTest(unittest.TestCase):
    """Tests logger functionality."""

    def test_constructor(self):
        reference = Logger(
            name="arbitrarylogger",
            syslog=True,
            json=True,
            level=Levels.INFO
        )

        self.assertEqual(reference.name, "arbitrarylogger")
        self.assertEqual(reference.syslog, True)
        self.assertEqual(reference.json, True)
        self.assertEqual(reference.level, Levels.INFO)

    @mock.patch('cfnupdateservice.logging.print')
    @mock.patch('cfnupdateservice.logging.syslog.syslog')
    def test_write(self, mock_syslog, mock_print):
        """Test the output writing of the logger."""
        # test writing to syslog
        reference = Logger("arbitrarylogger", syslog=True, json=False)
        reference.write("sample")

        mock_syslog.assert_called_with("sample")
        mock_print.assert_not_called()

        # reset mocks
        mock_syslog.reset_mock()
        mock_print.reset_mock()

        # test writing to stdout
        reference.syslog=False
        reference.write("sample")

        mock_syslog.assert_not_called()
        mock_print.assert_called_with("sample")

    @mock.patch('cfnupdateservice.logging.json.dumps')
    def test_format(self, mock_json_dumps):
        """Tests formatting of logging messages."""
        reference = Logger("arbitrarylogger", syslog=False, json=True)
        event = {'message': 'hello', 'level': Levels.INFO.name, 'logger': 'arbitrarylogger', 'timestamp': 'lolnao'}

        # test JSON formatting; JSON key sorting is not deterministic or weird at best
        reference.format(event)
        mock_json_dumps.assert_called_with(event)

        # test plaintext formatting
        reference.json = False
        self.assertEqual("lolnao [INFO ] arbitrarylogger - hello", reference.format(event))

    @mock.patch('cfnupdateservice.logging.datetime')
    def test_get_timestamp(self, mock_datetime):
        """Tests getting the current formatted timestamp."""
        mock_utcnow = mock.Mock()
        mock_datetime.utcnow.return_value = mock_utcnow

        reference = Logger("arbitrarylogger")
        reference.get_timestamp()

        mock_utcnow.strftime.assert_called_with("%Y-%m-%dT%H:%M:%SZ")

    @mock.patch.object(Logger, 'get_timestamp')
    def test_generate_event(self, mock_get_timestamp):
        """Tests generating a logging event."""
        mock_get_timestamp.return_value = "CUKE"

        reference = Logger("arbitraryname")
        expected = { 'level': "ERROR", "message": "the message", "logger": "arbitraryname", "timestamp": "CUKE"}

        self.assertEqual(reference.generate_event(Levels.ERROR, "the message"), expected)

    @mock.patch.object(Logger, 'write')
    @mock.patch.object(Logger, 'format')
    @mock.patch.object(Logger, 'generate_event')
    def test_emit(self, mock_generate_event, mock_format, mock_write):
        """Tests that emitting a message works as expected."""
        # setup mocks
        event, message = mock.Mock(), mock.Mock()
        mock_generate_event.return_value = event
        mock_format.return_value = message

        # test
        reference = Logger("arbitrarylogger", level=Levels.INFO)

        # test that a message won't be emitted with an unknown level
        self.assertFalse(reference.emit(Level("UNKNOWN", 999), "message"))
        mock_generate_event.assert_not_called()
        mock_format.assert_not_called()
        mock_write.assert_not_called()
        # test that a message won't be emitted with a level below the set level
        self.assertFalse(reference.emit(Levels.DEBUG, "message"))
        mock_generate_event.assert_not_called()
        mock_format.assert_not_called()
        mock_write.assert_not_called()
        # test that a righteous logging event will get through
        self.assertTrue(reference.emit(Levels.INFO, "message"))
        mock_generate_event.assert_called_with(Levels.INFO, "message")
        mock_format.assert_called_with(event)
        mock_write.assert_called_with(message)

    @mock.patch.object(Logger, 'emit')
    def test_trace(self, mock_emit):
        Logger("arbitrarylogger", Levels.TRACE).trace("message")
        mock_emit.assert_called_with(Levels.TRACE, "message")

    @mock.patch.object(Logger, 'emit')
    def test_debug(self, mock_emit):
        Logger("arbitrarylogger", Levels.TRACE).debug("message")
        mock_emit.assert_called_with(Levels.DEBUG, "message")

    @mock.patch.object(Logger, 'emit')
    def test_info(self, mock_emit):
        Logger("arbitrarylogger", Levels.TRACE).info("message")
        mock_emit.assert_called_with(Levels.INFO, "message")

    @mock.patch.object(Logger, 'emit')
    def test_info(self, mock_emit):
        Logger("arbitrarylogger", Levels.TRACE).warn("message")
        mock_emit.assert_called_with(Levels.WARN, "message")

    @mock.patch.object(Logger, 'emit')
    def test_info(self, mock_emit):
        Logger("arbitrarylogger", Levels.TRACE).error("message")
        mock_emit.assert_called_with(Levels.ERROR, "message")
