using UnityEditor;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.XR;

namespace Emvr.Workflow.Editor
{
    internal static class EmvrHeadTrackingCheck
    {
        [MenuItem("Tools/EMVR/Diagnostics/Check Head Tracking")]
        public static void Check()
        {
            var camera = Camera.main;
            if (camera == null)
            {
                Debug.LogWarning("EMVR: no active camera with the MainCamera tag. Check the XR Origin and Game view camera.");
                return;
            }
            foreach (var other in Camera.allCameras)
                if (other != camera && other.CompareTag("MainCamera"))
                    Debug.LogWarning($"EMVR: another active MainCamera ({other.name}) exists alongside {camera.name}. Check which camera renders Game view.", other);
            if (!camera.TryGetComponent<TrackedPoseDriver>(out var driver))
            {
                Debug.LogWarning($"EMVR: MainCamera {camera.name} has no Input System Tracked Pose Driver.", camera);
                return;
            }
            if (!driver.isActiveAndEnabled)
                Debug.LogWarning($"EMVR: the Tracked Pose Driver on {camera.name} is disabled.", camera);
            Debug.Log($"EMVR: camera={camera.name}, scene={camera.gameObject.scene.path}, driver enabled={driver.isActiveAndEnabled}, play={Application.isPlaying}", camera);
            CheckInput(driver.positionInput, "Position");
            CheckInput(driver.rotationInput, "Rotation");
            CheckInput(driver.trackingStateInput, "Tracking State");
        }

        static void CheckInput(InputActionProperty input, string name)
        {
            var action = input.action;
            var actual = action == null ? "Missing" : $"{action.actionMap?.name}/{action.name}";
            if (actual != "XRI Head/" + name)
                Debug.LogWarning($"EMVR: expected XRI Head/{name}, found {actual}. Inspect the scene instance and the imported XR Rig.");
            else if (Application.isPlaying && !action.enabled)
                Debug.LogWarning($"EMVR: {actual} is disabled in Play Mode. Check the active Input Action Manager.");
            else
                Debug.Log($"EMVR: {actual} resolved, enabled={action.enabled}");
        }
    }
}
