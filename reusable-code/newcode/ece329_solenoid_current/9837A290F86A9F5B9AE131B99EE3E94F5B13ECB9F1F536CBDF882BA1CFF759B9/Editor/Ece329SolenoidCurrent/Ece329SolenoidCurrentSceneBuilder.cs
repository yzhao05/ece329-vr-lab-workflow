using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using EMVR.Common.Assist;
using EMVR.Common.Editor.Validation;
using EMVR.Common.Interaction;
using EMVR.Common.Objects;
using EMVR.Common.SceneFlow;
using EMVR.Common.Telemetry;
using EMVR.Common.UI;
using EMVR.ReusableFoundation.Gate5.Editor;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using UnityEngine.XR.Interaction.Toolkit;
using UnityEngine.XR.Interaction.Toolkit.UI;
using UnityEngine.XR.Interaction.Toolkit.Inputs.Simulation;

namespace EMVR.Labs.Ece329SolenoidCurrent.Editor
{
    public static class Ece329SolenoidCurrentSceneBuilder
    {
        const string LabId = Ece329SolenoidCurrentController.LabId;
        const string ScenePath = "Assets/Scenes/ece329_solenoid_current.unity";
        const string RootName = "Ece329SolenoidCurrent_Generated";
        const string Imports = "Assets/Generated/" + LabId + "/ApprovedDependencies/";

        const string SimulatorDirectory = "XRInteractionToolkitSamples/XR Device Simulator/";
        const string SimulatorPrefab = SimulatorDirectory + "XR Device Simulator.prefab";
        const ImportAssetOptions ReimportOptions =
            ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport;

        [MenuItem("Tools/EMVR/Labs/Build Ece329 Solenoid Current")]
        public static void BuildScene()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
            {
                EditorUtility.DisplayDialog("EMVR Lab Builder", "Exit Play Mode before building.", "OK");
                return;
            }
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
                return;

