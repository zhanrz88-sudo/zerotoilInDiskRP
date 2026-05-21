"""Tests for Break Old Snapshot Families TSG."""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from zerotoil.tsgs.break_old_snapshot_families import (
    ACIS_EXTENSION,
    ACIS_OPERATION,
    BreakOldSnapshotFamilies,
    BreakSnapshotFamilyInput,
    ManualActionRequired,
)


class TestBreakOldSnapshotFamiliesValidation(unittest.IsolatedAsyncioTestCase):
    """Test input validation."""

    async def test_valid_input(self):
        tsg = BreakOldSnapshotFamilies(dry_run=True)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="test-disk",
            subscription_id="aaaa-bbbb-cccc",
            resource_group="my-rg",
            region="eastus",
        )
        result = await tsg.run(tsg_input)
        assert result.status in ("completed", "submitted")

    async def test_empty_disk_name_raises(self):
        tsg = BreakOldSnapshotFamilies(dry_run=True)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="",
            subscription_id="aaaa-bbbb-cccc",
            resource_group="my-rg",
            region="eastus",
        )
        with self.assertRaises(ValueError):
            await tsg.run(tsg_input)

    async def test_empty_subscription_raises(self):
        tsg = BreakOldSnapshotFamilies(dry_run=True)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="test-disk",
            subscription_id="",
            resource_group="my-rg",
            region="eastus",
        )
        with self.assertRaises(ValueError):
            await tsg.run(tsg_input)

    async def test_empty_resource_group_raises(self):
        tsg = BreakOldSnapshotFamilies(dry_run=True)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="test-disk",
            subscription_id="aaaa-bbbb-cccc",
            resource_group="",
            region="eastus",
        )
        with self.assertRaises(ValueError):
            await tsg.run(tsg_input)

    async def test_empty_region_raises(self):
        tsg = BreakOldSnapshotFamilies(dry_run=True)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="test-disk",
            subscription_id="aaaa-bbbb-cccc",
            resource_group="my-rg",
            region="",
        )
        with self.assertRaises(ValueError):
            await tsg.run(tsg_input)


class TestBreakOldSnapshotFamiliesDryRun(unittest.IsolatedAsyncioTestCase):
    """Test dry-run mode skips mutating actions."""

    async def test_dry_run_skips_acis(self):
        tsg = BreakOldSnapshotFamilies(dry_run=True)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="FFM-SA-RDS01-datadisk_Z1_v2",
            subscription_id="19659d89-4b14-48d3-af88-fb1dbd02e14e",
            resource_group="FFM-FREEDOMFM",
            region="australiaeast",
        )
        result = await tsg.run(tsg_input)
        assert result.action_id == "dry-run-action-id"
        assert result.action_result == "dry-run-skipped"
        assert result.status == "completed"

    async def test_dry_run_with_clear_billing(self):
        tsg = BreakOldSnapshotFamilies(dry_run=True)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="test-disk",
            subscription_id="aaaa-bbbb-cccc",
            resource_group="my-rg",
            region="westus2",
            clear_billing=True,
        )
        result = await tsg.run(tsg_input)
        assert result.action_id == "dry-run-action-id"
        assert result.status == "completed"


