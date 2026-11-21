using System.Collections.Generic;
using EMVR.Common.Objects;
using EMVR.ReusableFoundation.Gate5.Editor;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UnityEngine.XR.Interaction.Toolkit.UI;

namespace EMVR.ReusableFoundation.Gate5.Tests
{
    public sealed class EmVrGate5FoundationTests
    {
        readonly List<GameObject> created = new List<GameObject>();
        readonly List<EventSystem> preExistingEventSystems = new List<EventSystem>();
        readonly List<bool> preExistingEventSystemStates = new List<bool>();

        [SetUp]
        public void SetUp()
        {
            EventSystem[] systems = Object.FindObjectsOfType<EventSystem>(true);
            for (int i = 0; i < systems.Length; i++)
            {
                preExistingEventSystems.Add(systems[i]);
                preExistingEventSystemStates.Add(systems[i].enabled);
                systems[i].enabled = false;
            }
        }

        [TearDown]
        public void TearDown()
        {
            for (int i = created.Count - 1; i >= 0; i--)
            {
                if (created[i] != null)
                {
                    Object.DestroyImmediate(created[i]);
                }
            }
            created.Clear();
            for (int i = 0; i < preExistingEventSystems.Count; i++)
            {
                if (preExistingEventSystems[i] != null)
                {
                    preExistingEventSystems[i].enabled = preExistingEventSystemStates[i];
                }
            }
            preExistingEventSystems.Clear();
            preExistingEventSystemStates.Clear();
        }

        [Test]
        public void InactiveReplacementTemplateIsRejected()
        {
            EmVrGate5FoundationHarness harness = CreateHarness(out GameObject template);
            template.SetActive(false);

            Assert.That(harness.TryValidateWiring(out string failure), Is.False);
            StringAssert.Contains("inactive", failure);
        }

        [Test]
        public void PersistentButtonSpawnsActiveVisibleCollidableObject()
        {
            EmVrGate5FoundationHarness harness = CreateHarness(out _);
            Canvas canvas = harness.spawnButton.GetComponentInParent<Canvas>();
            Assert.That(canvas.GetComponent<GraphicRaycaster>(), Is.Not.Null);
            Assert.That(canvas.GetComponent<TrackedDeviceGraphicRaycaster>(), Is.Not.Null);

            Assert.That(harness.TryValidateWiring(out string wiringFailure), Is.True, wiringFailure);
            Assert.That(
                harness.spawnButton.onClick.GetPersistentListenerState(0),
                Is.EqualTo(UnityEventCallState.EditorAndRuntime));
            harness.spawnButton.onClick.Invoke();
            created.Add(harness.SpawnedObject);
            Assert.That(
                harness.TryValidateSpawnedVisibility(out string visibilityFailure),
                Is.True,
                visibilityFailure);
        }

        [Test]
        public void DuplicateActiveEventSystemsAreRejected()
        {
            EmVrGate5FoundationHarness harness = CreateHarness(out _);
            NewObject("Duplicate EventSystem").AddComponent<EventSystem>();

            Assert.That(harness.TryValidateWiring(out string failure), Is.False);
            StringAssert.Contains("exactly one active EventSystem", failure);
        }

        EmVrGate5FoundationHarness CreateHarness(out GameObject template)
        {
            NewObject("EventSystem").AddComponent<EventSystem>();

            GameObject cameraObject = NewObject("Validation Camera");
            Camera camera = cameraObject.AddComponent<Camera>();
            camera.transform.position = new Vector3(0f, 0f, -5f);
            camera.transform.rotation = Quaternion.identity;

            GameObject anchorObject = NewObject("Spawn Anchor");
            GameObject loaderObject = NewObject("Loader");
            EmVrReplacementSpawner spawner = loaderObject.AddComponent<EmVrReplacementSpawner>();
            spawner.spawnAnchor = anchorObject.transform;
            spawner.maximumReplacementCount = 1;
            spawner.captureOriginOnEnable = false;
            spawner.CaptureOrigin();

            template = GameObject.CreatePrimitive(PrimitiveType.Cube);
            template.name = "Active Offstage Template";
            template.transform.position = new Vector3(0f, -1000f, 0f);
            created.Add(template);
            spawner.replacementPrefab = template;

            GameObject canvasObject = NewObject("Canvas", typeof(RectTransform), typeof(Canvas));
            Canvas canvas = canvasObject.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            canvas.worldCamera = camera;

            GameObject harnessObject = NewObject("Foundation Harness");
            EmVrGate5FoundationHarness harness = harnessObject.AddComponent<EmVrGate5FoundationHarness>();
            harness.spawnButton = EmVrGate5FoundationSceneUtility.CreatePersistentButton(
                (RectTransform)canvas.transform, Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"),
                "Spawn Button", "Spawn", Vector2.zero, harness.SpawnAndValidate);
            harness.replacementSpawner = spawner;
            harness.validationCamera = camera;
            return harness;
        }

        GameObject NewObject(string name)
        {
            GameObject instance = new GameObject(name);
            created.Add(instance);
            return instance;
        }

        GameObject NewObject(string name, params System.Type[] components)
        {
            GameObject instance = new GameObject(name, components);
            created.Add(instance);
            return instance;
        }
    }
}