            try
            {
                using (var guard = new EmVrGate5BuildGuard())
                {
                    RequireXrInputAssets();
                    var lighting = EmVrRoomLighting.ForLab(LabId, ScenePath);
                    LightingSettings settings = lighting.RequireRoomLightingSettings();
                    string previousPath = SceneManager.GetActiveScene().path;
                    Scene inspection = default;
                    Scene scene = default;
                    try
                    {
                        if (AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath) != null)
                        {
                            Scene target = SceneManager.GetSceneByPath(ScenePath);
                            if (!target.isLoaded)
                            {
                                inspection = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Additive);
                                target = inspection;
                            }
                            if (!target.GetRootGameObjects().Any(root => root.name == RootName))
                                throw new InvalidOperationException("The target scene has no current-Lab ownership marker.");
                            if (inspection.IsValid())
                            {
                                EditorSceneManager.CloseScene(inspection, true);
                                inspection = default;
                            }
                        }

                        scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                        var experiment = new GameObject(RootName);
                        Transform room = Child(experiment.transform, "Environment");
                        Transform xr = Child(experiment.transform, "XR");
                        Transform systems = Child(experiment.transform, "Systems");
                        AssembleRoom(room);
                        lighting.ApplyRoomLightingDefaults(room, settings);

                        GameObject setup = RequirePrefab(
                            "XRInteractionToolkitSamples/Starter Assets/Prefabs/XR Interaction Setup.prefab", xr);
                        RequirePrefab(SimulatorPrefab, xr);
                        setup.transform.localPosition = new Vector3(-1.5f, 0f, -2.1f);
                        Camera camera = setup.GetComponentsInChildren<Camera>().Single(value => value.CompareTag("MainCamera"));
                        if (!camera.isActiveAndEnabled)
                            throw new InvalidOperationException("The approved XR camera must be active.");
                        Vector3 forward = Vector3.ProjectOnPlane(camera.transform.forward, Vector3.up).normalized;
                        Vector3 station = setup.transform.position;
                        Vector3 bench = station + forward * 2f;
                        RequireFloor(room, station, bench);
                        systems.gameObject.AddComponent<EmVrXrRayRuntimeTuner>().enableMouseLeftDebugSelect = false;
                        var pointer = systems.gameObject.AddComponent<EmVrMousePointer>();
                        pointer.showPointerRay = false;
                        EmVrGate5FoundationSceneUtility.EnsureSingleXrEventSystem(systems);
                        WireLab(experiment.transform, systems, camera, bench, forward);
                        foreach (var issue in EmVrSceneValidator.ValidateActiveScene())
                        {
                            if (issue.isError)
                                throw new InvalidOperationException(issue.message);
                            Debug.LogWarning("[ece329_solenoid_current] " + issue.message, issue.context);
                        }

                        if (!AssetDatabase.IsValidFolder("Assets/Scenes"))
                            AssetDatabase.CreateFolder("Assets", "Scenes");
                        guard.ThrowIfCapturedErrors();
                        if (!EditorSceneManager.SaveScene(scene, ScenePath))
                            throw new InvalidOperationException("Unity did not save " + ScenePath);
                        lighting.VerifyOriginalLightingAfterSave();
                        guard.ThrowIfCapturedErrors();
                        Debug.Log("[ece329_solenoid_current] Lab scene saved: " + ScenePath);
                    }
                    catch
                    {
                        if (inspection.IsValid() && inspection.isLoaded && inspection.path != previousPath)
                            EditorSceneManager.CloseScene(inspection, true);
                        if (scene.IsValid() && scene.isLoaded)
                        {
                            if (!string.IsNullOrEmpty(previousPath))
                                EditorSceneManager.OpenScene(previousPath, OpenSceneMode.Single);
                            else
                                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                        }
                        throw;
                    }
                }
            }
            catch (Exception error)
            {
                Debug.LogError("[ece329_solenoid_current] Lab build failed: " + error);
            }
        }

        static void RequireXrInputAssets()
        {
            RequireActionAsset("XRInteractionToolkitSamples/Starter Assets/XRI Default Input Actions.inputactions");
            InputActionAsset device = RequireActionAsset(SimulatorDirectory + "XR Device Simulator Controls.inputactions");
            InputActionAsset controller = RequireActionAsset(SimulatorDirectory + "XR Device Controller Controls.inputactions");
            InputActionAsset hand = RequireActionAsset(SimulatorDirectory + "XR Device Hand Controls.inputactions");
            string path = Imports + SimulatorPrefab;

            bool HasApprovedBindings()
            {
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                XRDeviceSimulator simulator = prefab != null ? prefab.GetComponentInChildren<XRDeviceSimulator>(true) : null;
                return simulator != null && simulator.deviceSimulatorActionAsset == device
                    && simulator.controllerActionAsset == controller && simulator.handActionAsset == hand;
            }

            if (!HasApprovedBindings())
                AssetDatabase.ImportAsset(path, ReimportOptions);
            if (!HasApprovedBindings())
                throw new InvalidOperationException("XR Device Simulator does not resolve its three approved input assets.");
        }

        static InputActionAsset RequireActionAsset(string relativePath)
        {
            string path = Imports + relativePath;
            InputActionAsset asset = AssetDatabase.LoadAssetAtPath<InputActionAsset>(path);
            if (asset == null || asset.actionMaps.Count == 0)
            {
                // Refresh can retain a failed import from when the project was opened at a long path.
                AssetDatabase.ImportAsset(path, ReimportOptions);
                asset = AssetDatabase.LoadAssetAtPath<InputActionAsset>(path);
            }
            if (asset == null || asset.actionMaps.Count == 0)
                throw new InvalidOperationException("Unity could not import XR input actions from " + path);
            return asset;
        }

        static void AssembleRoom(Transform room)
        {
            string recipePath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../Policies/emvr-room-assembly.json"));
            RoomRecipe recipe = JsonUtility.FromJson<RoomRecipe>(File.ReadAllText(recipePath));
            if (recipe.layout_revision != "emvrlabs-room-v1" || recipe.modules.Length != 5)
                throw new InvalidOperationException("Invalid approved room recipe.");

            var linkedCounts = new Dictionary<string, int>();
            foreach (RoomModule module in recipe.modules)
            {
                const string sourceRoot = "ApprovedAssets/";
                if (!module.prefab.StartsWith(sourceRoot, StringComparison.Ordinal))
                    throw new InvalidOperationException("Room recipe path must use ApprovedAssets.");
                string relative = module.prefab.Substring(sourceRoot.Length);
                if (AssetDatabase.AssetPathToGUID(Imports + relative) != module.guid)
                    throw new InvalidOperationException("Unexpected GUID for " + relative);
                GameObject instance = RequirePrefab(relative, room);
                instance.transform.localPosition = new Vector3(module.x, 0f, 0f);
                instance.transform.localRotation = Quaternion.Euler(0f, module.yaw, 0f);
                if (instance.transform.localScale != Vector3.one || !instance.activeInHierarchy)
                    throw new InvalidOperationException("Room modules must remain active at unit scale.");
                ApplyRoomOverrides(instance, module);
                string name = Path.GetFileNameWithoutExtension(relative);
                linkedCounts.TryGetValue(name, out int count);
                linkedCounts[name] = count + 1;
            }
            if (linkedCounts.Count != 3 || linkedCounts["Room_Big_Part_01"] != 2
                || linkedCounts["Room_Big_Part_02"] != 2 || linkedCounts["Room_Big_Part_03"] != 1)
                throw new InvalidOperationException("Wrong linked module counts.");
        }

        static void ApplyRoomOverrides(GameObject instance, RoomModule module)
        {
            var components = instance.GetComponentsInChildren<Component>(true);
            foreach (RoomOverride change in module.overrides)
            {
                Component target = components.SingleOrDefault(component =>
                {
                    if (!(component is Transform) && !(component is Light))
                        return false;
                    Component source = PrefabUtility.GetCorrespondingObjectFromSource(component);
                    return source != null
                        && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(source, out string guid, out long fileId)
                        && guid == module.guid && fileId == change.file_id;
                });
                if (target == null)
                    throw new InvalidOperationException("Room recipe target missing: " + change.file_id);

                bool validProperty = target is Transform
                    ? change.property == "m_LocalPosition.x" || change.property == "m_LocalPosition.y"
                    : change.property == "m_Intensity" || change.property == "m_Range"
                        || change.property.StartsWith("m_Color.", StringComparison.Ordinal);
                var serialized = new SerializedObject(target);
                SerializedProperty property = serialized.FindProperty(change.property);
                if (!validProperty || property == null || property.propertyType != SerializedPropertyType.Float)
                    throw new InvalidOperationException("Invalid room override: " + change.property);
                property.floatValue = change.value;
                serialized.ApplyModifiedPropertiesWithoutUndo();
                PrefabUtility.RecordPrefabInstancePropertyModifications(target);
            }
        }

        static bool HasRole(Renderer renderer, string role, Transform room)
        {
            for (Transform node = renderer.transform; node != null && node != room; node = node.parent)
                if (node.name.StartsWith(role, StringComparison.OrdinalIgnoreCase))
                    return true;
            return false;
        }

        static void RequireFloor(Transform room, Vector3 station, Vector3 bench)
        {
            Renderer[] active = room.GetComponentsInChildren<Renderer>()
                .Where(renderer => renderer.enabled).ToArray();
            Renderer[] floors = active.Where(renderer => HasRole(renderer, "Floor", room)
                && renderer.bounds.max.y < 0.75f).ToArray();
            if (floors.Length == 0 || !active.Any(renderer => HasRole(renderer, "Wall", room))
                || !active.Any(renderer => HasRole(renderer, "Roof", room)))
                throw new InvalidOperationException("Room requires active floor, wall and roof renderers.");
            Bounds footprint = floors[0].bounds;
            foreach (Renderer floor in floors)
                footprint.Encapsulate(floor.bounds);
            if (footprint.size.x < 14.8f || footprint.size.z < 17.8f)
                throw new InvalidOperationException("The approved room floor coverage is incomplete.");
            foreach (Vector3 point in new[] { station, bench, new Vector3(0f, 0f, 0f),
                         new Vector3(3f, 0f, 0f), new Vector3(-3f, 0f, 0f), new Vector3(-6f, 0f, 0f) })
                if (!floors.Any(floor => Covers(floor.bounds, point)))
                    throw new InvalidOperationException("No active floor footprint under " + point);
        }

        static bool Covers(Bounds bounds, Vector3 point)
        {
            const float seamMargin = 0.04f;
            return point.x >= bounds.min.x - seamMargin && point.x <= bounds.max.x + seamMargin
                && point.z >= bounds.min.z - seamMargin && point.z <= bounds.max.z + seamMargin;
        }

        static void WireLab(Transform root, Transform systems, Camera camera, Vector3 bench, Vector3 forward)
        {
            Vector3 right = Vector3.Cross(Vector3.up, forward);
            Transform apparatus = Child(root, "Experiment");
            Vector3 coilCenter = bench - right * 0.71f + Vector3.up * 1.03f;
            EmVrLabObject solenoid = CreateSolenoid(apparatus, coilCenter, right);
            GameObject marker = Primitive(apparatus, PrimitiveType.Sphere, "Fixed center probe",
                coilCenter, Vector3.one * 0.095f);
            var probe = marker.AddComponent<EmVrLabObject>();
            probe.ConfigureIdentity("center_probe", "Measurement", "Fixed center probe");
            Primitive(apparatus, PrimitiveType.Cube, "Bench top", coilCenter - Vector3.up * 0.25f,
                new Vector3(1.42f, 0.09f, 0.70f));
            for (int x = -1; x <= 1; x += 2)
            for (int z = -1; z <= 1; z += 2)
                Primitive(apparatus, PrimitiveType.Cube, "Bench leg",
                    coilCenter + new Vector3(x * 0.62f, -0.64f, z * 0.27f),
                    new Vector3(0.07f, 0.74f, 0.07f));

            Transform ui = Child(root, "UI");
            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            RectTransform start = CreatePanel(ui, "Start", camera,
                bench + Vector3.up * 1.47f, forward, new Vector2(900f, 360f));
            RectTransform lab = CreatePanel(ui, "Lab", camera,
                bench + right * 0.81f + Vector3.up * 1.47f, forward, new Vector2(1000f, 900f));

            var slice = systems.gameObject.AddComponent<SolenoidCurrentSlice>();
            slice.startPage = start.gameObject;
            slice.labPage = lab.gameObject;
            slice.apparatus = apparatus.gameObject;
            slice.currentState = lab.gameObject.AddComponent<EmVrParameterizedLabObject>();
            slice.currentState.ConfigureIdentity("current_panel", "ControlPanel", "Solenoid current");
            slice.currentState.ConfigureParameter("current_a", 0f, 0f, 2f);
            var plotObject = new GameObject("ScatterPlot", typeof(RectTransform), typeof(CanvasRenderer),
                typeof(SolenoidScatterPlot), typeof(EmVrLabObject));
            var plotRect = (RectTransform)plotObject.transform;
            plotRect.SetParent(lab, false);
            plotRect.sizeDelta = new Vector2(690f, 200f);
            plotRect.anchoredPosition = new Vector2(35f, 48f);
            slice.plot = plotObject.GetComponent<SolenoidScatterPlot>();
            slice.plot.raycastTarget = false;
            var results = plotObject.GetComponent<EmVrLabObject>();
            results.ConfigureIdentity("results_panel", "ResultsPanel", "Current versus magnetic field");
            var xr = root.Find("XR").gameObject.AddComponent<EmVrLabObject>();
            xr.ConfigureIdentity("xr_setup", "XRInput", "XR interaction setup");

            slice.snapshots = systems.gameObject.AddComponent<EmVrObjectStateSnapshotStore>();
            slice.snapshots.explicitObjects = new EmVrLabObject[] { slice.currentState };
            slice.telemetry = systems.gameObject.AddComponent<EmVrTelemetryEmitter>();
            slice.assist = systems.gameObject.AddComponent<EmVrAssistGroundingProvider>();
            slice.assist.explicitObjectSources = new[] { solenoid, probe, slice.currentState, results, xr };
            slice.assist.discoverObjectSourcesInChildren = false;
            slice.assist.telemetryEmitter = slice.telemetry;
            slice.status = systems.gameObject.AddComponent<EmVrStatusDisplay>();
            slice.runner = systems.gameObject.AddComponent<EmVrLabContractRunner>();
            slice.runner.labId = LabId;
            slice.runner.sessionId = "local_solenoid";
            slice.runner.userId = "local_student";
            slice.runner.clearTelemetryOnStart = false;
            slice.runner.knownObjects = new[] { solenoid, probe, slice.currentState, results, xr };
            string[] stepNames = { "Reset baseline", "Record zero", "Set current", "Record five points",
                "Compare results", "Explain the relationship" };
            slice.runner.steps = stepNames.Select((name, i) => new EmVrLabContractRunner.StepDefinition
                { stepId = "S" + (i + 1), displayName = name }).ToArray();
            slice.runner.statusDisplay = slice.status;
            slice.runner.telemetryEmitter = slice.telemetry;
            slice.runner.assistGrounding = slice.assist;
            new GameObject("PersistentServices", typeof(EmVrPersistentServiceRoot));
            systems.gameObject.AddComponent<EmVrSceneLoader>();

            Label(start, font, "Title", 0f, 83f, 845f, 75f, 44, "Solenoid magnetic field and current");
            Label(start, font, "Goal", 0f, 18f, 820f, 55f, 28,
                "Record the center field at five currents and compare the slope.");
            ButtonAt(start, font, "StartLab", "Start lab", 0f, -78f, slice.OpenLab);

            Label(lab, font, "Title", 0f, 365f, 905f, 56f, 37, "Center field of a long solenoid");
            slice.instruction = Label(lab, font, "Instruction", 0f, 310f, 925f, 48f, 26, "");
            slice.readout = Label(lab, font, "Reading", 0f, 255f, 925f, 48f, 32, "");
            slice.currentSlider = CurrentSlider(lab);
            Label(lab, font, "Vertical axis", -411f, 169f, 145f, 38f, 23, "Bz (mT)");
            Label(lab, font, "Horizontal axis", 437f, -43f, 94f, 36f, 23, "I (A)");
            for (int tick = 0; tick <= 4; tick++)
                Label(lab, font, "I tick " + tick, -310f + 172.5f * tick, -73f, 55f, 33f, 21,
                    (tick * .5f).ToString("0.0", System.Globalization.CultureInfo.InvariantCulture));
            for (int tick = 0; tick <= 5; tick++)
                Label(lab, font, "B tick " + tick, -357f, -52f + 200f * tick * .5f / 2.6f, 65f, 29f, 21,
                    (tick * .5f).ToString("0.0", System.Globalization.CultureInfo.InvariantCulture));
            Label(lab, font, "Legend", 0f, -112f, 935f, 34f, 23,
                "Solid points: recorded     Dashed line: theory (1.257 mT/A)");

            ButtonAt(lab, font, "Capture", "Record", -348f, -158f, slice.Capture);
            ButtonAt(lab, font, "Restore", "Restore", -116f, -158f, slice.Restore);
            ButtonAt(lab, font, "Reset", "Reset", 116f, -158f, slice.ResetMeasurement);
            slice.compareButton = ButtonAt(lab, font, "Compare", "Compare", 348f, -158f, slice.Compare);
            ButtonAt(lab, font, "Back", "Back", -348f, -220f, slice.Back);
            ButtonAt(lab, font, "Help", "Help", -116f, -220f, slice.Help);
            slice.finishButton = ButtonAt(lab, font, "Finish", "Finish", 348f, -220f, slice.Finish);
            slice.message = Label(lab, font, "Status", 0f, -269f, 925f, 42f, 24, "");
            slice.report = Label(lab, font, "Report", 0f, -339f, 925f, 96f, 22, "");
            slice.recordedReadings = Label(lab, font, "Records", 0f, -417f, 925f, 42f, 22, "");
            lab.gameObject.SetActive(false);
            apparatus.gameObject.SetActive(false);
            if (!slice.runner.TryValidateContract(out string error))
                throw new InvalidOperationException(error);
        }

        static EmVrLabObject CreateSolenoid(Transform apparatus, Vector3 center, Vector3 axis)
        {
            const string path = "Assets/ApprovedReuse/Models/solenoid1.fbx";
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (model == null || !(PrefabUtility.InstantiatePrefab(model, apparatus) is GameObject coil))
                throw new InvalidOperationException("The approved solenoid model is unavailable.");
            Renderer[] renderers = coil.GetComponentsInChildren<Renderer>();
            if (renderers.Length == 0)
                throw new InvalidOperationException("The approved solenoid has no visible mesh.");
            Bounds bounds = ModelBounds(renderers);
            Vector3 size = bounds.size;
            Vector3 sourceAxis = size.x >= size.y && size.x >= size.z ? Vector3.right
                : size.y >= size.z ? Vector3.up : Vector3.forward;
            float length = Mathf.Max(size.x, Mathf.Max(size.y, size.z));
            if (length <= Mathf.Epsilon)
                throw new InvalidOperationException("The approved solenoid has empty bounds.");
            var mount = Child(apparatus, "Solenoid mounting");
            mount.position = center;
            coil.transform.SetParent(mount, true);
            mount.rotation = Quaternion.FromToRotation(sourceAxis, axis);
            mount.localScale = Vector3.one * (1.20f / length);
            coil.transform.position += center - ModelBounds(renderers).center;
            foreach (Collider collider in coil.GetComponentsInChildren<Collider>(true))
                collider.enabled = false;
            var labObject = mount.gameObject.AddComponent<EmVrLabObject>();
            labObject.ConfigureIdentity("solenoid", "FieldSource", "Long solenoid");
            return labObject;
        }

        static Bounds ModelBounds(Renderer[] renderers)
        {
            Bounds bounds = renderers[0].bounds;
            foreach (Renderer renderer in renderers)
                bounds.Encapsulate(renderer.bounds);
            return bounds;
        }

        static GameObject Primitive(Transform parent, PrimitiveType type, string name, Vector3 position, Vector3 scale)
        {
            GameObject item = GameObject.CreatePrimitive(type);
            item.name = name;
            item.transform.SetParent(parent, false);
            item.transform.position = position;
            item.transform.localScale = scale;
            item.GetComponent<Collider>().enabled = false;
            return item;
        }

        static RectTransform CreatePanel(Transform parent, string name, Camera camera,
            Vector3 position, Vector3 forward, Vector2 size)
        {
            var panel = new GameObject(name, typeof(RectTransform), typeof(Canvas),
                typeof(GraphicRaycaster), typeof(TrackedDeviceGraphicRaycaster));
            var rect = (RectTransform)panel.transform;
            rect.SetParent(parent, false);
            rect.position = position;
            rect.rotation = Quaternion.LookRotation(forward, Vector3.up);
            rect.localScale = Vector3.one * 0.00135f;
            rect.sizeDelta = size;
            Canvas canvas = panel.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            canvas.worldCamera = camera;
            if (Vector3.Dot(-rect.forward, (camera.transform.position - rect.position).normalized) <= 0f)
                throw new InvalidOperationException("The actual XR camera is behind " + name + ".");
            var background = new GameObject("Panel background", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image))
                .GetComponent<Image>();
            background.rectTransform.SetParent(rect, false);
            background.rectTransform.anchorMin = Vector2.zero;
            background.rectTransform.anchorMax = Vector2.one;
            background.rectTransform.offsetMin = Vector2.zero;
            background.rectTransform.offsetMax = Vector2.zero;
            background.color = new Color(0.07f, 0.12f, 0.17f, 0.96f);
            background.raycastTarget = false;
            return rect;
        }

        static Text Label(RectTransform panel, Font font, string name, float x, float y, float width,
            float height, int fontSize, string value)
        {
            var text = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Text)).GetComponent<Text>();
            text.rectTransform.SetParent(panel, false);
            text.rectTransform.sizeDelta = new Vector2(width, height);
            text.rectTransform.anchoredPosition = new Vector2(x, y);
            text.font = font;
            text.fontSize = fontSize;
            text.alignment = TextAnchor.MiddleCenter;
            text.color = Color.white;
            text.text = value;
            text.raycastTarget = false;
            return text;
        }

        static Button ButtonAt(RectTransform panel, Font font, string name, string label,
            float x, float y, UnityEngine.Events.UnityAction action)
        {
            return EmVrGate5FoundationSceneUtility.CreatePersistentButton(
                panel, font, name, label, new Vector2(x, y), action);
        }

        static Slider CurrentSlider(RectTransform panel)
        {
            var rail = new GameObject("CurrentSlider", typeof(RectTransform), typeof(CanvasRenderer),
                typeof(Image), typeof(Slider));
            var railRect = rail.GetComponent<RectTransform>();
            railRect.SetParent(panel, false);
            railRect.sizeDelta = new Vector2(760f, 48f);
            railRect.anchoredPosition = new Vector2(0f, 197f);
            rail.GetComponent<Image>().color = new Color(0.15f, 0.27f, 0.35f);
            var travel = new GameObject("HandleTravel", typeof(RectTransform)).GetComponent<RectTransform>();
            travel.SetParent(railRect, false);
            travel.anchorMin = Vector2.zero;
            travel.anchorMax = Vector2.one;
            travel.offsetMin = new Vector2(21f, 0f);
            travel.offsetMax = new Vector2(-21f, 0f);
            var handle = new GameObject("Handle", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image))
                .GetComponent<Image>();
            handle.rectTransform.SetParent(travel, false);
            handle.rectTransform.sizeDelta = new Vector2(42f, 42f);
            handle.color = new Color(0.34f, 0.82f, 0.94f);

            var slider = rail.GetComponent<Slider>();
            slider.handleRect = handle.rectTransform;
            slider.targetGraphic = handle;
            slider.wholeNumbers = true;
            slider.maxValue = 20;
            return slider;
        }

        static Transform Child(Transform parent, string name)
        {
            var child = new GameObject(name);
            child.transform.SetParent(parent, false);
            return child.transform;
        }

        static GameObject RequirePrefab(string relativePath, Transform parent)
        {
            GameObject source = AssetDatabase.LoadAssetAtPath<GameObject>(Imports + relativePath);
            if (source == null || !(PrefabUtility.InstantiatePrefab(source, parent) is GameObject instance)
                || PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(instance) != Imports + relativePath)
                throw new InvalidOperationException("Unable to instantiate linked approved prefab " + relativePath);
            return instance;
        }

        [Serializable]
        sealed class RoomRecipe
        {
            public string layout_revision;
            public RoomModule[] modules;
        }

        [Serializable]
        sealed class RoomModule
        {
            public string prefab;
            public string guid;
            public float x;
            public float yaw;
            public RoomOverride[] overrides;
        }

        [Serializable]
        sealed class RoomOverride
        {
            public long file_id;
            public string property;
            public float value;
        }
    }
}