class TestBreakOldSnapshotFamiliesLiveExecution(unittest.IsolatedAsyncioTestCase):
    """Test live execution with mocked ACIS and ICM."""

    @patch("zerotoil.tsgs.break_old_snapshot_families.icm")
    @patch("zerotoil.tsgs.break_old_snapshot_families.acis")
    async def test_submit_and_poll_success(self, mock_acis, mock_icm):
        mock_acis.submit = AsyncMock(return_value={"id": "action-123"})
        mock_acis.get_result = AsyncMock(return_value={"status": "Succeeded", "resultMessage": "Snapshot family removed"})

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = BreakOldSnapshotFamilies(dry_run=False)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="FFM-SA-RDS01-datadisk_Z1_v2",
            subscription_id="19659d89-4b14-48d3-af88-fb1dbd02e14e",
            resource_group="FFM-FREEDOMFM",
            region="australiaeast",
        )
        result = await tsg.run(tsg_input)

        # Verify ACIS was called correctly
        mock_acis.submit.assert_called_once()
        call_args = mock_acis.submit.call_args
        assert call_args[0][0] == ACIS_EXTENSION
        assert call_args[0][1] == ACIS_OPERATION
        params = call_args[0][2]
        # New format: positional params list
        assert params[0] == "19659d89-4b14-48d3-af88-fb1dbd02e14e"  # subscriptionId
        assert params[1] == "australiaeast"  # region
        assert params[2] == "FFM-FREEDOMFM"  # resourceGroup
        assert params[3] == "FFM-SA-RDS01-datadisk_Z1_v2"  # diskName
        assert params[4] == "false"  # skipValidation
        assert params[5] == "false"  # clearBilling

        # Verify polling
        mock_acis.get_result.assert_called_once_with(
            ACIS_EXTENSION, "action-123", wait_for_completion=True,
        )

        # Verify ICM comment
        mock_icm.get_incident.assert_called_once_with(12345)
        mock_incident.add_description.assert_called_once()
        comment_html = mock_incident.add_description.call_args[0][0]
        assert "FFM-SA-RDS01-datadisk_Z1_v2" in comment_html
        assert "action-123" in comment_html

        assert result.action_id == "action-123"
        assert result.status == "completed"

    @patch("zerotoil.tsgs.break_old_snapshot_families.icm")
    @patch("zerotoil.tsgs.break_old_snapshot_families.acis")
    async def test_submit_with_clear_billing(self, mock_acis, mock_icm):
        mock_acis.submit = AsyncMock(return_value={"id": "action-456"})
        mock_acis.get_result = AsyncMock(return_value={"status": "Succeeded"})

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = BreakOldSnapshotFamilies(dry_run=False)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="test-disk",
            subscription_id="aaaa-bbbb-cccc",
            resource_group="my-rg",
            region="westus2",
            clear_billing=True,
        )
        result = await tsg.run(tsg_input)

        # Verify ClearBilling was included in params
        call_args = mock_acis.submit.call_args
        params = call_args[0][2]
        assert params[5] == "true"  # clearBilling

    @patch("zerotoil.tsgs.break_old_snapshot_families.icm")
    @patch("zerotoil.tsgs.break_old_snapshot_families.acis")
    async def test_submit_without_clear_billing(self, mock_acis, mock_icm):
        mock_acis.submit = AsyncMock(return_value={"id": "action-789"})
        mock_acis.get_result = AsyncMock(return_value={"status": "Succeeded"})

        mock_incident = MagicMock()
        mock_incident.add_description = AsyncMock()
        mock_icm.get_incident = AsyncMock(return_value=mock_incident)

        tsg = BreakOldSnapshotFamilies(dry_run=False)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="test-disk",
            subscription_id="aaaa-bbbb-cccc",
            resource_group="my-rg",
            region="westus2",
            clear_billing=False,
        )
        result = await tsg.run(tsg_input)

        # Verify ClearBilling was NOT included
        call_args = mock_acis.submit.call_args
        params = call_args[0][2]
        assert params[5] == "false"  # clearBilling

    @patch("zerotoil.tsgs.break_old_snapshot_families.acis")
    async def test_acis_submit_failure(self, mock_acis):
        mock_acis.submit = AsyncMock(side_effect=Exception("JIT access denied"))

        tsg = BreakOldSnapshotFamilies(dry_run=False)
        tsg_input = BreakSnapshotFamilyInput(
            incident_id="12345",
            disk_name="test-disk",
            subscription_id="aaaa-bbbb-cccc",
            resource_group="my-rg",
            region="eastus",
        )
        with self.assertRaises(Exception, msg="JIT access denied"):
            await tsg.run(tsg_input)


class TestBreakOldSnapshotFamiliesManualInput(unittest.IsolatedAsyncioTestCase):
    """Test that run_for_incident raises ManualActionRequired."""

    @patch("xportal.icm.get_incident", new_callable=AsyncMock)
    async def test_run_for_incident_raises(self, mock_get_incident):
        mock_get_incident.return_value = MagicMock(
            Title="Test incident", Severity=3, Id=12345,
        )
        tsg = BreakOldSnapshotFamilies(dry_run=True)
        with self.assertRaises(ManualActionRequired):
            await tsg.run_for_incident("12345")


if __name__ == "__main__":
    unittest.main()
