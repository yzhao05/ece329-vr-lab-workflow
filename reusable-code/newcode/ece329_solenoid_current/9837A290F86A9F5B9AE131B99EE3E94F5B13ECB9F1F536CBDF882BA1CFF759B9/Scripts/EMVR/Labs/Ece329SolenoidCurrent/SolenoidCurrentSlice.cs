using System;
using System.Collections.Generic;
using System.Globalization;
using EMVR.Common.Assist;
using EMVR.Common.Objects;
using EMVR.Common.SceneFlow;
using EMVR.Common.Telemetry;
using EMVR.Common.UI;
using UnityEngine;
using UnityEngine.UI;

namespace EMVR.Labs.Ece329SolenoidCurrent
{
    [DisallowMultipleComponent]
    public sealed class SolenoidCurrentSlice : MonoBehaviour
    {
        const double Mu0 = 1.25663706e-6;
        const double TurnsPerMetre = 1000;
        static readonly int[] RequiredTicks = { 0, 5, 10, 15, 20 };

        public GameObject startPage;
        public GameObject labPage;
        public GameObject apparatus;
        public Slider currentSlider;
        public Text readout;
        public Text instruction;
        public Text message;
        public Text report;
        public Text recordedReadings;
        public Button compareButton;
        public Button finishButton;
        public SolenoidScatterPlot plot;
        public EmVrParameterizedLabObject currentState;
        public EmVrObjectStateSnapshotStore snapshots;
        public EmVrTelemetryEmitter telemetry;
        public EmVrAssistGroundingProvider assist;
        public EmVrStatusDisplay status;
        public EmVrLabContractRunner runner;

        readonly List<Sample> samples = new List<Sample>();
        string capturedState;
        int lastSnapshotId;
        bool labOpen;

        void OnEnable()
        {
            currentSlider.onValueChanged.AddListener(SetCurrentTick);
        }

        void OnDisable()
        {
            currentSlider.onValueChanged.RemoveListener(SetCurrentTick);
        }

        public void OpenLab()
        {
            if (labOpen)
                return;
            labOpen = true;
            startPage.SetActive(false);
            labPage.SetActive(true);
            apparatus.SetActive(true);
            if (!ResetData())
                return;
            if (!runner.TryStartLab(out string error))
            {
                ShowStatus(error);
                return;
            }
            Emit("session_start");
            ShowInstruction();
        }

        public void Back()
        {
            labOpen = false;
            labPage.SetActive(false);
            apparatus.SetActive(false);
            startPage.SetActive(true);
        }

        void SetCurrentTick(float tick)
        {
            if (!labOpen)
                return;
            if (float.IsNaN(tick) || float.IsInfinity(tick) || tick < 0f || tick > 20f)
            {
                RefreshReadout();
                ShowStatus("Choose a current from 0.0 to 2.0 A.");
                Emit("solenoid_invalid_input", "Current is outside the allowed range.");
                return;
            }
            currentState.SetParameterValue(Mathf.RoundToInt(tick) / 10f);
            Emit("solenoid_current_changed");
            RefreshReadout();
            Emit("solenoid_readout_refreshed");
            ShowStatus("Reading updated. Record to add a point.");
        }

        public void Capture()
        {
            if (!labOpen)
                return;
            if (!snapshots.TryCaptureSnapshot(out string snapshot, out string error))
            {
                ShowStatus(error);
                return;
            }

            string step = runner.CurrentStepId;
            capturedState = snapshot;
            lastSnapshotId++;
            int tick = CurrentTick();
            samples.Add(new Sample { tick = tick, bz = FieldMilliTesla(tick) });
            plot.AddPoint(tick / 10f, (float)FieldMilliTesla(tick));
            RefreshRecordedReadings();
            RefreshReadout();
            Emit("solenoid_capture");
            if (step == "S2" && tick == 0)
                AdvanceStep();
            if (runner.CurrentStepId == "S3" && HasRequiredSamples())
            {
                if (AdvanceStep())
                    AdvanceStep(); // S3 and S4 share the four recorded setpoint checks.
            }
            ShowInstruction();
            ShowStatus("Recorded point " + samples.Count + ".");
        }

        public void Restore()
        {
            if (!labOpen)
                return;
            if (string.IsNullOrEmpty(capturedState))
            {
                ShowStatus("Record a point before restoring.");
                return;
            }
            if (!snapshots.TryRestoreSnapshot(capturedState, out string error))
            {
                ShowStatus(error);
                return;
            }
            RefreshReadout();
            Emit("solenoid_restore");
            ShowStatus("Restored the latest recorded current.");
        }

        public void ResetMeasurement()
        {
            if (!labOpen)
                return;
            int dropped = samples.Count;
            if (!ResetData())
                return;
            if (!runner.TryStartLab(out string error))
            {
                ShowStatus(error);
                return;
            }
            Emit("solenoid_reset", dropped: dropped);
            AdvanceStep();
            ShowInstruction();
            ShowStatus("Current reset. All recorded points cleared.");
        }

        bool ResetData()
        {
            if (!snapshots.TryResetObjects(out string error))
            {
                ShowStatus(error);
                return false;
            }
            capturedState = null;
            samples.Clear();
            plot.ClearPoints();
            RefreshRecordedReadings();
            report.text = string.Empty;
            compareButton.interactable = false;
            finishButton.interactable = false;
            RefreshReadout();
            return true;
        }

