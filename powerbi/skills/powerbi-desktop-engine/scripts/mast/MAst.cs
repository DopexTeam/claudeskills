// Emits Power BI's own M syntax tree as JSON.
//
// Every dependency-extraction regex in depgraph.py reimplements argument-position
// analysis that this tree gives exactly. The subtle bugs so far were parsing
// failures rather than logic failures: a nested call head a head-matcher could
// not see, a column named as a string inside an aggregate lambda, an unmatched
// ')' inside a comment.
//
// Targets .NET Framework because Microsoft.MashupEngine.dll does.
//   csc /target:exe /out:mast.exe MAst.cs /r:Microsoft.MashupEngine.dll
//
// stdin : one record per line, "name<TAB>M-text" with \n escaped
// stdout: [{name, ok, ast|error}]
using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Text;

public static class MAst
{
    static object engine;
    static MethodInfo parse;

    static Type FindType(Assembly a, string simpleName)
    {
        Type[] ts;
        try { ts = a.GetTypes(); }
        catch (ReflectionTypeLoadException e) { ts = e.Types; }
        foreach (Type t in ts) { if (t != null && t.Name == simpleName) return t; }
        return null;
    }

    static void Init(string dll)
    {
        Assembly a = Assembly.LoadFrom(dll);
        Type engines = FindType(a, "Engines");
        engine = engines.GetProperty("Version1").GetValue(null, null);
        Type ext = FindType(a, "IEngineExtensions");
        foreach (MethodInfo m in ext.GetMethods(BindingFlags.Public | BindingFlags.Static))
        {
            if (m.Name == "Parse" && m.GetParameters().Length == 3) parse = m;
        }
    }

    static void Esc(StringBuilder sb, string s)
    {
        sb.Append('"');
        for (int i = 0; i < s.Length; i++)
        {
            char c = s[i];
            if (c == '"') sb.Append("\\\"");
            else if (c == '\\') sb.Append("\\\\");
            else if (c == '\n') sb.Append("\\n");
            else if (c == '\r') sb.Append("\\r");
            else if (c == '\t') sb.Append("\\t");
            else if (c < ' ') sb.Append("\\u").Append(((int)c).ToString("x4"));
            else sb.Append(c);
        }
        sb.Append('"');
    }

    // Node kind, scalar payload (identifier names, literal text), then children.
    //
    // `seen` guards against cycles and must therefore be scoped to the CURRENT
    // PATH -- entries are removed on the way back up. A tree-global set looks
    // like a harmless de-duplication but is not: the engine INTERNS TextValues
    // and identifiers, so the second occurrence of any repeated literal is the
    // same object and would be dropped. `{"a"} ... {"a"}` would emit the second
    // list empty, and a column named twice in a query would simply vanish --
    // exactly the silent false negative this whole tool exists to prevent.
    static void Dump(object n, StringBuilder sb, int depth, HashSet<object> seen)
    {
        if (n == null || depth > 60) { sb.Append("null"); return; }
        Type t = n.GetType();
        sb.Append("{");
        Esc(sb, "k"); sb.Append(":"); Esc(sb, t.Name);
        List<string> kids = new List<string>();
        foreach (PropertyInfo p in t.GetProperties())
        {
            // Token positions and inferred type metadata dominate the output --
            // every string literal drags a PrimitiveTypeValue with twenty flags
            // behind it -- and nothing downstream reads them.
            if (p.Name == "Range" || p.Name == "Type" || p.Name == "Kind" ||
                p.Name == "TypeFacets" || p.Name == "Start" || p.Name == "End") continue;
            object v;
            try { v = p.GetValue(n, null); }
            catch { continue; }
            if (v == null) continue;
            if (v is string || v is bool || v is int || v is long || v is double)
            {
                sb.Append(","); Esc(sb, p.Name); sb.Append(":"); Esc(sb, Convert.ToString(v));
            }
            else if (v is IEnumerable)
            {
                StringBuilder inner = new StringBuilder("[");
                bool any = false;
                foreach (object i in (IEnumerable)v)
                {
                    if (i == null || i is string || i.GetType().IsPrimitive) continue;
                    if (any) inner.Append(",");
                    Dump(i, inner, depth + 1, seen);
                    any = true;
                }
                inner.Append("]");
                if (any) kids.Add("\"" + p.Name + "\":" + inner.ToString());
            }
            else
            {
                Type vt = v.GetType();
                if (vt.Namespace == null || !vt.Namespace.StartsWith("Microsoft.Mashup")) continue;
                if (seen.Contains(v)) continue;
                seen.Add(v);
                StringBuilder inner = new StringBuilder();
                Dump(v, inner, depth + 1, seen);
                seen.Remove(v);
                kids.Add("\"" + p.Name + "\":" + inner.ToString());
            }
        }
        for (int i = 0; i < kids.Count; i++) { sb.Append(",").Append(kids[i]); }
        sb.Append("}");
    }

    public static int Main(string[] args)
    {
        Init(args[0]);
        string input = Console.In.ReadToEnd();
        StringBuilder outSb = new StringBuilder("[");
        bool first = true;
        string[] lines = input.Split('\n');
        for (int li = 0; li < lines.Length; li++)
        {
            string line = lines[li].TrimEnd('\r');
            if (line.Trim().Length == 0) continue;
            int tab = line.IndexOf('\t');
            if (tab < 0) continue;
            string name = line.Substring(0, tab);
            string m = line.Substring(tab + 1)
                           .Replace("\\n", "\n").Replace("\\t", "\t");
            if (!first) outSb.Append(",");
            first = false;
            outSb.Append("{");
            Esc(outSb, "name"); outSb.Append(":"); Esc(outSb, name);
            try
            {
                object doc = parse.Invoke(null, new object[] {
                    engine, "section S;\nshared Q = " + m + ";", null });
                object section = doc.GetType().GetProperty("Section").GetValue(doc, null);
                outSb.Append(","); Esc(outSb, "ok"); outSb.Append(":true,");
                Esc(outSb, "ast"); outSb.Append(":");
                Dump(section, outSb, 0, new HashSet<object>());
            }
            catch (Exception e)
            {
                Exception r = e;
                while (r.InnerException != null) r = r.InnerException;
                outSb.Append(","); Esc(outSb, "ok"); outSb.Append(":false,");
                Esc(outSb, "error"); outSb.Append(":"); Esc(outSb, r.Message);
            }
            outSb.Append("}");
        }
        outSb.Append("]");
        Console.Out.Write(outSb.ToString());
        return 0;
    }
}
