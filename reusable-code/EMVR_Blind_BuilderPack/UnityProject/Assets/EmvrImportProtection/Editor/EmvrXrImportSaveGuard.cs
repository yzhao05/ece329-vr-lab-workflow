using System;
using System.Text.RegularExpressions;
using UnityEditor;

namespace Emvr.Workflow.Editor
{
    // Unity may dirty the imported prefab while editing a scene instance.
    // Scene changes are saved normally. The approved asset stays byte-identical.
    sealed class EmvrXrImportSaveGuard : AssetModificationProcessor
    {
        static readonly Regex ImportedSetup = new Regex(
            @"\AAssets/Generated/[a-z][a-z0-9_]{2,63}/ApprovedDependencies/XRInteractionToolkitSamples/Starter Assets/Prefabs/XR Interaction Setup\.prefab(?:\.meta)?\z",
            RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

        static string[] OnWillSaveAssets(string[] paths)
        {
            return Array.FindAll(paths, path => !ImportedSetup.IsMatch(path.Replace('\\', '/')));
        }
    }
}