        public void Compare()
        {
            if (!labOpen || runner.CurrentStepId != "S5" || !HasRequiredSamples())
                return;
            double slope = (FirstRequiredSample(20).bz - FirstRequiredSample(0).bz) / 2.0;
            if (!AdvanceStep())
                return;
            report.text = string.Format(CultureInfo.InvariantCulture,
                "Measured slope: {0:F3} mT/A. Theory: 1.257 mT/A.\n"
                + "Q1. Do the origin, slope and points support a proportional relationship?\n"
                + "Q2. What does this simulation compare, and what would you measure on a real coil?", slope);
            ShowInstruction();
            ShowStatus("Compare the five points, then answer both questions in your report.");
        }

        public void Finish()
        {
            if (!labOpen || runner.CurrentStepId != "S6" || !AdvanceStep())
                return;
            Emit("outcome_recorded");
            ShowInstruction();
            ShowStatus("VR task complete. Submit readings, plot and both report answers.");
        }

        public void Help()
        {
            if (!labOpen)
                return;
            assist.SetSelectedObject(currentState);
            string grounding = assist.BuildAssistGroundingJson();
            telemetry.Emit("assist_requested", grounding);
            string help = runner.CurrentStepId == "S3" && !HasRequiredSamples()
                ? "Next required current: " + (NextRequiredTick() / 10f).ToString("F1", CultureInfo.InvariantCulture) + " A."
                : instruction.text;
            ShowStatus(help);
            Emit("assist_response_shown");
        }

        bool AdvanceStep()
        {
            if (runner.TryCompleteCurrentStep(out string error))
            {
                if (!runner.IsLabCompleted)
                    Emit("step_start");
                return true;
            }
            ShowStatus(error);
            return false;
        }

        void ShowInstruction()
        {
            string step = runner.CurrentStepId;
            compareButton.interactable = step == "S5" && HasRequiredSamples();
            finishButton.interactable = step == "S6";
            switch (step)
            {
                case "S1": instruction.text = "Reset to check the zero-current baseline."; break;
                case "S2": instruction.text = "Record the 0.0 A reference point."; break;
                case "S3": instruction.text = "Record 0.5, 1.0, 1.5 and 2.0 A, in order."; break;
                case "S5": instruction.text = "Compare the five readings with the dashed theory line."; break;
                case "S6": instruction.text = "Use the plot and slope to answer the report questions."; break;
                default: instruction.text = "Experiment complete."; break;
            }
            assist.stepId = step;
        }

        bool HasRequiredSamples()
        {
            return NextRequiredTick() < 0;
        }

        int NextRequiredTick()
        {
            int remaining = 0;
            foreach (Sample sample in samples)
            {
                if (sample.tick != RequiredTicks[remaining])
                    continue;
                remaining++;
                if (remaining == RequiredTicks.Length)
                    return -1;
            }
            return RequiredTicks[remaining];
        }

        Sample FirstRequiredSample(int tick)
        {
            return samples.Find(sample => sample.tick == tick);
        }

        void RefreshRecordedReadings()
        {
            var readings = new List<string>();
            foreach (int tick in RequiredTicks)
            {
                int index = samples.FindIndex(sample => sample.tick == tick);
                if (index >= 0)
                    readings.Add(string.Format(CultureInfo.InvariantCulture, "{0:F1} / {1:F3}",
                        tick / 10f, samples[index].bz));
            }
            recordedReadings.text = readings.Count == 0
                ? "Recorded readings: none"
                : "A / mT: " + string.Join("     ", readings);
        }

        void RefreshReadout()
        {
            int tick = CurrentTick();
            currentSlider.SetValueWithoutNotify(tick);
            readout.text = string.Format(CultureInfo.InvariantCulture, "I = {0:F1} A     Center Bz = {1:F3} mT",
                tick / 10f, FieldMilliTesla(tick));
            assist.diagnosticHintsJson = JsonUtility.ToJson(EventData());
        }

        void ShowStatus(string value)
        {
            status.SetStatus("experiment", value);
            message.text = value;
        }

        int CurrentTick()
        {
            return Mathf.RoundToInt(currentState.ParameterValue * 10f);
        }

        static double FieldMilliTesla(int tick)
        {
            return Mu0 * TurnsPerMetre * (tick / 10.0) * 1000.0;
        }

        void Emit(string name, string reason = "", int dropped = 0)
        {
            Payload payload = EventData();
            payload.reason = reason;
            payload.dropped_sample_count = dropped;
            telemetry.Emit(name, JsonUtility.ToJson(payload));
        }

        Payload EventData()
        {
            return new Payload
            {
                event_id = Guid.NewGuid().ToString("N"),
                session_id = runner.sessionId,
                user_id = runner.userId,
                lab_id = Ece329SolenoidCurrentController.LabId,
                step_id = runner.CurrentStepId,
                object_id = currentState.ObjectId,
                current_a = CurrentTick() / 10f,
                center_bz_mt = FieldMilliTesla(CurrentTick()),
                snapshot_id = capturedState == null ? 0 : lastSnapshotId,
                sample_count = samples.Count,
                next_required_tick = NextRequiredTick(),
                resolved = runner.IsLabCompleted
            };
        }

        struct Sample
        {
            public int tick;
            public double bz;
        }

        [Serializable]
        sealed class Payload
        {
            public string event_id, session_id, user_id, lab_id, step_id, object_id, reason;
            public float current_a;
            public double center_bz_mt;
            public int snapshot_id, sample_count, next_required_tick, dropped_sample_count;
            public bool resolved;
        }
    }
}
