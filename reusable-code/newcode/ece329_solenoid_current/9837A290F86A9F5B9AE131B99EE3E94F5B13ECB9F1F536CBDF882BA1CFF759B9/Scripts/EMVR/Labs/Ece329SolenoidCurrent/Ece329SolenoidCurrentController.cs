using EMVR.Common.Assist;
using EMVR.Common.Objects;
using EMVR.Common.SceneFlow;
using EMVR.Common.Telemetry;
using EMVR.Common.UI;
using EMVR.ReusableFoundation.Gate5;
using UnityEngine;
using UnityEngine.UI;

namespace EMVR.Labs.Ece329SolenoidCurrent
{
    [DisallowMultipleComponent]
    public sealed class Ece329SolenoidCurrentController : MonoBehaviour
    {
        public const string LabId = "ece329_solenoid_current";

        public EmVrGate5FoundationHarness harness;
        public EmVrObjectStateSnapshotStore snapshots;
        public EmVrLabContractRunner runner;
        public EmVrAssistGroundingProvider assist;
        public EmVrTelemetryEmitter telemetry;
        public EmVrStatusDisplay status;
        public Text statusLabel;
        public Button spawnButton;

        void OnEnable()
        {
            if (status != null)
                status.StatusChanged += DisplayStatus;
        }

        void Start()
        {
            if (runner.TryStartLab(out string error))
                status.SetStatus("foundation", "Ready - spawn the test object");
            else
                ShowError(error);
        }

        void OnDisable()
        {
            if (status != null)
                status.StatusChanged -= DisplayStatus;
        }

        public void SpawnNeutral()
        {
            if (harness.SpawnedObject != null)
                return;

            var anchor = harness.replacementSpawner.spawnAnchor;
            Vector3 viewport = harness.validationCamera.WorldToViewportPoint(anchor.position);
            if (viewport.z <= 0f || viewport.x < 0.05f || viewport.x > 0.95f
                || viewport.y < 0.05f || viewport.y > 0.95f)
            {
                status.SetStatus("foundation", "Face the center of the room and try Spawn again");
                return;
            }

            harness.SpawnAndValidate();
            if (harness.SpawnedObject == null)
                return;
            EmVrLabObject target = harness.SpawnedObject.GetComponent<EmVrLabObject>();
            target.CaptureInitialState();
            snapshots.explicitObjects = new[] { target };
            assist.explicitObjectSources = new MonoBehaviour[] { target };
            assist.SetSelectedObject(target);
            spawnButton.interactable = false;
            status.SetStatus("foundation", "Spawned - drag, capture, restore or reset");
            telemetry.Emit("foundation_spawned", target.ExportStateJson());
        }

        public void CaptureNeutral()
        {
            if (!HasTarget())
                return;
            if (snapshots.TryCaptureSnapshot(out _, out string error))
                status.SetStatus("foundation", "Captured");
            else
                ShowError(error);
        }

        public void RestoreNeutral()
        {
            if (!HasTarget())
                return;
            if (snapshots.TryRestoreCurrentSnapshot(out string error))
                status.SetStatus("foundation", "Restored the captured position");
            else
                ShowError(error);
        }

        public void ResetNeutral()
        {
            if (!HasTarget())
                return;
            if (snapshots.TryResetObjects(out string error))
                status.SetStatus("foundation", "Reset to the spawn position");
            else
                ShowError(error);
        }

        bool HasTarget()
        {
            if (harness.SpawnedObject != null)
                return true;
            status.SetStatus("foundation", "Spawn the test object first");
            return false;
        }

        void ShowError(string error)
        {
            status.SetStatus("foundation", error);
            Debug.LogError(error, this);
        }

        void DisplayStatus(string message)
        {
            statusLabel.text = message;
        }
    }
}
