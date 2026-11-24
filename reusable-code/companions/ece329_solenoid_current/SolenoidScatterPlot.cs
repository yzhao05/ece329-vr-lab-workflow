using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace EMVR.Labs.Ece329SolenoidCurrent
{
    // The scene builder supplies tick labels for 0–2 A and 0–2.6 mT.
    public sealed class SolenoidScatterPlot : MaskableGraphic
    {
        const float MaxCurrent = 2f;
        const float MaxField = 2.6f;
        const float SlopeMilliTeslaPerAmp = 1.25663706f;
        readonly List<Vector2> samples = new List<Vector2>();

        public void AddPoint(float current, float field)
        {
            Vector2 point = new Vector2(current, field);
            if (samples.Contains(point)) return;
            samples.Add(point);
            SetVerticesDirty();
        }

        public void ClearPoints()
        {
            samples.Clear();
            SetVerticesDirty();
        }

        protected override void OnPopulateMesh(VertexHelper mesh)
        {
            mesh.Clear();
            Rect bounds = GetPixelAdjustedRect();
            if (bounds.width <= 0 || bounds.height <= 0) return;

            Vector2 origin = bounds.min;
            AddLine(mesh, origin, new Vector2(bounds.xMax, bounds.yMin), color);
            AddLine(mesh, origin, new Vector2(bounds.xMin, bounds.yMax), color);

            Vector2 end = new Vector2(bounds.xMax, bounds.yMin + bounds.height * MaxCurrent * SlopeMilliTeslaPerAmp / MaxField);
            const int dashes = 18;
            for (int i = 0; i < dashes; i++)
            {
                AddLine(mesh, Vector2.Lerp(origin, end, (float)i / dashes),
                    Vector2.Lerp(origin, end, (i + 0.65f) / dashes), new Color32(255, 209, 95, 255));
            }
            foreach (Vector2 sample in samples)
            {
                Vector2 center = origin + new Vector2(bounds.width * sample.x / MaxCurrent, bounds.height * sample.y / MaxField);
                AddPointMarker(mesh, center);
            }
        }

        static void AddLine(VertexHelper mesh, Vector2 start, Vector2 end, Color32 tint)
        {
            Vector2 offset = Vector2.Perpendicular(end - start).normalized;
            int first = mesh.currentVertCount;
            mesh.AddVert(start - offset, tint, Vector2.zero);
            mesh.AddVert(start + offset, tint, Vector2.zero);
            mesh.AddVert(end + offset, tint, Vector2.zero);
            mesh.AddVert(end - offset, tint, Vector2.zero);
            mesh.AddTriangle(first, first + 1, first + 2);
            mesh.AddTriangle(first, first + 2, first + 3);
        }

        static void AddPointMarker(VertexHelper mesh, Vector2 center)
        {
            const int sides = 12;
            Color32 tint = new Color32(100, 225, 255, 255);
            int first = mesh.currentVertCount;
            mesh.AddVert(center, tint, Vector2.zero);
            for (int i = 0; i < sides; i++)
            {
                float angle = -2f * Mathf.PI * i / sides;
                mesh.AddVert(center + 5f * new Vector2(Mathf.Cos(angle), Mathf.Sin(angle)), tint, Vector2.zero);
            }
            for (int i = 0; i < sides; i++)
                mesh.AddTriangle(first, first + 1 + i, first + 1 + (i + 1) % sides);
        }
    }
}
