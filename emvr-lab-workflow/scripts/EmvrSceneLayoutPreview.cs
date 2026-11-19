using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using Unity.Collections;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

// Editor-only bridge. Scene assets and Builder evidence are never written here.
[InitializeOnLoad]
internal static class EmvrSceneLayoutPreview
{
    [Serializable]
    private class Item
    {
        public int id;
        public string name;
        public Vector3 position;
        public int mesh;
        public float[] matrix;
        public string[] colors;
    }

    [Serializable]
    private class Layout
    {
        public string scene;
        public string fileTicks;
        public string geometry;
        public List<Item> objects = new List<Item>();
    }

    private static double nextUpdate;
    private static readonly HashSet<string> liveFiles = new HashSet<string>();
    private static readonly string cache = Path.Combine(Application.dataPath, "../Library/EMVRLayout");
    private static readonly Dictionary<string, (string inputs, string hash)> bundles =
        new Dictionary<string, (string, string)>();

    static EmvrSceneLayoutPreview()
    {
        EditorApplication.projectChanged += bundles.Clear;
        EditorSceneManager.sceneSaved += scene => Publish(scene, true);
        EditorSceneManager.sceneOpened += (scene, mode) => Publish(scene, true);
        EditorApplication.delayCall += () => VisitScenes(true);
        EditorApplication.update += () =>
        {
            if (EditorApplication.timeSinceStartup < nextUpdate) return;
            nextUpdate = EditorApplication.timeSinceStartup + 2;
            VisitScenes(false);
        };
        EditorSceneManager.sceneClosed += scene => RemoveLive(scene.path);
        EditorApplication.quitting += ClearLive;
        AssemblyReloadEvents.beforeAssemblyReload += ClearLive;
    }

    private static void VisitScenes(bool saved)
    {
        for (int i = 0; i < SceneManager.sceneCount; i++)
            Publish(SceneManager.GetSceneAt(i), saved);
    }

    private static void Publish(Scene scene, bool saved)
    {
        if (!scene.isLoaded || !scene.path.StartsWith("Assets/Scenes/", StringComparison.Ordinal)
            || !File.Exists(scene.path) || (saved && (scene.isDirty || EditorApplication.isPlayingOrWillChangePlaymode))) return;
        var temporary = new List<Mesh>();
        try
        {
            var data = new Layout { scene = scene.path, fileTicks = File.GetLastWriteTimeUtc(scene.path).Ticks.ToString() };
            var meshes = new List<Mesh>();
            var slots = new Dictionary<Mesh, int>();
            foreach (var root in scene.GetRootGameObjects())
            {
                foreach (var renderer in root.GetComponentsInChildren<Renderer>())
                {
                    if (!renderer.gameObject.activeInHierarchy || !renderer.enabled || renderer.forceRenderingOff
                        || (renderer.gameObject.hideFlags & HideFlags.HideInHierarchy) != 0) continue;
                    var matrix = renderer.localToWorldMatrix;
                    Mesh mesh = null;
                    if (renderer is SkinnedMeshRenderer skin && skin.sharedMesh)
                    {
                        mesh = new Mesh();
                        temporary.Add(mesh);
                        skin.BakeMesh(mesh);
                    }
                    else if (renderer is LineRenderer line && line.positionCount > 1)
                    {
                        mesh = new Mesh();
                        temporary.Add(mesh);
                        var camera = SceneView.lastActiveSceneView ? SceneView.lastActiveSceneView.camera : Camera.main;
                        if (camera) line.BakeMesh(mesh, camera, false);
                        else
                        {
                            var points = new Vector3[line.positionCount];
                            line.GetPositions(points);
                            mesh.vertices = points;
                            var indices = new int[(points.Length - (line.loop ? 0 : 1)) * 2];
                            for (int i = 0; i < indices.Length / 2; i++)
                            {
                                indices[2*i] = i;
                                indices[2*i+1] = (i+1) % points.Length;
                            }
                            mesh.SetIndices(indices, MeshTopology.Lines, 0);
                        }
                        if (line.useWorldSpace) matrix = Matrix4x4.identity;
                    }
                    else if (renderer is MeshRenderer && renderer.TryGetComponent<MeshFilter>(out var filter))
                        mesh = filter.sharedMesh;
                    if (!mesh || mesh.vertexCount == 0) continue;
                    if (!slots.TryGetValue(mesh, out int slot))
                    {
                        if (!HasGeometry(mesh)) continue;
                        slot = meshes.Count;
                        slots.Add(mesh, slot);
                        meshes.Add(mesh);
                    }
                    var elements = new float[16];
                    for (int i = 0; i < elements.Length; i++) elements[i] = matrix[i];
                    var colors = Array.ConvertAll(renderer.sharedMaterials, material =>
                    {
                        var color = Color.gray;
                        if (material && material.HasProperty("_BaseColor")) color = material.GetColor("_BaseColor");
                        else if (material && material.HasProperty("_Color")) color = material.GetColor("_Color");
                        return "#" + ColorUtility.ToHtmlStringRGB(color);
                    });
                    data.objects.Add(new Item { id = renderer.GetInstanceID(), name = renderer.name, position = renderer.transform.position,
                        matrix = elements, mesh = slot, colors = colors });
                }
            }
            var path = Path.Combine(cache, scene.path + (saved ? ".saved.json" : ".live.json"));
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            if (meshes.Count > 0) data.geometry = WriteGeometry(path + ".bin", meshes, saved);
            var temp = path + ".tmp";
            File.WriteAllText(temp, JsonUtility.ToJson(data));
            if (File.Exists(path)) File.Replace(temp, path, null);
            else File.Move(temp, path);
            if (meshes.Count == 0) RemoveGeometry(path);
            if (!saved) liveFiles.Add(path);
        }
        catch (IOException) { /* The next editor update retries transient file locks. */ }
        finally { foreach (var mesh in temporary) UnityEngine.Object.DestroyImmediate(mesh); }
    }

    private static bool HasGeometry(Mesh mesh)
    {
        for (int i = 0; i < mesh.subMeshCount; i++)
            if (mesh.GetIndexCount(i) > 0 && (mesh.GetTopology(i) == MeshTopology.Triangles || mesh.GetTopology(i) == MeshTopology.Lines))
                return true;
        return false;
    }

    // One local-space mesh per unique source. Moving an instance only changes its matrix.
    private static string WriteGeometry(string path, List<Mesh> meshes, bool saved)
    {
        var keys = new List<string>(meshes.Count);
        var dynamicParts = new Dictionary<Mesh, byte[]>();
        foreach (var mesh in meshes)
        {
            if (EditorUtility.IsPersistent(mesh))
                keys.Add(mesh.GetInstanceID() + "/" + EditorUtility.GetDirtyCount(mesh));
            else
            {
                using (var part = new MemoryStream())
                using (var partWriter = new BinaryWriter(part))
                {
                    WriteMesh(partWriter, mesh);
                    var bytes = part.ToArray();
                    dynamicParts.Add(mesh, bytes);
                    using (var sha = SHA256.Create()) keys.Add(Convert.ToBase64String(sha.ComputeHash(bytes)));
                }
            }
        }
        string inputs = string.Join(",", keys);
        bool exists = bundles.TryGetValue(path, out var previous) && File.Exists(path);
        if (!saved && exists && inputs == previous.inputs) return previous.hash;
        using (var stream = new MemoryStream())
        using (var writer = new BinaryWriter(stream))
        {
            writer.Write(meshes.Count);
            foreach (var mesh in meshes)
            {
                if (dynamicParts.TryGetValue(mesh, out var bytes)) writer.Write(bytes);
                else WriteMesh(writer, mesh);
            }
            stream.Position = 0;
            string hash;
            using (var sha = SHA256.Create()) hash = BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
            if (!exists || previous.hash != hash)
            {
                stream.Position = 0;
                using (var file = File.Create(path + ".tmp")) stream.CopyTo(file);
                if (File.Exists(path)) File.Replace(path + ".tmp", path, null);
                else File.Move(path + ".tmp", path);
            }
            bundles[path] = (inputs, hash);
            return hash;
        }
    }

    private static void WriteMesh(BinaryWriter writer, Mesh mesh)
    {
        // Editor API also reads imported models with Read/Write disabled.
        using (var native = MeshUtility.AcquireReadOnlyMeshData(mesh))
        using (var positions = new NativeArray<Vector3>(mesh.vertexCount, Allocator.Temp))
        {
            var source = native[0];
            source.GetVertices(positions);
            writer.Write(positions.Length);
            foreach (var p in positions) { writer.Write(p.x); writer.Write(p.y); writer.Write(p.z); }
            writer.Write(source.subMeshCount);
            for (int i = 0; i < source.subMeshCount; i++)
            {
                var sub = source.GetSubMesh(i);
                bool supported = sub.topology == MeshTopology.Triangles || sub.topology == MeshTopology.Lines;
                writer.Write(sub.topology == MeshTopology.Lines ? 2 : 3);
                writer.Write(supported ? sub.indexCount : 0);
                if (!supported || sub.indexCount == 0) continue;
                using (var indices = new NativeArray<int>(sub.indexCount, Allocator.Temp))
                {
                    source.GetIndices(indices, i, true);
                    foreach (int index in indices) writer.Write(index);
                }
            }
        }
    }

    private static void RemoveLive(string scene)
    {
        var path = Path.Combine(cache, scene + ".live.json");
        if (liveFiles.Remove(path)) RemoveSnapshot(path);
    }

    private static void ClearLive()
    {
        foreach (var path in liveFiles) RemoveSnapshot(path);
        liveFiles.Clear();
    }

    private static void RemoveSnapshot(string path)
    {
        TryDelete(path);
        RemoveGeometry(path);
    }

    private static void RemoveGeometry(string path)
    {
        var binary = path + ".bin";
        bundles.Remove(binary);
        if (File.Exists(binary)) TryDelete(binary);
    }

    private static void TryDelete(string path)
    {
        try { File.Delete(path); } catch (IOException) { }
    }
}
